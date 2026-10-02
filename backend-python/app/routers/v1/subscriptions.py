# backend-python/app/routers/v1/subscriptions.py
"""Subscription API (management + user-facing).

Authorization map:
  * ``/schools...``, ``/users/{id}...``, ``/metrics`` - SUPER_ADMIN only
    (``require_subscription_admin`` -> 403 UNAUTHORIZED_SUBSCRIPTION_ACTION).
  * ``/me...`` and ``/payments...`` - any authenticated user, ALWAYS scoped
    to the token's own identity (``school_id``/``user_id`` are never taken
    from the client). These stay reachable when the subscription has
    expired - the user must never be locked out of renewing.

Error style: ``detail = {"code": "...", "message": "..."}`` for the
subscription domain so the frontend can branch on stable codes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps import get_db, get_current_active_user, require_subscription_admin
from app.models.user import User
from app.schemas.subscription import (
    BulkOperationResponse,
    BulkOperationRequest,
    ExtendSubscriptionRequest,
    GrantSubscriptionRequest,
    MePlansResponse,
    MeSubscriptionResponse,
    SchoolRoleDetailResponse,
    SchoolRolesResponse,
    SchoolSubscriptionListResponse,
    SchoolSubscriptionSettingsResponse,
    SchoolSubscriptionSettingsUpdate,
    SchoolSubscriptionSummary,
    SchoolUsersListResponse,
    SubscriptionListResponse,
    SubscriptionMetricsResponse,
    SubscriptionResponse,
    SubscriptionStateRequest,
    UserOverrideCreate,
    UserOverrideResponse,
    UserOverrideUpdate,
    UserSubscriptionDetailResponse,
)
from app.schemas.subscription_payment import (
    MockCheckoutRequest,
    PaymentCreateRequest,
    SubscriptionPaymentListResponse,
    SubscriptionPaymentResponse,
)
from app.services.payment import PaymentService
from app.services.subscription import SubscriptionService

router = APIRouter(prefix="/subscription", tags=["Subscriptions"])


# ---------------------------------------------------------------------------
# School-level (Super Admin)
# ---------------------------------------------------------------------------


@router.get("/schools", response_model=SchoolSubscriptionListResponse)
def list_schools(
    search: Optional[str] = Query(None, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    """Subscription summary for every school (real aggregates only)."""
    total, items = SubscriptionService.list_schools(
        db, search=search, skip=skip, limit=limit
    )
    return {"total": total, "items": items}


@router.get("/schools/{school_id}", response_model=SchoolSubscriptionSummary)
def get_school(
    school_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    return SubscriptionService.get_school_detail(db, school_id)


@router.get(
    "/schools/{school_id}/settings",
    response_model=SchoolSubscriptionSettingsResponse,
)
def get_school_settings(
    school_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    SubscriptionService.get_school(db, school_id)
    enabled, free_until = SubscriptionService.get_settings(db, school_id)
    return {
        "school_id": school_id,
        "subscriptions_enabled": enabled,
        "free_until": free_until,
    }


@router.patch(
    "/schools/{school_id}/settings",
    response_model=SchoolSubscriptionSettingsResponse,
)
def update_school_settings(
    school_id: int,
    payload: SchoolSubscriptionSettingsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    row = SubscriptionService.update_school_settings(
        db, school_id=school_id, payload=payload, admin=admin
    )
    return {
        "school_id": school_id,
        "subscriptions_enabled": row.subscriptions_enabled,
        "free_until": row.free_until,
        "updated_at": row.updated_at,
    }


# ---------------------------------------------------------------------------
# Role views (Super Admin)
# ---------------------------------------------------------------------------


@router.get("/schools/{school_id}/roles", response_model=SchoolRolesResponse)
def list_school_roles(
    school_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    return SubscriptionService.get_school_roles(db, school_id)


@router.get(
    "/schools/{school_id}/roles/{role}", response_model=SchoolRoleDetailResponse
)
def get_school_role(
    school_id: int,
    role: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    return SubscriptionService.get_role_detail(db, school_id, role)


# ---------------------------------------------------------------------------
# School user listing (Super Admin)
# ---------------------------------------------------------------------------


@router.get("/schools/{school_id}/users", response_model=SchoolUsersListResponse)
def list_school_users(
    school_id: int,
    role: Optional[str] = Query(None, max_length=20),
    status_filter: Optional[str] = Query(None, alias="status", max_length=20),
    search: Optional[str] = Query(None, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    SubscriptionService.get_school(db, school_id)
    total, items = SubscriptionService.list_school_users(
        db,
        school_id,
        role=role,
        status_filter=status_filter,
        search=search,
        skip=skip,
        limit=limit,
    )
    return {"total": total, "items": items}


# ---------------------------------------------------------------------------
# User overrides + manual subscription operations (Super Admin)
# ---------------------------------------------------------------------------


@router.get("/users/{user_id}", response_model=UserSubscriptionDetailResponse)
def get_user_subscription(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    return SubscriptionService.get_user_detail(db, user_id)


@router.post(
    "/users/{user_id}/override",
    response_model=UserOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user_override(
    user_id: int,
    payload: UserOverrideCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    target = SubscriptionService.get_user(db, user_id)
    return SubscriptionService.create_override(
        db, target=target, payload=payload, admin=admin
    )


@router.patch("/users/{user_id}/override", response_model=UserOverrideResponse)
def update_user_override(
    user_id: int,
    payload: UserOverrideUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    target = SubscriptionService.get_user(db, user_id)
    return SubscriptionService.update_override(
        db, target=target, payload=payload, admin=admin
    )


@router.delete(
    "/users/{user_id}/override",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user_override(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    target = SubscriptionService.get_user(db, user_id)
    SubscriptionService.remove_override(db, target=target, admin=admin)
    return None


@router.post(
    "/users/{user_id}/grant",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def grant_subscription(
    user_id: int,
    payload: GrantSubscriptionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    target = SubscriptionService.get_user(db, user_id)
    return SubscriptionService.grant(
        db,
        target=target,
        plan_id=payload.plan_id,
        reason=payload.reason,
        admin=admin,
    )


@router.post("/users/{user_id}/extend", response_model=SubscriptionResponse)
def extend_subscription(
    user_id: int,
    payload: ExtendSubscriptionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    target = SubscriptionService.get_user(db, user_id)
    return SubscriptionService.extend(db, target=target, payload=payload, admin=admin)


@router.post("/users/{user_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    user_id: int,
    payload: SubscriptionStateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    target = SubscriptionService.get_user(db, user_id)
    return SubscriptionService.cancel(
        db, target=target, reason=payload.reason, admin=admin
    )


@router.post("/users/{user_id}/suspend", response_model=SubscriptionResponse)
def suspend_subscription(
    user_id: int,
    payload: SubscriptionStateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    target = SubscriptionService.get_user(db, user_id)
    return SubscriptionService.suspend(
        db, target=target, reason=payload.reason, admin=admin
    )


@router.post("/users/{user_id}/restore", response_model=SubscriptionResponse)
def restore_subscription(
    user_id: int,
    payload: SubscriptionStateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    target = SubscriptionService.get_user(db, user_id)
    return SubscriptionService.restore(
        db, target=target, reason=payload.reason, admin=admin
    )


# ---------------------------------------------------------------------------
# Bulk operations (Super Admin)
# ---------------------------------------------------------------------------


@router.post(
    "/schools/{school_id}/bulk",
    response_model=BulkOperationResponse,
    status_code=status.HTTP_201_CREATED,
)
def bulk_subscription_operation(
    school_id: int,
    payload: BulkOperationRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    return SubscriptionService.bulk_operation(
        db, school_id=school_id, payload=payload, admin=admin
    )


# ---------------------------------------------------------------------------
# Metrics (Super Admin) - real database aggregates only
# ---------------------------------------------------------------------------


@router.get("/metrics", response_model=SubscriptionMetricsResponse)
def subscription_metrics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    return SubscriptionService.get_metrics(db)


# ---------------------------------------------------------------------------
# User-facing (any authenticated user; never blocked by a lock screen)
# ---------------------------------------------------------------------------


@router.get("/me", response_model=MeSubscriptionResponse)
def my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return SubscriptionService.me(db, current_user)


@router.get("/me/plans", response_model=MePlansResponse)
def my_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return SubscriptionService.me_plans(db, current_user)


@router.get("/me/history", response_model=SubscriptionListResponse)
def my_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items = SubscriptionService.history(db, current_user)
    return {"total": len(items), "items": items}


@router.get("/me/payments", response_model=SubscriptionPaymentListResponse)
def my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items = SubscriptionService.payments_for(db, current_user)
    return {"total": len(items), "items": items}


# ---------------------------------------------------------------------------
# Payments (mock provider in Phase 1; Razorpay plugs into the same flow)
# ---------------------------------------------------------------------------


@router.post(
    "/payments",
    response_model=SubscriptionPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payload: PaymentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return PaymentService.serialize(
        PaymentService.create_checkout(
            db, user=current_user, plan_id=payload.plan_id
        )
    )


@router.post("/payments/{payment_id}/mock/complete", response_model=SubscriptionPaymentResponse)
def complete_mock_payment(
    payment_id: int,
    payload: MockCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Development checkout completion.

    Gated by the mock provider (unavailable when ENVIRONMENT=production).
    The client only reports the simulated provider outcome; the server
    verifies the signed provider payload before activating anything.
    """
    return PaymentService.serialize(
        PaymentService.complete_mock_checkout(
            db, user=current_user, payment_id=payment_id, outcome=payload.outcome
        )
    )


@router.post("/payments/{payment_id}/cancel", response_model=SubscriptionPaymentResponse)
def cancel_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return PaymentService.serialize(
        PaymentService.cancel_pending(db, user=current_user, payment_id=payment_id)
    )
