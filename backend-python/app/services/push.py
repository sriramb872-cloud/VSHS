# app/services/push.py
"""Best-effort Web Push delivery (VAPID, free, no third-party service).

Every notification created through ``CRUDNotification.create`` is mirrored
to the browsers of the users who may see it in-app. The recipient set
mirrors ``CRUDNotification._visible_query`` - it is never wider - and is
always scoped to the notification's ``school_id`` (tenant isolation).

A push failure must never break notification creation: every entry point
swallows its own errors, same best-effort philosophy as
``subscription.notify_user``.
"""
from __future__ import annotations

import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional

import pywebpush
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.section import Section
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.user import User
from app.schemas.push import PushKeys

logger = logging.getLogger(__name__)

# --- Tunables / policy -------------------------------------------------------

#: Same active-account check as ``deps.get_current_active_user``.
ACTIVE_ACCOUNT_STATUS = "ACTIVE"

#: Who receives a school-wide PUBLIC push.
PUBLIC_PUSH_ROLES = ("STUDENT", "TEACHER", "PRINCIPAL")

#: Who receives a STAFF_ONLY push (when it is not addressed to one user).
STAFF_PUSH_ROLES = ("TEACHER", "PRINCIPAL")

#: SUPER_ADMIN receives push ONLY for notifications addressed directly to it
#: (``user_id`` set). School-wide pushes would be far too noisy on a platform
#: admin's device. Flip to False to include super admins everywhere.
SUPER_ADMIN_PUSH_DIRECT_ONLY = True

#: Max stored subscriptions per user; the oldest is deleted beyond this.
MAX_SUBSCRIPTIONS_PER_USER = 10

#: Push body truncation length.
BODY_TRUNCATE_AT = 140

#: HTTP 404/410 from the push service mean the subscription is gone.
GONE_STATUS_CODES = (404, 410)

#: How long the push service should keep trying to deliver.
PUSH_TTL_SECONDS = 3600
PUSH_TIMEOUT_SECONDS = 10.0

#: When True the dispatch runs inline in the calling thread. Tests flip this
#: on so assertions are deterministic; production leaves it off.
DISPATCH_INLINE = False

#: Fire-and-forget executor. Threads are joined by an atexit hook, so a
#: pending dispatch still completes when the worker shuts down.
_PUSH_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="webpush")


# --- Config helpers ----------------------------------------------------------


def push_enabled() -> bool:
    """True only when push is switched on AND both VAPID keys are set."""
    return bool(
        settings.PUSH_ENABLED and settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY
    )


# --- Recipient resolution ----------------------------------------------------


def _role_value(role) -> str:
    """Normalise a User.role (plain str or enum member) to its value."""
    return str(getattr(role, "value", role) or "").upper()


def _notifications_url(role: str) -> str:
    normalized = _role_value(role)
    if normalized not in ("SUPER_ADMIN", "PRINCIPAL", "TEACHER", "STUDENT"):
        normalized = "STUDENT"
    return f"/{normalized.lower()}/notifications"


def _super_admin_push_allowed(notification: Notification) -> bool:
    """True when a SUPER_ADMIN may receive this notification's push."""
    if not SUPER_ADMIN_PUSH_DIRECT_ONLY:
        return True
    return notification.user_id is not None


def _without_sender(recipients: List[User], sender_id: Optional[int]) -> List[User]:
    if sender_id is None:
        return recipients
    return [u for u in recipients if u.id != sender_id]


def _class_recipients(
    db: Session, school_id: int, target_class_id: Optional[int]
) -> List[User]:
    """Active students enrolled in ``target_class_id`` (same school)."""
    if not target_class_id:
        return []
    # The section must belong to the notification's school: a cross-tenant
    # section id must never widen the audience.
    section = (
        db.query(Section)
        .filter(Section.id == target_class_id, Section.school_id == school_id)
        .first()
    )
    if section is None:
        return []
    student_user_ids = [
        row[0]
        for row in (
            db.query(Student.user_id)
            .join(StudentEnrollment, StudentEnrollment.student_id == Student.id)
            .filter(
                StudentEnrollment.section_id == target_class_id,
                Student.school_id == school_id,
            )
            .all()
        )
    ]
    if not student_user_ids:
        return []
    return (
        db.query(User)
        .filter(
            User.school_id == school_id,
            User.role == "STUDENT",
            User.is_active == ACTIVE_ACCOUNT_STATUS,
            User.id.in_(student_user_ids),
        )
        .all()
    )


