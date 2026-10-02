# backend-python/app/services/subscription.py
"""Central subscription service - the single authoritative access resolver.

Every access decision in the product flows through
``SubscriptionService.get_access_status()``. Routers never re-implement the
precedence rules:

    1. SUPER_ADMIN                        -> always allowed
    2. school subscriptions disabled      -> allowed (nothing to enforce)
    3. active school-wide free override   -> allowed until free_until
    4. active individual free override    -> allowed until free_until
    5. active individual subscription     -> allowed while start <= now < end
    6. active role-plan entitlement       -> allowed (ROLE_PLAN-sourced row)
    7. otherwise                          -> PAYMENT_REQUIRED

Notes on rule 6/8: a *role plan* is only the price offered to a role - it
never grants access by itself (see spec section 8). Entitlement comes from a
``subscriptions`` row (any source, including ROLE_PLAN) or an override, so
the payment model stays clean.

Access never depends on a background job: expiry is evaluated from the
current server time on every check (``start_at <= now < end_at``).

TIME: all datetimes are naive UTC (``app.core.time_utils``); aware client
input is normalised on the way in.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException, status as http_status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.time_utils import add_duration, utcnow
from app.crud.notification import notification as crud_notification
from app.models.notification import Notification
from app.models.school import School
from app.models.school_subscription_settings import SchoolSubscriptionSettings
from app.models.subscription import (
    LIVE_STATUSES,
    SUBSCRIPTION_SOURCES,
    Subscription,
)
from app.models.subscription_audit_log import SubscriptionAuditLog
from app.models.subscription_payment import SubscriptionPayment
from app.models.subscription_plan import BILLABLE_ROLES, DURATION_UNITS, SubscriptionPlan
from app.models.user import User
from app.models.user_subscription_override import OVERRIDE_TYPES, UserSubscriptionOverride
from app.schemas.subscription import AccessStatusResponse, PlanBrief


# ---------------------------------------------------------------------------
# Errors (structured, machine-readable - FastAPI renders them as-is)
# ---------------------------------------------------------------------------


class SubscriptionError(HTTPException):
    """HTTP error with a stable ``detail.code`` the frontend can branch on."""

    def __init__(self, code: str, message: str, status_code: int = 400, **extra: Any):
        detail: Dict[str, Any] = {"code": code, "message": message}
        detail.update(extra)
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class SubscriptionRequired(SubscriptionError):
    """403 SUBSCRIPTION_REQUIRED: authenticated but not entitled right now."""

    def __init__(self, *, state: str, reason: str, expires_at: Optional[datetime]):
        super().__init__(
            "SUBSCRIPTION_REQUIRED",
            "Your subscription does not allow access to this feature right now.",
            status_code=http_status.HTTP_403_FORBIDDEN,
            subscription_status=state,
            reason=reason,
            expires_at=expires_at.isoformat() if expires_at else None,
        )


# ---------------------------------------------------------------------------
# Access status value object
# ---------------------------------------------------------------------------


@dataclass
class AccessStatus:
    has_access: bool
    status: str            # ACTIVE | PAYMENT_REQUIRED | SUSPENDED
    reason: str
    plan: Optional[PlanBrief] = None
    expires_at: Optional[datetime] = None
    subscription_id: Optional[int] = None
    subscriptions_enabled: bool = False
    school_free_until: Optional[datetime] = None
    user_free_until: Optional[datetime] = None
    school_id: Optional[int] = None
    role: str = ""
    mock_payments_enabled: bool = False
    payment_provider: str = "INTERNAL"

    def as_response(self) -> AccessStatusResponse:
        return AccessStatusResponse.model_validate(dict(self.__dict__))


# Small helpers ------------------------------------------------------------


def _plan_brief(plan: Optional[SubscriptionPlan]) -> Optional[PlanBrief]:
    if plan is None:
        return None
    return PlanBrief(
        id=plan.id,
        name=plan.name,
        price=float(plan.price),
        currency=plan.currency,
        billing_interval=plan.billing_interval,
        duration_value=plan.duration_value,
        duration_unit=plan.duration_unit,
    )


def _allow(
    reason: str,
    *,
    expires_at: Optional[datetime] = None,
    plan: Optional[SubscriptionPlan] = None,
    subscription_id: Optional[int] = None,
    subscriptions_enabled: bool = False,
    school_free_until: Optional[datetime] = None,
    user_free_until: Optional[datetime] = None,
    school_id: Optional[int] = None,
    role: str = "",
) -> AccessStatus:
    from app.services.payment import PaymentService  # local import: avoid cycle

    return AccessStatus(
        has_access=True,
        status="ACTIVE",
        reason=reason,
        plan=_plan_brief(plan),
        expires_at=expires_at,
        subscription_id=subscription_id,
        subscriptions_enabled=subscriptions_enabled,
        school_free_until=school_free_until,
        user_free_until=user_free_until,
        school_id=school_id,
        role=role,
        mock_payments_enabled=PaymentService.mock_payments_enabled(),
    )


def _deny(
    state: str,
    reason: str,
    *,
    expires_at: Optional[datetime] = None,
    plan: Optional[SubscriptionPlan] = None,
    subscription_id: Optional[int] = None,
    subscriptions_enabled: bool = True,
    school_free_until: Optional[datetime] = None,
    user_free_until: Optional[datetime] = None,
    school_id: Optional[int] = None,
    role: str = "",
) -> AccessStatus:
    from app.services.payment import PaymentService

    return AccessStatus(
        has_access=False,
        status=state,
        reason=reason,
        plan=_plan_brief(plan),
        expires_at=expires_at,
        subscription_id=subscription_id,
        subscriptions_enabled=subscriptions_enabled,
        school_free_until=school_free_until,
        user_free_until=user_free_until,
        school_id=school_id,
        role=role,
        mock_payments_enabled=PaymentService.mock_payments_enabled(),
    )


# ---------------------------------------------------------------------------
# Notification helpers (reuse the existing notification infrastructure)
# ---------------------------------------------------------------------------

_REMINDER_WINDOWS = (
    (7 * 86400, 6 * 86400, "7 days"),
    (3 * 86400, 2 * 86400, "3 days"),
    (1 * 86400, 0, "1 day"),
)


def _notify_type_for(role: str) -> str:
    """Pick a notification_type the existing visibility filters accept.

    Students see direct (user_id == me) rows regardless of type; teachers
    only see rows of type PUBLIC/STAFF_ONLY inside their school, so direct
    messages to staff use STAFF_ONLY.
    """
    return "ONLY_FOR_STUDENT" if str(role).upper() == "STUDENT" else "STAFF_ONLY"


def notify_user(
    db: Session,
    *,
    user: User,
    title: str,
    message: str,
    reference_id: Optional[int] = None,
    once: bool = True,
) -> None:
    """Best-effort, targeted notification through the existing pipeline.

    ``once=True`` de-duplicates on (user, title, message) so reminder spam
    cannot happen even if the access check runs on every request.
    """
    try:
        if once:
            exists_row = (
                db.query(Notification)
                .filter(
                    Notification.user_id == user.id,
                    Notification.title == title,
                    Notification.message == message,
                )
                .first()
            )
            if exists_row is not None:
                return
        crud_notification.create(
            db,
            title=title,
            message=message,
            notification_type=_notify_type_for(str(user.role)),
            sender_id=None,
            sender_role="SUPER_ADMIN",
            school_id=user.school_id,
            category=None,
            user_id=user.id,
            reference_id=reference_id,
        )
    except Exception:  # noqa: BLE001 - notifications must never break the caller
        db.rollback()


def _maybe_send_expiry_reminders(
    db: Session, user: User, sub: Subscription, now: datetime
) -> None:
    """Emit 7/3/1-day reminders lazily during access checks (no cron yet)."""
    if sub.end_at is None:
        return
    remaining = (sub.end_at - now).total_seconds()
    if remaining <= 0:
        return
    for upper, lower, label in _REMINDER_WINDOWS:
        if lower < remaining <= upper:
            expiry_text = sub.end_at.strftime("%d %b %Y")
            notify_user(
                db,
                user=user,
                title=f"Subscription expires in {label}",
                message=(
                    f"Your subscription expires on {expiry_text}. Renew a plan "
                    f"to keep using the portal without interruption."
                ),
                reference_id=sub.id,
            )
            return


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------


class SubscriptionService:
    """Static-method service (house style)."""

    # -----------------------------------------------------------------------
    # 1. Access resolution - THE authoritative check
    # -----------------------------------------------------------------------

    @staticmethod
    def get_settings(
        db: Session, school_id: Optional[int]
    ) -> Tuple[bool, Optional[datetime]]:
        """Effective settings for a school. No row == subscriptions disabled."""
        if school_id is None:
            return False, None
        row = (
            db.query(SchoolSubscriptionSettings)
            .filter(SchoolSubscriptionSettings.school_id == school_id)
            .first()
        )
        if row is None:
            return False, None
        return bool(row.subscriptions_enabled), row.free_until

    @staticmethod
    def get_access_status(db: Session, user: User) -> AccessStatus:
        """Resolve the caller's entitlement right now (pure read)."""
        now = utcnow()
        role = str(getattr(user, "role", "") or "").upper()

        # -- 1. Super Admin bypass ----------------------------------------
        if role == "SUPER_ADMIN":
            return _allow("SUPER_ADMIN", role=role, school_id=user.school_id)

        # -- 1b. Roles that are never billed -------------------------------
        # Only PRINCIPAL / TEACHER / STUDENT are billable (see BILLABLE_ROLES
        # and _ensure_billable). Gating a parent - or any future non-billable
        # role - behind a payment would break an ERP feature that has nothing
        # to do with the school's plan, so they are entitled by construction.
        if role not in BILLABLE_ROLES:
            enabled, school_free_until = SubscriptionService.get_settings(
                db, user.school_id
            )
            return _allow(
                "NON_BILLABLE_ROLE",
                subscriptions_enabled=enabled,
                school_free_until=school_free_until,
                school_id=user.school_id,
                role=role,
            )

        school_id = user.school_id
        if school_id is None:
            # Fail closed: a non-super-admin without tenant context is a
            # misconfigured account (get_current_active_user also rejects it).
            return _deny(
                "PAYMENT_REQUIRED", "SCHOOL_CONTEXT_MISSING", role=role
            )

        enabled, school_free_until = SubscriptionService.get_settings(db, school_id)

        # -- 2. School does not require subscriptions ---------------------
        if not enabled:
            return _allow(
                "SCHOOL_SUBSCRIPTIONS_DISABLED",
                subscriptions_enabled=False,
                school_id=school_id,
                role=role,
            )

        # -- 3. School-wide free period -----------------------------------
        if school_free_until is not None and now < school_free_until:
            return _allow(
                "SCHOOL_FREE",
                expires_at=school_free_until,
                subscriptions_enabled=True,
                school_free_until=school_free_until,
                school_id=school_id,
                role=role,
            )

        # -- 4. Individual free override ----------------------------------
        override = (
            db.query(UserSubscriptionOverride)
            .filter(
                UserSubscriptionOverride.user_id == user.id,
                UserSubscriptionOverride.override_type == "FREE",
            )
            .first()
        )
        override_active = False
        if override is not None:
            override_active = override.free_until is None or now < override.free_until
        if override_active:
            return _allow(
                "USER_FREE_OVERRIDE",
                expires_at=override.free_until,
                subscriptions_enabled=True,
                school_free_until=school_free_until,
                user_free_until=override.free_until,
                school_id=school_id,
                role=role,
            )

        # -- 5/6. Live subscription (any source: PAYMENT, ADMIN_GRANT,
        #         ROLE_PLAN, INDIVIDUAL_OVERRIDE, SCHOOL_OVERRIDE) ---------
        rows = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user.id,
                Subscription.status != "CANCELLED",
            )
            .order_by(Subscription.end_at.desc())
            .all()
        )

        latest_plan: Optional[SubscriptionPlan] = None
        for row in rows:
            if row.status == "ACTIVE" and row.start_at <= now < row.end_at:
                plan = row.plan  # relationship
                _maybe_send_expiry_reminders(db, user, row, now)
                return _allow(
                    str(row.source or "PAYMENT"),
                    expires_at=row.end_at,
                    plan=plan,
                    subscription_id=row.id,
                    subscriptions_enabled=True,
                    school_free_until=school_free_until,
                    school_id=school_id,
                    role=role,
                )
            if latest_plan is None and row.plan_id:
                latest_plan = row.plan

        # -- 7. Not entitled: report the most specific state --------------
        suspended_row = next(
            (r for r in rows if r.status == "SUSPENDED" and now < r.end_at), None
        )
        if suspended_row is not None:
            return _deny(
                "SUSPENDED",
                "SUSPENDED",
                expires_at=suspended_row.end_at,
                plan=suspended_row.plan,
                subscription_id=suspended_row.id,
                subscriptions_enabled=True,
                school_free_until=school_free_until,
                school_id=school_id,
                role=role,
            )

        cancelled_row = next((r for r in rows if r.status == "CANCELLED"), None)
        ended_row = next((r for r in rows if now >= r.end_at), None)
        if ended_row is not None:
            # Lazily notify "expired" once (de-duplicated on the exact text).
            expiry_text = ended_row.end_at.strftime("%d %b %Y")
            notify_user(
                db,
                user=user,
                title="Subscription expired",
                message=(
                    f"Your subscription expired on {expiry_text}. Choose a plan "
                    f"to restore access to your portal."
                ),
                reference_id=ended_row.id,
            )
            return _deny(
                "PAYMENT_REQUIRED",
                "EXPIRED",
                expires_at=ended_row.end_at,
                plan=ended_row.plan,
                subscription_id=ended_row.id,
                subscriptions_enabled=True,
                school_free_until=school_free_until,
                school_id=school_id,
                role=role,
            )
        if cancelled_row is not None:
            return _deny(
                "PAYMENT_REQUIRED",
                "CANCELLED",
                plan=cancelled_row.plan,
                subscription_id=cancelled_row.id,
                subscriptions_enabled=True,
                school_free_until=school_free_until,
                school_id=school_id,
                role=role,
            )
        if rows:
            # Stored EXPIRED/CANCELLED rows already handled above; anything
            # else with no valid window is treated as expired.
            first = rows[0]
            return _deny(
                "PAYMENT_REQUIRED",
                "EXPIRED",
                expires_at=first.end_at,
                plan=first.plan,
                subscription_id=first.id,
                subscriptions_enabled=True,
                school_free_until=school_free_until,
                school_id=school_id,
                role=role,
            )
        return _deny(
            "PAYMENT_REQUIRED",
            "NONE",
            subscriptions_enabled=True,
            school_free_until=school_free_until,
            school_id=school_id,
            role=role,
        )

    @staticmethod
    def require_access(db: Session, user: User) -> AccessStatus:
        """Raise 403 SUBSCRIPTION_REQUIRED unless the user is entitled now."""
        access = SubscriptionService.get_access_status(db, user)
        if not access.has_access:
            raise SubscriptionRequired(
                state=access.status,
                reason=access.reason,
                expires_at=access.expires_at,
            )
        return access

    # -----------------------------------------------------------------------
    # 2. Effective per-user status (listings/aggregates)
    # -----------------------------------------------------------------------

    @staticmethod
    def effective_status(db: Session, user: User, now: Optional[datetime] = None) -> str:
        """Entitlement-level status for UI lists: FREE | ACTIVE | SUSPENDED |
        EXPIRED | NONE. Ignores school-level switches (those are per school)."""
        now = now or utcnow()
        override = (
            db.query(UserSubscriptionOverride)
            .filter(
                UserSubscriptionOverride.user_id == user.id,
                UserSubscriptionOverride.override_type == "FREE",
            )
            .first()
        )
        if override is not None and (
            override.free_until is None or now < override.free_until
        ):
            return "FREE"
        rows = (
            db.query(Subscription)
            .filter(Subscription.user_id == user.id)
            .order_by(Subscription.end_at.desc())
            .all()
        )
        if not rows:
            return "NONE"
        if any(r.status == "ACTIVE" and r.start_at <= now < r.end_at for r in rows):
            return "ACTIVE"
        if any(r.status == "SUSPENDED" and now < r.end_at for r in rows):
            return "SUSPENDED"
        return "EXPIRED"  # has history, nothing live (expired/cancelled)

    # -----------------------------------------------------------------------
    # 3. Entitlement mutations (shared core for payment / grant / extend)
    # -----------------------------------------------------------------------

    @staticmethod
    def _time_active_row(db: Session, user_id: int, now: datetime) -> Optional[Subscription]:
        """A row whose window currently covers ``now`` (to extend in place)."""
        return (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status.in_(list(LIVE_STATUSES)),
                Subscription.start_at <= now,
                Subscription.end_at > now,
            )
            .order_by(Subscription.end_at.desc())
            .first()
        )

    @staticmethod
    def apply_entitlement(
        db: Session,
        *,
        user: User,
        plan: Optional[SubscriptionPlan],
        source: str,
        duration: Optional[Tuple[int, str]] = None,
        activate: bool = True,
        amount: Optional[Decimal] = None,
        currency: Optional[str] = None,
    ) -> Subscription:
        """Create/extend an entitlement following the renewal rules:

        * existing subscription still active -> extend ``end_at`` from the
          existing end (paid time is NEVER thrown away);
        * existing subscription expired      -> new row starting now;
        * no subscription                     -> new row starting now.

        Stale stored-ACTIVE rows are lazily flipped to EXPIRED here (status
        hygiene without needing a background job).
        """
        now = utcnow()
        if duration is not None:
            dv, du = duration
        elif plan is not None:
            dv, du = plan.duration_value, plan.duration_unit
        else:
            raise SubscriptionError(
                "INVALID_DURATION", "A plan or explicit duration is required"
            )

        row = SubscriptionService._time_active_row(db, user.id, now)
        if row is not None:
            row.end_at = add_duration(row.end_at, dv, du)
            if activate:
                row.status = "ACTIVE"
            if plan is not None and plan.id and row.plan_id != plan.id:
                row.plan_id = plan.id
            if amount is not None:
                row.amount = amount
                row.currency = currency
            db.add(row)
        else:
            # Preserve history: past rows are kept and marked EXPIRED, the
            # new period starts now in its own row.
            (
                db.query(Subscription)
                .filter(
                    Subscription.user_id == user.id,
                    Subscription.status == "ACTIVE",
                    Subscription.end_at <= now,
                )
                .update({"status": "EXPIRED"}, synchronize_session=False)
            )
            row = Subscription(
                school_id=user.school_id,
                user_id=user.id,
                plan_id=plan.id if plan is not None else None,
                status="ACTIVE" if activate else "SUSPENDED",
                start_at=now,
                end_at=add_duration(now, dv, du),
                source=source if source in SUBSCRIPTION_SOURCES else "ADMIN_GRANT",
                amount=amount,
                currency=currency,
            )
            db.add(row)
        db.flush()
        return row

    # -----------------------------------------------------------------------
    # 4. Audit
    # -----------------------------------------------------------------------

    @staticmethod
    def audit(
        db: Session,
        *,
        action: str,
        school_id: Optional[int],
        admin_id: Optional[int],
        user_id: Optional[int] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Append an audit row INSIDE the caller's transaction."""
        db.add(
            SubscriptionAuditLog(
                school_id=school_id,
                user_id=user_id,
                admin_id=admin_id,
                action=action,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
            )
        )

    @staticmethod
    def _platform_audit(
        db: Session,
        *,
        admin: Optional[User],
        school_id: Optional[int],
        action: str,
        resource_id: Optional[Any],
        details: Dict[str, Any],
    ) -> None:
        """Also mirror into the generic platform audit log (best-effort)."""
        write_audit_log(
            db,
            user_id=admin.id if admin else None,
            school_id=school_id,
            action=action,
            resource_type="Subscription",
            resource_id=resource_id,
            details=details,
        )

    # -----------------------------------------------------------------------
    # 5. Validation helpers (structured error codes)
    # -----------------------------------------------------------------------

    @staticmethod
    def get_school(db: Session, school_id: int) -> School:
        school = db.query(School).filter(School.id == school_id).first()
        if school is None:
            raise SubscriptionError("SCHOOL_NOT_FOUND", "School not found", 404)
        return school

    @staticmethod
    def get_user(db: Session, user_id: int) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise SubscriptionError("USER_NOT_FOUND", "User not found", 404)
        return user

    @staticmethod
    def get_plan(db: Session, plan_id: int) -> SubscriptionPlan:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if plan is None:
            raise SubscriptionError("PLAN_NOT_FOUND", "Plan not found", 404)
        return plan

    @staticmethod
    def validate_price(price: float) -> float:
        try:
            value = float(price)
        except (TypeError, ValueError):
            raise SubscriptionError("INVALID_PRICE", "Price must be a number")
        if value != value or value in (float("inf"), float("-inf")):
            raise SubscriptionError("INVALID_PRICE", "Price must be a finite number")
        if value < 0:
            raise SubscriptionError("INVALID_PRICE", "Price must not be negative")
        if value > 99_999_999.99:
            raise SubscriptionError("INVALID_PRICE", "Price is too large")
        return round(value, 2)

    @staticmethod
    def validate_duration(duration_value: Any, duration_unit: Any) -> Tuple[int, str]:
        if not isinstance(duration_value, int) or isinstance(duration_value, bool):
            raise SubscriptionError("INVALID_DURATION", "duration_value must be an integer")
        if duration_value < 1:
            raise SubscriptionError(
                "INVALID_DURATION",
                "duration_value must be at least 1 (0 means no duration)",
            )
        unit = str(duration_unit or "").upper()
        if unit not in DURATION_UNITS:
            raise SubscriptionError(
                "INVALID_DURATION",
                f"duration_unit must be one of: {', '.join(DURATION_UNITS)}",
            )
        return duration_value, unit

    @staticmethod
    def validate_plan_role(role: Any) -> str:
        value = str(role or "").upper()
        if value not in BILLABLE_ROLES:
            raise SubscriptionError(
                "INVALID_ROLE",
                f"role must be one of: {', '.join(BILLABLE_ROLES)}",
            )
        return value

    @staticmethod
    def _ensure_billable(target: User) -> None:
        role = str(getattr(target, "role", "") or "").upper()
        if role not in BILLABLE_ROLES:
            raise SubscriptionError(
                "NOT_BILLABLE_ROLE",
                "Subscription operations only apply to principals, teachers and students",
            )

    @staticmethod
    def ensure_plan_usable(
        db: Session, *, plan: SubscriptionPlan, target: User
    ) -> SubscriptionPlan:
        """Plan must be active, belong to the target's school AND role."""
        if not plan.is_active:
            raise SubscriptionError("PLAN_INACTIVE", "This plan is no longer available")
        if plan.school_id != target.school_id:
            raise SubscriptionError(
                "USER_NOT_IN_SCHOOL",
                "The plan belongs to a different school than the user",
            )
        if str(plan.role).upper() != str(target.role).upper():
            raise SubscriptionError(
                "PLAN_ROLE_MISMATCH",
                "The plan's role does not match the user's role",
            )
        return plan

    @staticmethod
    def _fmt_money(amount: Any, currency: str) -> str:
        try:
            return f"{float(amount):g} {currency}"
        except (TypeError, ValueError):
            return f"{amount} {currency}"

    @staticmethod
    def _fmt_duration(value: int, unit: str) -> str:
        unit_l = str(unit).lower()
        suffix = "" if value == 1 else "s"
        return f"{value} {unit_l}{suffix}"

    @classmethod
    def _plan_value(cls, plan: SubscriptionPlan) -> str:
        return (
            f"{plan.name}: {cls._fmt_money(plan.price, plan.currency)} / "
            f"{cls._fmt_duration(plan.duration_value, plan.duration_unit)}"
        )

    # -----------------------------------------------------------------------
    # 6. Plans (CRUD - deactivate, never delete)
    # -----------------------------------------------------------------------

    @staticmethod
    def create_plan(
        db: Session, *, school_id: int, payload: Any, admin: User
    ) -> SubscriptionPlan:
        school = SubscriptionService.get_school(db, school_id)
        role = SubscriptionService.validate_plan_role(payload.role)
        price = SubscriptionService.validate_price(payload.price)
        dv, du = SubscriptionService.validate_duration(
            payload.duration_value, payload.duration_unit
        )
        interval = str(payload.billing_interval or "CUSTOM").upper()
        if interval not in ("ONE_TIME", "WEEKLY", "MONTHLY", "QUARTERLY", "YEARLY", "CUSTOM"):
            interval = "CUSTOM"

        plan = SubscriptionPlan(
            school_id=school.id,
            role=role,
            name=payload.name.strip(),
            description=payload.description,
            price=Decimal(str(price)),
            currency=(payload.currency or "INR").upper(),
            billing_interval=interval,
            duration_value=dv,
            duration_unit=du,
            is_active=True,
        )
        db.add(plan)
        db.flush()
        SubscriptionService.audit(
            db,
            action="PLAN_CREATED",
            school_id=school.id,
            admin_id=admin.id,
            new_value=SubscriptionService._plan_value(plan),
            reason=getattr(payload, "reason", None),
        )
        db.commit()
        db.refresh(plan)
        SubscriptionService._platform_audit(
            db,
            admin=admin,
            school_id=school.id,
            action="CREATE",
            resource_id=plan.id,
            details={"role": role, "value": SubscriptionService._plan_value(plan)},
        )
        return plan

    @staticmethod
    def update_plan(
        db: Session, *, plan_id: int, payload: Any, admin: User
    ) -> SubscriptionPlan:
        plan = SubscriptionService.get_plan(db, plan_id)
        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise SubscriptionError("NO_CHANGES", "No changes supplied")

        old_value = SubscriptionService._plan_value(plan)

        if "price" in data and data["price"] is not None:
            plan.price = Decimal(str(SubscriptionService.validate_price(data["price"])))
        if "duration_value" in data and data["duration_value"] is not None:
            plan.duration_value = data["duration_value"]
        if "duration_unit" in data and data["duration_unit"] is not None:
            plan.duration_unit = str(data["duration_unit"]).upper()
        # Re-validate the pair whenever either half changed.
        if "duration_value" in data or "duration_unit" in data:
            plan.duration_value, plan.duration_unit = SubscriptionService.validate_duration(
                plan.duration_value, plan.duration_unit
            )
        if "name" in data and data["name"] is not None:
            plan.name = data["name"].strip()
        if "description" in data:
            plan.description = data["description"]
        if "currency" in data and data["currency"]:
            plan.currency = str(data["currency"]).upper()
        if "billing_interval" in data and data["billing_interval"]:
            plan.billing_interval = str(data["billing_interval"]).upper()
        if "is_active" in data and data["is_active"] is not None:
            plan.is_active = bool(data["is_active"])

        db.add(plan)
        db.flush()
        new_value = SubscriptionService._plan_value(plan)
        SubscriptionService.audit(
            db,
            action="PLAN_UPDATED",
            school_id=plan.school_id,
            admin_id=admin.id,
            old_value=old_value,
            new_value=new_value,
            reason=getattr(payload, "reason", None),
        )
        db.commit()
        db.refresh(plan)
        SubscriptionService._platform_audit(
            db,
            admin=admin,
            school_id=plan.school_id,
            action="UPDATE",
            resource_id=plan.id,
            details={"old": old_value, "new": new_value},
        )
        return plan

    @staticmethod
    def deactivate_plan(db: Session, *, plan_id: int, admin: User) -> SubscriptionPlan:
        plan = SubscriptionService.get_plan(db, plan_id)
        if not plan.is_active:
            # Idempotent: deactivating twice is not an error, just no-op audit.
            return plan
        plan.is_active = False
        db.add(plan)
        db.flush()
        SubscriptionService.audit(
            db,
            action="PLAN_DEACTIVATED",
            school_id=plan.school_id,
            admin_id=admin.id,
            old_value=SubscriptionService._plan_value(plan) + " (active)",
            new_value=SubscriptionService._plan_value(plan) + " (inactive)",
        )
        db.commit()
        db.refresh(plan)
        SubscriptionService._platform_audit(
            db,
            admin=admin,
            school_id=plan.school_id,
            action="UPDATE",
            resource_id=plan.id,
            details={"is_active": False},
        )
        return plan

    # -----------------------------------------------------------------------
    # 7. School settings (enable/disable + school-wide free)
    # -----------------------------------------------------------------------

    @staticmethod
    def _settings_row(
        db: Session, school_id: int, *, create: bool = False
    ) -> Optional[SchoolSubscriptionSettings]:
        row = (
            db.query(SchoolSubscriptionSettings)
            .filter(SchoolSubscriptionSettings.school_id == school_id)
            .first()
        )
        if row is None and create:
            row = SchoolSubscriptionSettings(
                school_id=school_id, subscriptions_enabled=False, free_until=None
            )
            db.add(row)
            db.flush()
        return row

    @staticmethod
    def update_school_settings(
        db: Session, *, school_id: int, payload: Any, admin: User
    ) -> SchoolSubscriptionSettings:
        school = SubscriptionService.get_school(db, school_id)
        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise SubscriptionError("NO_CHANGES", "No changes supplied")

        row = SubscriptionService._settings_row(db, school.id, create=True)
        now = utcnow()

        if "subscriptions_enabled" in data and data["subscriptions_enabled"] is not None:
            new_val = bool(data["subscriptions_enabled"])
            if new_val != row.subscriptions_enabled:
                row.subscriptions_enabled = new_val
                SubscriptionService.audit(
                    db,
                    action=(
                        "SCHOOL_SUBSCRIPTIONS_ENABLED"
                        if new_val
                        else "SCHOOL_SUBSCRIPTIONS_DISABLED"
                    ),
                    school_id=school.id,
                    admin_id=admin.id,
                    old_value="ENABLED" if not new_val else "DISABLED",
                    new_value="ENABLED" if new_val else "DISABLED",
                    reason=data.get("reason"),
                )

        if "free_until" in data:
            new_free = data["free_until"]
            old_free = row.free_until
            if new_free is not None and new_free.tzinfo is not None:
                from app.core.time_utils import as_utc_naive

                new_free = as_utc_naive(new_free)
            row.free_until = new_free
            was_active = old_free is not None and now < old_free
            is_active = new_free is not None and now < new_free
            if is_active and not was_active:
                action = "SCHOOL_FREE_GRANTED"
            elif was_active and not is_active:
                action = "SCHOOL_FREE_REMOVED"
            elif new_free != old_free:
                action = "SCHOOL_FREE_GRANTED" if is_active else "SCHOOL_FREE_REMOVED"
            else:
                action = None
            if action:
                SubscriptionService.audit(
                    db,
                    action=action,
                    school_id=school.id,
                    admin_id=admin.id,
                    old_value=old_free.isoformat() if old_free else None,
                    new_value=new_free.isoformat() if new_free else None,
                    reason=data.get("reason"),
                )

        db.add(row)
        db.commit()
        db.refresh(row)
        SubscriptionService._platform_audit(
            db,
            admin=admin,
            school_id=school.id,
            action="UPDATE",
            resource_id=school.id,
            details={
                "enabled": row.subscriptions_enabled,
                "free_until": row.free_until.isoformat() if row.free_until else None,
            },
        )
        return row

    # -----------------------------------------------------------------------
    # 8. Individual user overrides
    # -----------------------------------------------------------------------

    @staticmethod
    def create_override(
        db: Session, *, target: User, payload: Any, admin: User
    ) -> UserSubscriptionOverride:
        SubscriptionService._ensure_billable(target)
        otype = str(payload.override_type or "FREE").upper()
        if otype not in OVERRIDE_TYPES:
            raise SubscriptionError(
                "INVALID_OVERRIDE_TYPE",
                f"override_type must be one of: {', '.join(OVERRIDE_TYPES)}",
            )
        existing = (
            db.query(UserSubscriptionOverride)
            .filter(
                UserSubscriptionOverride.user_id == target.id,
                UserSubscriptionOverride.override_type == otype,
            )
            .first()
        )
        if existing is not None:
            raise SubscriptionError(
                "OVERRIDE_EXISTS",
                "User already has this override - update or remove it instead",
                409,
            )

        free_until = payload.free_until
        if free_until is not None and free_until.tzinfo is not None:
            from app.core.time_utils import as_utc_naive

            free_until = as_utc_naive(free_until)

        row = UserSubscriptionOverride(
            school_id=target.school_id,
            user_id=target.id,
            override_type=otype,
            free_until=free_until,
            reason=payload.reason,
            created_by=admin.id,
        )
        db.add(row)
        db.flush()
        SubscriptionService.audit(
            db,
            action="USER_FREE_GRANTED" if otype == "FREE" else f"USER_{otype}_GRANTED",
            school_id=target.school_id,
            admin_id=admin.id,
            user_id=target.id,
            new_value=f"FREE until {free_until.isoformat() if free_until else 'indefinite'}",
            reason=payload.reason,
        )
        db.commit()
        db.refresh(row)
        SubscriptionService._platform_audit(
            db,
            admin=admin,
            school_id=target.school_id,
            action="UPDATE",
            resource_id=target.id,
            details={"override": otype, "free_until": str(free_until)},
        )
        return row

    @staticmethod
    def update_override(
        db: Session, *, target: User, payload: Any, admin: User
    ) -> UserSubscriptionOverride:
        row = (
            db.query(UserSubscriptionOverride)
            .filter(
                UserSubscriptionOverride.user_id == target.id,
                UserSubscriptionOverride.override_type == "FREE",
            )
            .first()
        )
        if row is None:
            raise SubscriptionError("OVERRIDE_NOT_FOUND", "User has no active override", 404)
        data = payload.model_dump(exclude_unset=True)
        old_value = (
            f"FREE until {row.free_until.isoformat() if row.free_until else 'indefinite'}"
        )
        if "free_until" in data:
            new_free = data["free_until"]
            if new_free is not None and new_free.tzinfo is not None:
                from app.core.time_utils import as_utc_naive

                new_free = as_utc_naive(new_free)
            row.free_until = new_free
        if "reason" in data:
            row.reason = data["reason"]
        new_value = (
            f"FREE until {row.free_until.isoformat() if row.free_until else 'indefinite'}"
        )
        db.add(row)
        db.flush()
        SubscriptionService.audit(
            db,
            action="USER_FREE_GRANTED",
            school_id=target.school_id,
            admin_id=admin.id,
            user_id=target.id,
            old_value=old_value,
            new_value=new_value,
            reason=data.get("reason"),
        )
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def remove_override(db: Session, *, target: User, admin: User) -> None:
        row = (
            db.query(UserSubscriptionOverride)
            .filter(
                UserSubscriptionOverride.user_id == target.id,
                UserSubscriptionOverride.override_type == "FREE",
            )
            .first()
        )
        if row is None:
            raise SubscriptionError("OVERRIDE_NOT_FOUND", "User has no active override", 404)
        old_value = (
            f"FREE until {row.free_until.isoformat() if row.free_until else 'indefinite'}"
        )
        db.delete(row)
        db.flush()
        SubscriptionService.audit(
            db,
            action="USER_FREE_REMOVED",
            school_id=target.school_id,
            admin_id=admin.id,
            user_id=target.id,
            old_value=old_value,
            new_value="override removed",
        )
        db.commit()
        SubscriptionService._platform_audit(
            db,
            admin=admin,
            school_id=target.school_id,
            action="UPDATE",
            resource_id=target.id,
            details={"override_removed": True},
        )

    # -----------------------------------------------------------------------
    # 9. Manual subscription operations (grant/extend/cancel/suspend/restore)
    # -----------------------------------------------------------------------

    @staticmethod
    def grant(
        db: Session, *, target: User, plan_id: int, reason: Optional[str], admin: User
    ) -> Subscription:
        SubscriptionService._ensure_billable(target)
        plan = SubscriptionService.get_plan(db, plan_id)
        SubscriptionService.ensure_plan_usable(db, plan=plan, target=target)

        now = utcnow()
        live = SubscriptionService._time_active_row(db, target.id, now)
        old_value = (
            f"until {live.end_at.isoformat()}" if live is not None else "no active subscription"
        )

        row = SubscriptionService.apply_entitlement(
            db,
            user=target,
            plan=plan,
            source="ADMIN_GRANT",
            activate=True,
            amount=plan.price,
            currency=plan.currency,
        )
        SubscriptionService.audit(
            db,
            action="USER_SUBSCRIPTION_GRANTED",
            school_id=target.school_id,
            admin_id=admin.id,
            user_id=target.id,
            old_value=old_value,
            new_value=f"{SubscriptionService._plan_value(plan)} until {row.end_at.isoformat()}",
            reason=reason,
        )
        db.commit()
        db.refresh(row)
        SubscriptionService._platform_audit(
            db,
            admin=admin,
            school_id=target.school_id,
            action="UPDATE",
            resource_id=target.id,
            details={"granted_until": row.end_at.isoformat(), "plan_id": plan.id},
        )
        notify_user(
            db,
            user=target,
            title="Subscription activated",
            message=(
                f"Your subscription is active until "
                f"{row.end_at.strftime('%d %b %Y')}."
            ),
            reference_id=row.id,
        )
        return row

    @staticmethod
    def extend(
        db: Session, *, target: User, payload: Any, admin: User
    ) -> Subscription:
        SubscriptionService._ensure_billable(target)
        now = utcnow()

        plan: Optional[SubscriptionPlan] = None
        if payload.plan_id:
            plan = SubscriptionService.get_plan(db, payload.plan_id)
            SubscriptionService.ensure_plan_usable(db, plan=plan, target=target)
            duration = (plan.duration_value, plan.duration_unit)
        else:
            if payload.duration_value is None or payload.duration_unit is None:
                raise SubscriptionError(
                    "INVALID_DURATION",
                    "Provide plan_id or duration_value + duration_unit",
                )
            duration = SubscriptionService.validate_duration(
                payload.duration_value, payload.duration_unit
            )

        live = SubscriptionService._time_active_row(db, target.id, now)
        keep_suspended = live is not None and live.status == "SUSPENDED"
        if plan is None and live is not None and live.plan_id:
            plan = live.plan  # keep pointing at the same plan when extending it
        old_value = (
            f"until {live.end_at.isoformat()}" if live is not None else "no active subscription"
        )

        row = SubscriptionService.apply_entitlement(
            db,
            user=target,
            plan=plan,
            source="ADMIN_GRANT",
            duration=duration,
            activate=not keep_suspended,
        )
        SubscriptionService.audit(
            db,
            action="USER_SUBSCRIPTION_EXTENDED",
            school_id=target.school_id,
            admin_id=admin.id,
            user_id=target.id,
            old_value=old_value,
            new_value=(
                f"until {row.end_at.isoformat()} (+"
                f"{SubscriptionService._fmt_duration(*duration)})"
            ),
            reason=getattr(payload, "reason", None),
        )
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def _transition(
        db: Session,
        *,
        target: User,
        action: str,
        new_status: str,
        allowed_current: Sequence[str],
        not_found_message: str,
        reason: Optional[str],
        admin: User,
        notify_title: Optional[str] = None,
        prefer_time_valid: bool = True,
    ) -> Subscription:
        """Shared implementation for cancel/suspend/restore."""
        rows = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == target.id,
                Subscription.status.in_(list(allowed_current)),
            )
            .order_by(Subscription.end_at.desc())
            .all()
        )
        if not rows:
            raise SubscriptionError("SUBSCRIPTION_NOT_FOUND", not_found_message, 404)

        now = utcnow()
        row = None
        if prefer_time_valid:
            row = next((r for r in rows if r.end_at > now), None)
        row = row or rows[0]

        old_status = row.status
        if old_status == new_status:
            raise SubscriptionError(
                "SUBSCRIPTION_NOT_FOUND",
                f"Subscription is already {new_status.lower()}",
                404,
            )
        row.status = new_status
        db.add(row)
        db.flush()
        SubscriptionService.audit(
            db,
            action=action,
            school_id=target.school_id,
            admin_id=admin.id,
            user_id=target.id,
            old_value=f"{old_status} until {row.end_at.isoformat()}",
            new_value=f"{new_status} until {row.end_at.isoformat()}",
            reason=reason,
        )
        db.commit()
        db.refresh(row)
        SubscriptionService._platform_audit(
            db,
            admin=admin,
            school_id=target.school_id,
            action="UPDATE",
            resource_id=target.id,
            details={"subscription_status": new_status},
        )
        if notify_title:
            notify_user(
                db,
                user=target,
                title=notify_title,
                message=f"Your subscription is now {new_status.lower()}.",
                reference_id=row.id,
            )
        return row

    @classmethod
    def cancel(
        cls, db: Session, *, target: User, reason: Optional[str], admin: User
    ) -> Subscription:
        SubscriptionService._ensure_billable(target)
        return cls._transition(
            db,
            target=target,
            action="USER_SUBSCRIPTION_CANCELLED",
            new_status="CANCELLED",
            allowed_current=("ACTIVE", "SUSPENDED"),
            not_found_message="No active subscription to cancel",
            reason=reason,
            admin=admin,
            notify_title="Subscription cancelled",
        )

    @classmethod
    def suspend(
        cls, db: Session, *, target: User, reason: Optional[str], admin: User
    ) -> Subscription:
        SubscriptionService._ensure_billable(target)
        return cls._transition(
            db,
            target=target,
            action="USER_SUBSCRIPTION_SUSPENDED",
            new_status="SUSPENDED",
            allowed_current=("ACTIVE",),
            not_found_message="No active subscription to suspend",
            reason=reason,
            admin=admin,
        )

    @classmethod
    def restore(
        cls, db: Session, *, target: User, reason: Optional[str], admin: User
    ) -> Subscription:
        SubscriptionService._ensure_billable(target)
        return cls._transition(
            db,
            target=target,
            action="USER_SUBSCRIPTION_RESTORED",
            new_status="ACTIVE",
            allowed_current=("SUSPENDED", "CANCELLED", "EXPIRED"),
            not_found_message="No suspended, cancelled or expired subscription to restore",
            reason=reason,
            admin=admin,
            notify_title="Subscription activated",
        )

    # -----------------------------------------------------------------------
    # 10. Bulk operations (single transaction, school-scoped, audited)
    # -----------------------------------------------------------------------

    @staticmethod
    def bulk_operation(
        db: Session, *, school_id: int, payload: Any, admin: User
    ) -> Dict[str, Any]:
        """Run one access-changing action across many users of ONE school.

        * shared inputs are validated once, up front;
        * each user runs inside a SAVEPOINT: a per-user failure rolls back
          only that user, successes stay in the outer transaction;
        * everything commits atomically at the end;
        * every change gets a subscription audit row (same transaction);
        * tenant scoping is enforced per user (school_id must match).
        """
        school = SubscriptionService.get_school(db, school_id)
        action = str(payload.action or "").upper()
        if action not in (
            "FREE_UNTIL",
            "REMOVE_FREE",
            "ASSIGN_PLAN",
            "EXTEND",
            "SUSPEND",
            "RESTORE",
            "CANCEL",
        ):
            raise SubscriptionError(
                "INVALID_BULK_ACTION",
                "action must be FREE_UNTIL | REMOVE_FREE | ASSIGN_PLAN | EXTEND | SUSPEND | RESTORE | CANCEL",
            )

        # ---- validate shared inputs ONCE before touching anything --------
        plan: Optional[SubscriptionPlan] = None
        duration: Optional[Tuple[int, str]] = None
        if action == "ASSIGN_PLAN":
            if payload.plan_id is None:
                raise SubscriptionError("PLAN_NOT_FOUND", "plan_id is required", 400)
            plan = SubscriptionService.get_plan(db, payload.plan_id)
            if plan.school_id != school.id:
                raise SubscriptionError(
                    "USER_NOT_IN_SCHOOL", "The plan belongs to a different school"
                )
            if not plan.is_active:
                raise SubscriptionError("PLAN_INACTIVE", "This plan is no longer available")
        elif action == "EXTEND":
            if payload.duration_value is None or payload.duration_unit is None:
                raise SubscriptionError(
                    "INVALID_DURATION", "duration_value + duration_unit are required"
                )
            duration = SubscriptionService.validate_duration(
                payload.duration_value, payload.duration_unit
            )
        elif action == "FREE_UNTIL":
            if payload.free_until is None:
                raise SubscriptionError(
                    "INVALID_FREE_UNTIL", "free_until is required for FREE_UNTIL"
                )

        user_ids = list(dict.fromkeys(payload.user_ids))  # de-dupe, keep order
        succeeded: List[int] = []
        failed: List[Dict[str, Any]] = []

        for uid in user_ids:
            try:
                # SAVEPOINT: a failure below undoes only this user's work.
                with db.begin_nested():
                    target = db.query(User).filter(User.id == uid).first()
                    if target is None:
                        raise SubscriptionError("USER_NOT_FOUND", "User not found", 404)
                    if target.school_id != school.id:
                        # Never let a bulk payload cross tenants.
                        raise SubscriptionError(
                            "USER_NOT_IN_SCHOOL", "User does not belong to this school"
                        )
                    if str(target.role).upper() not in BILLABLE_ROLES:
                        raise SubscriptionError(
                            "NOT_BILLABLE_ROLE",
                            "User's role cannot hold a subscription",
                        )

                    if action == "FREE_UNTIL":
                        existing = (
                            db.query(UserSubscriptionOverride)
                            .filter(
                                UserSubscriptionOverride.user_id == target.id,
                                UserSubscriptionOverride.override_type == "FREE",
                            )
                            .first()
                        )
                        old_value = None
                        if existing is not None:
                            old_value = (
                                "FREE until "
                                + (
                                    existing.free_until.isoformat()
                                    if existing.free_until
                                    else "indefinite"
                                )
                            )
                            existing.free_until = payload.free_until
                            if payload.reason:
                                existing.reason = payload.reason
                            db.add(existing)
                        else:
                            db.add(
                                UserSubscriptionOverride(
                                    school_id=school.id,
                                    user_id=target.id,
                                    override_type="FREE",
                                    free_until=payload.free_until,
                                    reason=payload.reason,
                                    created_by=admin.id,
                                )
                            )
                        db.flush()
                        SubscriptionService.audit(
                            db,
                            action="USER_FREE_GRANTED",
                            school_id=school.id,
                            admin_id=admin.id,
                            user_id=target.id,
                            old_value=old_value,
                            new_value=f"FREE until {payload.free_until.isoformat()}",
                            reason=payload.reason,
                        )

                    elif action == "REMOVE_FREE":
                        existing = (
                            db.query(UserSubscriptionOverride)
                            .filter(
                                UserSubscriptionOverride.user_id == target.id,
                                UserSubscriptionOverride.override_type == "FREE",
                            )
                            .first()
                        )
                        if existing is None:
                            raise SubscriptionError(
                                "OVERRIDE_NOT_FOUND", "User has no active override", 404
                            )
                        old_value = (
                            "FREE until "
                            + (
                                existing.free_until.isoformat()
                                if existing.free_until
                                else "indefinite"
                            )
                        )
                        db.delete(existing)
                        db.flush()
                        SubscriptionService.audit(
                            db,
                            action="USER_FREE_REMOVED",
                            school_id=school.id,
                            admin_id=admin.id,
                            user_id=target.id,
                            old_value=old_value,
                            new_value="override removed",
                            reason=payload.reason,
                        )

                    elif action == "ASSIGN_PLAN":
                        SubscriptionService.ensure_plan_usable(
                            db, plan=plan, target=target
                        )
                        row_obj = SubscriptionService.apply_entitlement(
                            db,
                            user=target,
                            plan=plan,
                            source="ADMIN_GRANT",
                            activate=True,
                            amount=plan.price,
                            currency=plan.currency,
                        )
                        SubscriptionService.audit(
                            db,
                            action="USER_SUBSCRIPTION_GRANTED",
                            school_id=school.id,
                            admin_id=admin.id,
                            user_id=target.id,
                            new_value=(
                                f"{SubscriptionService._plan_value(plan)} "
                                f"until {row_obj.end_at.isoformat()}"
                            ),
                            reason=payload.reason,
                        )

                    elif action == "EXTEND":
                        live = SubscriptionService._time_active_row(
                            db, target.id, utcnow()
                        )
                        keep_suspended = live is not None and live.status == "SUSPENDED"
                        row_obj = SubscriptionService.apply_entitlement(
                            db,
                            user=target,
                            plan=live.plan if live is not None and live.plan_id else None,
                            source="ADMIN_GRANT",
                            duration=duration,
                            activate=not keep_suspended,
                        )
                        SubscriptionService.audit(
                            db,
                            action="USER_SUBSCRIPTION_EXTENDED",
                            school_id=school.id,
                            admin_id=admin.id,
                            user_id=target.id,
                            new_value=f"until {row_obj.end_at.isoformat()}",
                            reason=payload.reason,
                        )

                    else:  # SUSPEND | RESTORE | CANCEL
                        sub_action = {
                            "SUSPEND": (
                                "USER_SUBSCRIPTION_SUSPENDED",
                                "SUSPENDED",
                                ("ACTIVE",),
                                "No active subscription to suspend",
                            ),
                            "RESTORE": (
                                "USER_SUBSCRIPTION_RESTORED",
                                "ACTIVE",
                                ("SUSPENDED", "CANCELLED", "EXPIRED"),
                                "No suspended/cancelled subscription to restore",
                            ),
                            "CANCEL": (
                                "USER_SUBSCRIPTION_CANCELLED",
                                "CANCELLED",
                                ("ACTIVE", "SUSPENDED"),
                                "No active subscription to cancel",
                            ),
                        }[action]
                        rows = (
                            db.query(Subscription)
                            .filter(
                                Subscription.user_id == target.id,
                                Subscription.status.in_(list(sub_action[2])),
                            )
                            .order_by(Subscription.end_at.desc())
                            .all()
                        )
                        now = utcnow()
                        valid = next((r for r in rows if r.end_at > now), None)
                        sub_row = valid or (rows[0] if rows else None)
                        if sub_row is None:
                            raise SubscriptionError(
                                "SUBSCRIPTION_NOT_FOUND", sub_action[3], 404
                            )
                        old_status = sub_row.status
                        if old_status == sub_action[1]:
                            raise SubscriptionError(
                                "SUBSCRIPTION_NOT_FOUND",
                                f"Subscription is already {old_status.lower()}",
                                404,
                            )
                        sub_row.status = sub_action[1]
                        db.add(sub_row)
                        SubscriptionService.audit(
                            db,
                            action=sub_action[0],
                            school_id=school.id,
                            admin_id=admin.id,
                            user_id=target.id,
                            old_value=f"{old_status} until {sub_row.end_at.isoformat()}",
                            new_value=(
                                f"{sub_action[1]} until {sub_row.end_at.isoformat()}"
                            ),
                            reason=payload.reason,
                        )

                succeeded.append(uid)
            except SubscriptionError as exc:  # per-user structured failure
                failed.append(
                    {
                        "user_id": uid,
                        "code": exc.code,
                        "message": exc.detail.get("message", "Failed"),
                    }
                )
            except Exception:  # noqa: BLE001 - never leak DB internals
                failed.append(
                    {"user_id": uid, "code": "INTERNAL_ERROR", "message": "Unexpected error"}
                )

        db.commit()
        SubscriptionService._platform_audit(
            db,
            admin=admin,
            school_id=school.id,
            action="UPDATE",
            resource_id=school.id,
            details={
                "bulk_action": action,
                "requested": len(user_ids),
                "succeeded": len(succeeded),
                "failed": len(failed),
            },
        )
        return {
            "action": action,
            "requested": len(user_ids),
            "succeeded": succeeded,
            "failed": failed,
        }

    # -----------------------------------------------------------------------
    # 11. Status hygiene
    # -----------------------------------------------------------------------

    @staticmethod
    def sync_stale_statuses(db: Session, now: Optional[datetime] = None) -> int:
        """Rewrite stored ACTIVE rows whose window has passed to EXPIRED.

        Correctness never depends on this (access checks read the clock),
        but keeping the stored status honest makes lists/metrics trivial.
        """
        now = now or utcnow()
        updated = (
            db.query(Subscription)
            .filter(
                Subscription.status == "ACTIVE",
                Subscription.end_at <= now,
            )
            .update({"status": "EXPIRED"}, synchronize_session=False)
        )
        if updated:
            db.commit()
        return int(updated or 0)

    # -----------------------------------------------------------------------
    # 12. School listings / summaries (real aggregates only)
    # -----------------------------------------------------------------------

    @staticmethod
    def _school_status(
        *,
        enabled: bool,
        free_until: Optional[datetime],
        now: datetime,
        needed_roles: set,
        planned_roles: set,
    ) -> str:
        if not enabled:
            return "DISABLED"
        if free_until is not None and now < free_until:
            return "FREE"
        if not needed_roles:
            return "ACTIVE"
        if needed_roles <= planned_roles:
            return "ACTIVE"
        if needed_roles & planned_roles:
            return "PARTIAL"
        return "NO_PLANS"

    @staticmethod
    def _summarize_schools(
        db: Session, schools: Sequence[School]
    ) -> List[Dict[str, Any]]:
        """Real aggregates for a page of schools (GROUP BY counts only)."""
        now = utcnow()
        school_ids = [s.id for s in schools]
        if not school_ids:
            return []

        # Real GROUP BY aggregates - no fabricated numbers.
        role_counts: Dict[int, Dict[str, int]] = {}
        for sid, role, count in (
            db.query(User.school_id, User.role, func.count(User.id))
            .filter(User.school_id.in_(school_ids))
            .group_by(User.school_id, User.role)
            .all()
        ):
            role_counts.setdefault(sid, {})[str(role)] = count

        settings_map = {
            row.school_id: row
            for row in db.query(SchoolSubscriptionSettings)
            .filter(SchoolSubscriptionSettings.school_id.in_(school_ids))
            .all()
        }

        planned: Dict[int, set] = {}
        for sid, role in (
            db.query(SubscriptionPlan.school_id, SubscriptionPlan.role)
            .filter(
                SubscriptionPlan.school_id.in_(school_ids),
                SubscriptionPlan.is_active.is_(True),
            )
            .distinct()
            .all()
        ):
            planned.setdefault(sid, set()).add(str(role))

        active_map: Dict[int, int] = {}
        for sid, count in (
            db.query(Subscription.school_id, func.count(func.distinct(Subscription.user_id)))
            .filter(
                Subscription.school_id.in_(school_ids),
                Subscription.status == "ACTIVE",
                Subscription.start_at <= now,
                Subscription.end_at > now,
            )
            .group_by(Subscription.school_id)
            .all()
        ):
            active_map[sid] = count

        expired_map: Dict[int, int] = {}
        for sid, count in (
            db.query(Subscription.school_id, func.count(func.distinct(Subscription.user_id)))
            .filter(
                Subscription.school_id.in_(school_ids),
                or_(
                    Subscription.status == "EXPIRED",
                    and_(Subscription.status == "ACTIVE", Subscription.end_at <= now),
                ),
            )
            .group_by(Subscription.school_id)
            .all()
        ):
            expired_map[sid] = count

        items: List[Dict[str, Any]] = []
        for school in schools:
            settings = settings_map.get(school.id)
            enabled = bool(settings and settings.subscriptions_enabled)
            free_until = settings.free_until if settings else None
            counts = role_counts.get(school.id, {})
            needed = {r for r in counts if r in BILLABLE_ROLES}
            items.append(
                {
                    "school_id": school.id,
                    "name": school.name,
                    "code": school.code,
                    "is_active": school.is_active,
                    "subscriptions_enabled": enabled,
                    "free_until": free_until,
                    "status": SubscriptionService._school_status(
                        enabled=enabled,
                        free_until=free_until,
                        now=now,
                        needed_roles=needed,
                        planned_roles=planned.get(school.id, set()),
                    ),
                    "students": counts.get("STUDENT", 0),
                    "teachers": counts.get("TEACHER", 0),
                    "others": sum(
                        counts.get(r, 0) for r in counts if r in ("PRINCIPAL", "SUPER_ADMIN")
                    ),
                    "active_subscriptions": active_map.get(school.id, 0),
                    "expired_subscriptions": expired_map.get(school.id, 0),
                }
            )
        return items

    @staticmethod
    def list_schools(
        db: Session,
        *,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        query = db.query(School)
        if search:
            needle = f"%{search.strip()}%"
            query = query.filter(or_(School.name.ilike(needle), School.code.ilike(needle)))
        total = query.count()
        schools = query.order_by(School.name).offset(skip).limit(limit).all()
        return total, SubscriptionService._summarize_schools(db, schools)

    @staticmethod
    def get_school_detail(db: Session, school_id: int) -> Dict[str, Any]:
        school = SubscriptionService.get_school(db, school_id)
        items = SubscriptionService._summarize_schools(db, [school])
        return items[0]

    # -----------------------------------------------------------------------
    # 13. Role summaries (counts by entitlement status + plans)
    # -----------------------------------------------------------------------

    @staticmethod
    def _role_buckets(
        db: Session, school_id: int, role: Optional[str], now: datetime
    ) -> Dict[str, set]:
        """Bucket every user of the school (optionally one role) into
        FREE/ACTIVE/SUSPENDED/EXPIRED/NONE using the same precedence as
        ``effective_status``."""
        user_query = db.query(User.id, User.role).filter(User.school_id == school_id)
        if role:
            user_query = user_query.filter(User.role == role)
        user_rows = user_query.all()
        all_ids = {uid for uid, _ in user_rows}

        buckets: Dict[str, set] = {
            "free": set(),
            "active": set(),
            "suspended": set(),
            "expired": set(),
            "none": set(all_ids),
        }
        if not all_ids:
            return buckets

        free_ids = {
            uid
            for (uid,) in db.query(UserSubscriptionOverride.user_id)
            .filter(
                UserSubscriptionOverride.user_id.in_(all_ids),
                UserSubscriptionOverride.override_type == "FREE",
                or_(
                    UserSubscriptionOverride.free_until.is_(None),
                    UserSubscriptionOverride.free_until > now,
                ),
            )
            .all()
        }
        sub_rows = db.query(
            Subscription.user_id, Subscription.status, Subscription.start_at, Subscription.end_at
        ).filter(Subscription.user_id.in_(all_ids))

        active_ids: set = set()
        suspended_ids: set = set()
        expired_ids: set = set()
        for uid, sub_status, start_at, end_at in sub_rows.all():
            if sub_status == "ACTIVE" and start_at <= now < end_at:
                active_ids.add(uid)
            elif sub_status == "SUSPENDED" and now < end_at:
                suspended_ids.add(uid)
            else:
                expired_ids.add(uid)  # EXPIRED / CANCELLED / passed windows

        # Exclusive buckets, precedence: FREE > ACTIVE > SUSPENDED > EXPIRED.
        buckets["free"] = free_ids & all_ids
        buckets["active"] = (active_ids - buckets["free"]) & all_ids
        buckets["suspended"] = (suspended_ids - buckets["free"] - buckets["active"]) & all_ids
        buckets["expired"] = (
            expired_ids - buckets["free"] - buckets["active"] - buckets["suspended"]
        ) & all_ids
        buckets["none"] = all_ids - (
            buckets["free"] | buckets["active"] | buckets["suspended"] | buckets["expired"]
        )
        return buckets

    @staticmethod
    def get_school_roles(db: Session, school_id: int) -> Dict[str, Any]:
        school = SubscriptionService.get_school(db, school_id)
        now = utcnow()
        enabled, free_until = SubscriptionService.get_settings(db, school_id)

        role_user_counts: Dict[str, int] = {}
        for role, count in (
            db.query(User.role, func.count(User.id))
            .filter(
                User.school_id == school_id,
                User.role.in_(list(BILLABLE_ROLES)),
            )
            .group_by(User.role)
            .all()
        ):
            role_user_counts[str(role)] = count

        plan_counts: Dict[str, int] = {}
        for role, count in (
            db.query(SubscriptionPlan.role, func.count(SubscriptionPlan.id))
            .filter(
                SubscriptionPlan.school_id == school_id,
                SubscriptionPlan.is_active.is_(True),
            )
            .group_by(SubscriptionPlan.role)
            .all()
        ):
            plan_counts[str(role)] = count

        buckets = SubscriptionService._role_buckets(db, school_id, None, now)

        roles = []
        for role in BILLABLE_ROLES:
            # Buckets are keyed by user id; intersect with this role's users.
            role_ids = {
                uid
                for (uid,) in db.query(User.id).filter(
                    User.school_id == school_id, User.role == role
                )
            }
            roles.append(
                {
                    "role": role,
                    "total_users": role_user_counts.get(role, 0),
                    "active_plans": plan_counts.get(role, 0),
                    "active": len(buckets["active"] & role_ids),
                    "free": len(buckets["free"] & role_ids),
                    "expired": len(buckets["expired"] & role_ids),
                    "suspended": len(buckets["suspended"] & role_ids),
                    "none": len(buckets["none"] & role_ids),
                }
            )
        return {
            "school_id": school.id,
            "school_name": school.name,
            "subscriptions_enabled": enabled,
            "free_until": free_until,
            "roles": roles,
        }

    @staticmethod
    def get_role_detail(db: Session, school_id: int, role: str) -> Dict[str, Any]:
        role = SubscriptionService.validate_plan_role(role)
        data = SubscriptionService.get_school_roles(db, school_id)
        plans = (
            db.query(SubscriptionPlan)
            .filter(
                SubscriptionPlan.school_id == school_id,
                SubscriptionPlan.role == role,
            )
            .order_by(SubscriptionPlan.is_active.desc(), SubscriptionPlan.price.asc())
            .all()
        )
        data["roles"] = [r for r in data["roles"] if r["role"] == role]
        data["plans"] = plans
        return data

    # -----------------------------------------------------------------------
    # 14. School user listing with per-user entitlement status
    # -----------------------------------------------------------------------

    @staticmethod
    def list_school_users(
        db: Session,
        school_id: int,
        *,
        role: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        now = utcnow()
        query = db.query(User.id, User.display_name, User.mobile, User.role).filter(
            User.school_id == school_id
        )
        if role:
            query = query.filter(User.role == str(role).upper())
        if search:
            needle = f"%{search.strip()}%"
            query = query.filter(
                or_(User.display_name.ilike(needle), User.mobile.ilike(needle))
            )
        user_rows = query.order_by(User.display_name.asc()).all()
        if not user_rows:
            return 0, []

        ids = [uid for uid, _, _, _ in user_rows]
        buckets = SubscriptionService._role_buckets(
            db, school_id, str(role).upper() if role else None, now
        )

        state_by_id: Dict[int, str] = {}
        for state in ("free", "active", "suspended", "expired", "none"):
            for uid in buckets[state]:
                state_by_id[uid] = state.upper()

        if status_filter:
            wanted = str(status_filter).upper()
            user_rows = [row for row in user_rows if state_by_id.get(row[0]) == wanted]

        total = len(user_rows)
        page = user_rows[skip : skip + limit]
        if not page:
            return total, []

        page_ids = [uid for uid, _, _, _ in page]

        # Detail for the page only: latest subscription + active override.
        sub_rows = (
            db.query(Subscription)
            .filter(Subscription.user_id.in_(page_ids))
            .order_by(Subscription.end_at.desc())
            .all()
        )
        sub_by_user: Dict[int, Subscription] = {}
        for row in sub_rows:
            sub_by_user.setdefault(row.user_id, row)
        override_by_user = {
            o.user_id: o
            for o in db.query(UserSubscriptionOverride)
            .filter(
                UserSubscriptionOverride.user_id.in_(page_ids),
                UserSubscriptionOverride.override_type == "FREE",
            )
            .all()
        }

        items: List[Dict[str, Any]] = []
        for uid, display_name, mobile, urole in page:
            state = state_by_id.get(uid, "NONE")
            sub = sub_by_user.get(uid)
            override = override_by_user.get(uid)
            items.append(
                {
                    "user_id": uid,
                    "display_name": display_name,
                    "mobile": mobile,
                    "role": str(urole),
                    "subscription_status": state,
                    "plan_name": sub.plan.name if (sub is not None and sub.plan) else None,
                    "expires_at": (
                        override.free_until
                        if state == "FREE" and override is not None
                        else (sub.end_at if sub is not None else None)
                    ),
                    "override_free_until": override.free_until if override else None,
                }
            )
        return total, items

    # -----------------------------------------------------------------------
    # 15. Single user detail (status + history + payments + audit)
    # -----------------------------------------------------------------------

    @staticmethod
    def get_user_detail(db: Session, user_id: int) -> Dict[str, Any]:
        target = SubscriptionService.get_user(db, user_id)
        now = utcnow()
        SubscriptionService.sync_stale_statuses(db, now)

        access = SubscriptionService.get_access_status(db, target)

        subs = (
            db.query(Subscription)
            .filter(Subscription.user_id == target.id)
            .order_by(Subscription.end_at.desc())
            .limit(50)
            .all()
        )
        live = next(
            (
                s
                for s in subs
                if s.status in LIVE_STATUSES and s.start_at <= now < s.end_at
            ),
            None,
        )
        current = live or (subs[0] if subs else None)

        override = (
            db.query(UserSubscriptionOverride)
            .filter(
                UserSubscriptionOverride.user_id == target.id,
                UserSubscriptionOverride.override_type == "FREE",
            )
            .first()
        )
        payments = (
            db.query(SubscriptionPayment)
            .filter(SubscriptionPayment.user_id == target.id)
            .order_by(SubscriptionPayment.created_at.desc())
            .limit(50)
            .all()
        )
        audit_rows = (
            db.query(SubscriptionAuditLog)
            .filter(SubscriptionAuditLog.user_id == target.id)
            .order_by(SubscriptionAuditLog.created_at.desc())
            .limit(50)
            .all()
        )
        school = db.query(School).filter(School.id == target.school_id).first()

        return {
            "user_id": target.id,
            "display_name": target.display_name,
            "role": str(target.role),
            "mobile": target.mobile,
            "school_id": target.school_id,
            "school_name": school.name if school else None,
            "access": access.as_response(),
            "subscription": current,
            "override": override,
            "history": subs,
            "payments": payments,
            "audit": audit_rows,
        }

    # -----------------------------------------------------------------------
    # 16. Metrics (real COUNT aggregates, nothing invented)
    # -----------------------------------------------------------------------

    @staticmethod
    def get_metrics(db: Session) -> Dict[str, int]:
        now = utcnow()
        total_schools = db.query(func.count(School.id)).scalar() or 0
        enabled = (
            db.query(func.count(SchoolSubscriptionSettings.id))
            .filter(SchoolSubscriptionSettings.subscriptions_enabled.is_(True))
            .scalar()
            or 0
        )
        free_now = (
            db.query(func.count(SchoolSubscriptionSettings.id))
            .filter(
                SchoolSubscriptionSettings.subscriptions_enabled.is_(True),
                SchoolSubscriptionSettings.free_until.isnot(None),
                SchoolSubscriptionSettings.free_until > now,
            )
            .scalar()
            or 0
        )
        active_subs = (
            db.query(func.count(func.distinct(Subscription.user_id)))
            .filter(
                Subscription.status == "ACTIVE",
                Subscription.start_at <= now,
                Subscription.end_at > now,
            )
            .scalar()
            or 0
        )
        expired_subs = (
            db.query(func.count(func.distinct(Subscription.user_id)))
            .filter(
                or_(
                    Subscription.status == "EXPIRED",
                    and_(Subscription.status == "ACTIVE", Subscription.end_at <= now),
                )
            )
            .scalar()
            or 0
        )
        pending = (
            db.query(func.count(SubscriptionPayment.id))
            .filter(SubscriptionPayment.status == "PENDING")
            .scalar()
            or 0
        )
        success = (
            db.query(func.count(SubscriptionPayment.id))
            .filter(SubscriptionPayment.status == "SUCCESS")
            .scalar()
            or 0
        )
        failed = (
            db.query(func.count(SubscriptionPayment.id))
            .filter(SubscriptionPayment.status.in_(["FAILED", "CANCELLED"]))
            .scalar()
            or 0
        )
        return {
            "total_schools": int(total_schools),
            "subscriptions_enabled": int(enabled),
            "schools_currently_free": int(free_now),
            "active_user_subscriptions": int(active_subs),
            "expired_user_subscriptions": int(expired_subs),
            "pending_payments": int(pending),
            "successful_payments": int(success),
            "failed_payments": int(failed),
        }

    # -----------------------------------------------------------------------
    # 17. User-facing /me views
    # -----------------------------------------------------------------------

    @staticmethod
    def me(db: Session, user: User) -> Dict[str, Any]:
        now = utcnow()
        SubscriptionService.sync_stale_statuses(db, now)
        access = SubscriptionService.get_access_status(db, user)

        subs = (
            db.query(Subscription)
            .filter(Subscription.user_id == user.id)
            .order_by(Subscription.end_at.desc())
            .all()
        )
        live = next(
            (
                s
                for s in subs
                if s.status in LIVE_STATUSES and s.start_at <= now < s.end_at
            ),
            None,
        )
        current = live or (subs[0] if subs else None)
        override = (
            db.query(UserSubscriptionOverride)
            .filter(
                UserSubscriptionOverride.user_id == user.id,
                UserSubscriptionOverride.override_type == "FREE",
            )
            .first()
        )
        school = (
            db.query(School).filter(School.id == user.school_id).first()
            if user.school_id
            else None
        )
        return {
            "user_id": user.id,
            "role": str(user.role),
            "school_id": user.school_id,
            "school_name": school.name if school else None,
            "access": access.as_response(),
            "subscription": current,
            "override": override,
        }

    @staticmethod
    def me_plans(db: Session, user: User) -> Dict[str, Any]:
        from app.services.payment import PaymentService

        enabled, free_until = SubscriptionService.get_settings(db, user.school_id)
        school = (
            db.query(School).filter(School.id == user.school_id).first()
            if user.school_id
            else None
        )
        plans: List[SubscriptionPlan] = []
        role = str(user.role).upper()
        if role in BILLABLE_ROLES and user.school_id:
            plans = (
                db.query(SubscriptionPlan)
                .filter(
                    SubscriptionPlan.school_id == user.school_id,
                    SubscriptionPlan.role == role,
                    SubscriptionPlan.is_active.is_(True),
                )
                .order_by(SubscriptionPlan.price.asc())
                .all()
            )
        return {
            "school_id": user.school_id,
            "school_name": school.name if school else None,
            "subscriptions_enabled": enabled,
            "free_until": free_until,
            "role": role,
            "plans": plans,
            "mock_payments_enabled": PaymentService.mock_payments_enabled(),
            "payment_provider": "INTERNAL",
        }

    @staticmethod
    def history(db: Session, user: User) -> List[Subscription]:
        return (
            db.query(Subscription)
            .filter(Subscription.user_id == user.id)
            .order_by(Subscription.end_at.desc())
            .limit(100)
            .all()
        )

    @staticmethod
    def payments_for(db: Session, user: User) -> List[SubscriptionPayment]:
        return (
            db.query(SubscriptionPayment)
            .filter(SubscriptionPayment.user_id == user.id)
            .order_by(SubscriptionPayment.created_at.desc())
            .limit(100)
            .all()
        )
