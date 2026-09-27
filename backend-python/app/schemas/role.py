"""Role schemas for the Super Admin role-management screen."""

from typing import List, Optional

from pydantic import BaseModel, Field


class RoleSummary(BaseModel):
    """One entry of the role catalogue.

    `name` is a member of :class:`app.models.role.UserRole`, which is the enum
    every authorization check in the application actually reads
    (``deps.require_roles``, ``app/permissions/*``). The list is therefore
    derived from the enum rather than from the (empty) ``roles`` table, so it
    can never drift from the roles the API will actually accept.
    """

    name: str
    description: str
    is_assignable: bool = True
    user_count: int = 0
    active_user_count: int = 0


class RoleListResponse(BaseModel):
    total: int
    items: List[RoleSummary]


class RoleUpdate(BaseModel):
    """Assign a role to a user."""

    role: str = Field(..., min_length=1, max_length=32)
    reason: Optional[str] = Field(None, max_length=255)