def _student_recipients(
    db: Session, school_id: int, target_student_id: Optional[int]
) -> List[User]:
    """The user account behind ``target_student_id`` (same school)."""
    if not target_student_id:
        return []
    student = (
        db.query(Student)
        .filter(Student.id == target_student_id, Student.school_id == school_id)
        .first()
    )
    if student is None or not student.user_id:
        return []
    return (
        db.query(User)
        .filter(
            User.id == student.user_id,
            User.is_active == ACTIVE_ACCOUNT_STATUS,
        )
        .all()
    )


def resolve_recipients(db: Session, notification: Notification) -> List[User]:
    """The users who may receive a Web Push for this notification.

    Mirrors ``CRUDNotification._visible_query`` - never wider - and is
    always scoped to the notification's ``school_id`` (tenant isolation).
    """
    school_id = notification.school_id
    sender_id = notification.sender_id

    # Direct (user_id set): ONLY that user, whatever the type. This is what
    # keeps STAFF_ONLY rows that the in-app list shows school-wide from
    # being pushed to every teacher.
    if notification.user_id:
        recipients = (
            db.query(User)
            .filter(
                User.id == notification.user_id,
                User.is_active == ACTIVE_ACCOUNT_STATUS,
            )
            .all()
        )
        return _without_sender(recipients, sender_id)

    # Platform-level rows (school_id NULL) have no school-wide audience.
    if school_id is None:
        return []

    ntype = (notification.notification_type or "").upper()
    base = db.query(User).filter(
        User.school_id == school_id,
        User.is_active == ACTIVE_ACCOUNT_STATUS,
    )
    if not _super_admin_push_allowed(notification):
        base = base.filter(User.role != "SUPER_ADMIN")

    if ntype == "PUBLIC":
        recipients = base.filter(User.role.in_(PUBLIC_PUSH_ROLES)).all()
    elif ntype == "STAFF_ONLY":
        recipients = base.filter(User.role.in_(STAFF_PUSH_ROLES)).all()
    elif ntype in ("CLASS_ONLY", "ONLY_FOR_CLASS"):
        recipients = _class_recipients(db, school_id, notification.target_class_id)
    elif ntype == "ONLY_FOR_STUDENT":
        recipients = _student_recipients(db, school_id, notification.target_student_id)
    else:
        # Unknown type (e.g. SLIP_TEST, which bypasses crud create anyway):
        # fail closed - no push.
        recipients = []

    return _without_sender(recipients, sender_id)


# --- Payload -----------------------------------------------------------------


def _payload_for(notification: Notification, user: User) -> dict:
    body = (notification.message or "").strip()
    if len(body) > BODY_TRUNCATE_AT:
        body = body[: BODY_TRUNCATE_AT - 3].rstrip() + "..."
    return {
        "title": notification.title,
        "body": body,
        "url": _notifications_url(user.role),
        "notification_id": notification.id,
        "tag": f"n-{notification.id}",
    }


# --- Sending -----------------------------------------------------------------


def _send(db: Session, subscription: PushSubscription, payload: dict) -> None:
    """Deliver one push. Never raises; updates ``last_used_at`` on success."""
    try:
        pywebpush.webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload, separators=(",", ":")),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            ttl=PUSH_TTL_SECONDS,
            timeout=PUSH_TIMEOUT_SECONDS,
        )
    except pywebpush.WebPushException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in GONE_STATUS_CODES:
            # The push service forgot this subscription (or the user cleared
            # site data) - drop it so we stop sending into the void.
            db.delete(subscription)
            db.commit()
            return
        # Never log the endpoint or the keys: they identify a device.
        logger.warning("Web Push delivery failed (status=%s)", status_code)
        return
    except Exception:
        logger.warning("Web Push delivery failed", exc_info=True)
        return
    subscription.last_used_at = datetime.utcnow()
    db.commit()


