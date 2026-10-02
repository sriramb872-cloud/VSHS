# backend-python/app/schemas/subscription_plan.py
"""Pydantic schemas for subscription plans (pricing per role per school).

Validation policy: field *types* are enforced here (a 422 for garbage JSON),
while business validation (INVALID_PRICE / INVALID_DURATION / PLAN_INACTIVE
...) happens in the service/router so the API returns structured error codes
the frontend can act on.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SubscriptionPlanBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Plan display name")
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., description="Price in the plan's currency (e.g. 3.00 for ₹3)")
    currency: str = Field("INR", min_length=3, max_length=3)
    billing_interval: str = Field(
        "CUSTOM",
        max_length=20,
        description="Informational cadence: ONE_TIME|WEEKLY|MONTHLY|QUARTERLY|YEARLY|CUSTOM",
    )
    duration_value: int = Field(..., description="Length of the plan in duration_unit units")
    duration_unit: str = Field(..., max_length=10, description="DAY | MONTH | YEAR")
    is_active: bool = Field(True, description="Inactive plans cannot be purchased or assigned")


class SubscriptionPlanCreate(SubscriptionPlanBase):
    role: str = Field(..., max_length=20, description="PRINCIPAL | TEACHER | STUDENT")


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    billing_interval: Optional[str] = Field(None, max_length=20)
    duration_value: Optional[int] = None
    duration_unit: Optional[str] = Field(None, max_length=10)
    is_active: Optional[bool] = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: int
    school_id: int
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionPlanListResponse(BaseModel):
    total: int
    items: List[SubscriptionPlanResponse]
