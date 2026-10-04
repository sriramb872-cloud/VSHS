# backend-python/app/routers/v1/subscription_plans.py
"""Subscription plan management (Super Admin only).

Plans are always school-scoped: the ``/schools/{school_id}/plans`` route
verifies the school exists, and every plan lookup is by plan id (which
belongs to exactly one school), so a plan from one school can never be
read or edited through another school's routes.

``SubscriptionService.create_plan`` / ``update_plan`` / ``deactivate_plan``
write a ``subscription_audit_log`` row and a platform audit-log row inside
the same transaction as the change itself.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_subscription_admin
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.schemas.subscription_plan import (
    SubscriptionPlanCreate,
    SubscriptionPlanListResponse,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
)
from app.services.subscription import SubscriptionService

router = APIRouter(
    prefix="/subscription",
    tags=["subscription-plans"],
)


@router.get("/plans", response_model=SubscriptionPlanListResponse)
def list_plans(
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
):
    """All plans across all schools (Super Admin audit view)."""
    items = db.query(SubscriptionPlan).order_by(
        SubscriptionPlan.school_id, SubscriptionPlan.role, SubscriptionPlan.price
    )
    return {"total": items.count(), "items": items.all()}


@router.post(
    "/schools/{school_id}/plans",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_plan(
    school_id: int,
    payload: SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
) -> SubscriptionPlanResponse:
    """Create a role plan for one school (price / currency / duration)."""
    return SubscriptionService.create_plan(
        db, school_id=school_id, payload=payload, admin=admin
    )


@router.patch("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
def update_plan(
    plan_id: int,
    payload: SubscriptionPlanUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
) -> SubscriptionPlanResponse:
    """Update price / currency / duration / name / description / is_active."""
    return SubscriptionService.update_plan(
        db, plan_id=plan_id, payload=payload, admin=admin
    )


@router.post("/plans/{plan_id}/deactivate", response_model=SubscriptionPlanResponse)
def deactivate_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_subscription_admin),
) -> SubscriptionPlanResponse:
    """Retire a plan (idempotent).

    Historical payments, subscriptions and audit logs are never deleted or
    rewritten when a plan is deactivated.
    """
    return SubscriptionService.deactivate_plan(db, plan_id=plan_id, admin=admin)