def dispatch_notification(notification_id: int) -> None:
    """Deliver the push for one notification. Never raises.

    Opens its OWN session (never the request's) and swallows every error:
    a push failure must never break notification creation.
    """
    if not push_enabled():
        return
    db = None
    try:
        db = SessionLocal()
        notification = (
            db.query(Notification).filter(Notification.id == notification_id).first()
        )
        if notification is None:
            return
        recipients = resolve_recipients(db, notification)
        if not recipients:
            return
        subscriptions = (
            db.query(PushSubscription)
            .filter(PushSubscription.user_id.in_([u.id for u in recipients]))
            .all()
        )
        if not subscriptions:
            return
        payloads = {u.id: _payload_for(notification, u) for u in recipients}
        for subscription in subscriptions:
            _send(db, subscription, payloads[subscription.user_id])
    except Exception:
        logger.warning(
            "Web Push dispatch failed for notification %s", notification_id, exc_info=True
        )
    finally:
        if db is not None:
            db.close()


def schedule_push(notification_id: int) -> None:
    """Fire-and-forget dispatch. Never raises, never blocks the request."""
    if not settings.PUSH_ENABLED:
        return
    if DISPATCH_INLINE:
        dispatch_notification(notification_id)
        return
    try:
        _PUSH_EXECUTOR.submit(dispatch_notification, notification_id)
    except Exception:
        logger.warning(
            "Failed to schedule Web Push dispatch for notification %s",
            notification_id,
            exc_info=True,
        )


# --- Subscription management (API layer) --------------------------------------


def get_public_key() -> dict:
    """The VAPID public key the browser needs to subscribe (or "")."""
    return {
        "public_key": settings.VAPID_PUBLIC_KEY or "",
        "enabled": push_enabled(),
    }


def _endpoint_hash(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def _enforce_subscription_cap(db: Session, user_id: int) -> None:
    """Keep at most MAX_SUBSCRIPTIONS_PER_USER rows; delete the oldest."""
    count = (
        db.query(PushSubscription).filter(PushSubscription.user_id == user_id).count()
    )
    if count < MAX_SUBSCRIPTIONS_PER_USER:
        return
    oldest = (
        db.query(PushSubscription)
        .filter(PushSubscription.user_id == user_id)
        .order_by(PushSubscription.created_at.asc(), PushSubscription.id.asc())
        .first()
    )
    if oldest is not None:
        db.delete(oldest)


def subscribe(
    db: Session,
    *,
    user: User,
    endpoint: str,
    keys: PushKeys,
    user_agent: Optional[str] = None,
) -> dict:
    """Upsert a browser subscription for ``user`` (shared-device safe)."""
    if not push_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications are not enabled on this server",
        )
    if not endpoint.lower().startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Push endpoints must use https",
        )
    endpoint_hash = _endpoint_hash(endpoint)
    row = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint_hash == endpoint_hash)
        .first()
    )
    if row is not None:
        # Shared school device: the same endpoint can be bound to a
        # different account after a re-login. Reassign instead of duplicating.
        row.user_id = user.id
        row.p256dh = keys.p256dh
        row.auth = keys.auth
        row.user_agent = (user_agent or "")[:255] or None
    else:
        _enforce_subscription_cap(db, user.id)
        row = PushSubscription(
            user_id=user.id,
            endpoint=endpoint,
            endpoint_hash=endpoint_hash,
            p256dh=keys.p256dh,
            auth=keys.auth,
            user_agent=(user_agent or "")[:255] or None,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "subscribed", "subscription_id": row.id}


def unsubscribe(db: Session, *, user: User, endpoint: str) -> dict:
    """Delete the caller's subscription for ``endpoint`` (idempotent)."""
    row = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.endpoint_hash == _endpoint_hash(endpoint),
            PushSubscription.user_id == user.id,
        )
        .first()
    )
    if row is not None:
        db.delete(row)
        db.commit()
    return {"status": "unsubscribed"}
