# backend-python/app/schemas/subscription.py
"""Pydantic schemas for the subscription domain (access, schools, overrides,
manual operations, bulk operations, audit and the user-facing /me views).

Structured errors are NOT modelled here: routers raise
``HTTPException(status_code=..., detail={"code": "SCHOOL_NOT_FOUND", ...})``
so the frontend can branch on machine-readable codes while still showing a
human message.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.subscription_payment import SubscriptionPaymentResponse


# ---------------------------------------------------------------------------
# Access resolution
# ---------------------------------------------------------------------------


class PlanBrief(BaseModel):
    """Compact plan reference embedded in access/history responses."""

    id: int
    name: str
    price: float
    currency: str
    billing_interval: str
    duration_value: int
    duration_unit: str


class AccessStatusResponse(BaseModel):
    """Result of SubscriptionService.get_access_status().

    Precedence (one authoritative resolver, used everywhere):
      1. SUPER_ADMIN                       -> reason SUPER_ADMIN
      2. school subscriptions disabled     -> reason SCHOOL_SUBSCRIPTIONS_DISABLED
      3. active school-wide free override  -> reason SCHOOL_FREE
      4. active individual free override   -> reason USER_FREE_OVERRIDE
      5. active individual subscription    -> reason = subscription source
      6. active role-plan entitlement      -> reason = ROLE_PLAN (source)
      7. otherwise                         -> PAYMENT_REQUIRED
    """

    has_access: bool
    status: str = Field(..., description="ACTIVE | PAYMENT_REQUIRED | SUSPENDED")
    reason: str = Field(..., description="Why access was granted/denied")
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


# ---------------------------------------------------------------------------
# Subscriptions (entitlements)
# ---------------------------------------------------------------------------


class SubscriptionResponse(BaseModel):
    id: int
    school_id: int
    user_id: int
    plan_id: Optional[int] = None
    plan: Optional[PlanBrief] = None
    status: str
    start_at: datetime
    end_at: datetime
    source: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    total: int
    items: List[SubscriptionResponse]


# ---------------------------------------------------------------------------
# School settings
# ---------------------------------------------------------------------------


class SchoolSubscriptionSettingsResponse(BaseModel):
    school_id: int
    subscriptions_enabled: bool
    free_until: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SchoolSubscriptionSettingsUpdate(BaseModel):
    subscriptions_enabled: Optional[bool] = None
    # Omitted -> unchanged; explicit null -> remove the free period.
    free_until: Optional[datetime] = None
    reason: Optional[str] = Field(None, max_length=500)


# ---------------------------------------------------------------------------
# User overrides
# ---------------------------------------------------------------------------


class UserOverrideResponse(BaseModel):
    id: int
    school_id: int
    user_id: int
    override_type: str
    free_until: Optional[datetime] = None
    reason: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserOverrideCreate(BaseModel):
    override_type: str = Field("FREE", max_length=30, description="FREE (extensible)")
    free_until: Optional[datetime] = Field(
        None, description="Access until this instant (UTC); null = indefinite"
    )
    reason: Optional[str] = Field(None, max_length=500)


class UserOverrideUpdate(BaseModel):
    free_until: Optional[datetime] = None
    reason: Optional[str] = Field(None, max_length=500)


# ---------------------------------------------------------------------------
# Manual subscription operations
# ---------------------------------------------------------------------------


class GrantSubscriptionRequest(BaseModel):
    plan_id: int = Field(..., description="Active plan (must belong to the user's school+role)")
    reason: Optional[str] = Field(None, max_length=500)


class ExtendSubscriptionRequest(BaseModel):
    # Either a plan (duration taken from it) or an explicit duration.
    plan_id: Optional[int] = None
    duration_value: Optional[int] = None
    duration_unit: Optional[str] = Field(None, max_length=10, description="DAY | MONTH | YEAR")
    reason: Optional[str] = Field(None, max_length=500)


class SubscriptionStateRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


# ---------------------------------------------------------------------------
# School / role / user listings (Super Admin)
# ---------------------------------------------------------------------------


class SchoolSubscriptionSummary(BaseModel):
    school_id: int
    name: str
    code: Optional[str] = None
    is_active: Optional[bool] = None
    subscriptions_enabled: bool = False
    free_until: Optional[datetime] = None
    # DISABLED | FREE | ACTIVE | PARTIAL | NO_PLANS
    status: str
    students: int = 0
    teachers: int = 0
    others: int = 0
    active_subscriptions: int = 0
    expired_subscriptions: int = 0


class SchoolSubscriptionListResponse(BaseModel):
    total: int
    items: List[SchoolSubscriptionSummary]


class RoleSummary(BaseModel):
    role: str
    total_users: int = 0
    active_plans: int = 0
    active: int = 0
    free: int = 0
    expired: int = 0
    suspended: int = 0
    none: int = 0


class SchoolRolesResponse(BaseModel):
    school_id: int
    school_name: str
    subscriptions_enabled: bool
    free_until: Optional[datetime] = None
    roles: List[RoleSummary]


class SchoolRoleDetailResponse(SchoolRolesResponse):
    plans: List["SubscriptionPlanResponse"] = []


class SchoolUserSubscriptionItem(BaseModel):
    user_id: int
    display_name: str
    mobile: str
    role: str
    subscription_status: str  # ACTIVE | FREE | EXPIRED | SUSPENDED | NONE
    plan_name: Optional[str] = None
    expires_at: Optional[datetime] = None
    override_free_until: Optional[datetime] = None


class SchoolUsersListResponse(BaseModel):
    total: int
    items: List[SchoolUserSubscriptionItem]


class SubscriptionAuditLogResponse(BaseModel):
    id: int
    school_id: Optional[int] = None
    user_id: Optional[int] = None
    admin_id: Optional[int] = None
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserSubscriptionDetailResponse(BaseModel):
    user_id: int
    display_name: str
    role: str
    mobile: str
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    access: AccessStatusResponse
    subscription: Optional[SubscriptionResponse] = None
    override: Optional[UserOverrideResponse] = None
    history: List[SubscriptionResponse] = []
    payments: List[SubscriptionPaymentResponse] = []
    audit: List[SubscriptionAuditLogResponse] = []


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------

BULK_ACTIONS = (
    "FREE_UNTIL",      # requires free_until
    "REMOVE_FREE",     # remove individual free overrides
    "ASSIGN_PLAN",     # requires plan_id
    "EXTEND",          # requires duration_value + duration_unit
    "SUSPEND",
    "RESTORE",
    "CANCEL",
)


class BulkOperationRequest(BaseModel):
    action: str = Field(..., max_length=30, description=" | ".join(BULK_ACTIONS))
    user_ids: List[int] = Field(..., min_length=1, max_length=500)
    free_until: Optional[datetime] = None
    plan_id: Optional[int] = None
    duration_value: Optional[int] = None
    duration_unit: Optional[str] = Field(None, max_length=10)
    reason: Optional[str] = Field(None, max_length=500)


class BulkOperationFailure(BaseModel):
    user_id: int
    code: str
    message: str


class BulkOperationResponse(BaseModel):
    action: str
    requested: int
    succeeded: List[int]
    failed: List[BulkOperationFailure]


# ---------------------------------------------------------------------------
# Metrics (real aggregates only)
# ---------------------------------------------------------------------------


class SubscriptionMetricsResponse(BaseModel):
    total_schools: int
    subscriptions_enabled: int
    schools_currently_free: int
    active_user_subscriptions: int
    expired_user_subscriptions: int
    pending_payments: int
    successful_payments: int
    failed_payments: int


# ---------------------------------------------------------------------------
# User-facing /me views
# ---------------------------------------------------------------------------


class MeSubscriptionResponse(BaseModel):
    user_id: int
    role: str
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    access: AccessStatusResponse
    subscription: Optional[SubscriptionResponse] = None
    override: Optional[UserOverrideResponse] = None


class MePlansResponse(BaseModel):
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    subscriptions_enabled: bool = False
    free_until: Optional[datetime] = None
    role: str
    plans: List["SubscriptionPlanResponse"] = []
    mock_payments_enabled: bool = False
    payment_provider: str = "INTERNAL"


# Resolve forward references (plans referenced from subscription.py while
# subscription_plan.py does not import this module).
from app.schemas.subscription_plan import SubscriptionPlanResponse  # noqa: E402

SchoolRoleDetailResponse.model_rebuild()
MePlansResponse.model_rebuild()
