# backend-python/app/routers/v1/roles.py
"""Role catalogue for the Super Admin "System Roles" screen.

The platform has no permission table: authorization is entirely role-based on
``app.models.role.UserRole``. This module exposes that enum (the real source of
truth used by ``deps.require_roles`` and ``app/permissions/*``) with live user
counts, and owns the role-assignment endpoint.

Role changes are deliberately routed through ``/users/{id}/role`` rather than
the generic ``PATCH /users/{id}`` so that the extra invariants - no self
demotion, never remove the last active Super Admin, never strand a user without
a school - cannot be bypassed.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.audit import write_audit_log
from app.models.role import UserRole
from app.models.school import School
from app.models.user import User
from app.schemas.role import RoleListResponse, RoleSummary, RoleUpdate
from app.routers.v1.users import serialize_user

router = APIRouter(prefix="/roles", tags=["Roles"])


# Human-readable descriptions of the fixed role set. Kept here (not in the
# database) because the role set is an enum: adding a role means changing code.
ROLE_DESCRIPTIONS: dict = {
    "SUPER_ADMIN": "Full platform management access across every school.",
    "PRINCIPAL": "School leadership and operational management for one school.",
    "TEACHER": "Classroom, attendance, homework and marks management.",
    "STUDENT": "Learner portal access to own records only.",
}


def _valid_roles() -> List[str]:
    return [r.value for r in UserRole]


@router.get("", response_model=RoleListResponse)
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"])),
):
    """The assignable role catalogue with live user counts."""
    valid = _valid_roles()
    counts = {
        (row[0], row[1]): row[2]
        for row in db.query(User.role, User.is_active, func.count(User.id))
        .filter(User.role.in_(valid))
        .group_by(User.role, User.is_active)
        .all()
    }

    items: List[RoleSummary] = []
    for name in valid:
        total = sum(n for (role, _active), n in counts.items() if role == name)
        active = sum(
            n
            for (role, is_active), n in counts.items()
            if role == name and str(is_active).upper() == "ACTIVE"
        )
        items.append(
            RoleSummary(
                name=name,
                description=ROLE_DESCRIPTIONS.get(name, ""),
                is_assignable=True,
                user_count=total,
                active_user_count=active,
            )
        )

    return RoleListResponse(total=len(items), items=items)


@router.get("/assignable", response_model=List[str])
def list_assignable_roles(
    current_user: User = Depends(require_roles(["SUPER_ADMIN"])),
):
    """Plain list of role names, for populating a role picker."""
    return _valid_roles()


@router.patch("/users/{user_id}", response_model=dict)
def assign_user_role(
    user_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"])),
):
    """Change a user's role.

    Guards:
      * the role must be a member of ``UserRole`` (422 otherwise);
      * a Super Admin cannot change their own role, so the last remaining
        Super Admin can never lock the platform out;
      * the platform must keep at least one active Super Admin;
      * a role change must not leave a user without a school, because every
        non-SUPER_ADMIN code path scopes data by ``school_id``.
    """
    target_role = str(payload.role).strip().upper()
    valid = _valid_roles()
    if target_role not in valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role {payload.role!r}. Valid roles: {', '.join(valid)}",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role.",
        )

    old_role = str(getattr(user.role, "value", user.role)).upper()
    if old_role == target_role:
        return {"user": serialize_user(user), "message": "Role unchanged."}

    # Never remove the last usable Super Admin.
    if old_role == "SUPER_ADMIN":
        remaining = (
            db.query(func.count(User.id))
            .filter(
                User.role == "SUPER_ADMIN",
                User.id != user.id,
                User.is_active == "ACTIVE",
            )
            .scalar()
            or 0
        )
        if remaining == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the only active Super Admin. Promote another account first.",
            )

    # A non-SUPER_ADMIN must belong to a school; otherwise every scoped query
    # would silently return nothing for them.
    if target_role != "SUPER_ADMIN":
        if not user.school_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This user is not attached to a school. Attach them to a school before "
                f"assigning the {target_role} role.",
            )
        if not db.query(School).filter(School.id == user.school_id).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This user's school no longer exists.",
            )

    user.role = UserRole(target_role)
    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        user_id=current_user.id,
        school_id=current_user.school_id,
        action="UPDATE_ROLE",
        resource_type="User",
        resource_id=user.id,
        details={
            "old_role": old_role,
            "new_role": target_role,
            "reason": payload.reason,
        },
    )

    return {
        "user": serialize_user(user),
        "message": f"Role changed from {old_role} to {target_role}.",
    }


@router.get("/users", response_model=List[dict])
def list_role_assignments(
    role: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN"])),
):
    """Users grouped for role assignment, with their current role."""
    from app.routers.v1.users import list_users

    normalized = str(role).strip().upper() if role else None
    if normalized and normalized not in _valid_roles():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role {role!r}. Valid roles: {', '.join(_valid_roles())}",
        )
    return list_users(
        skip=skip,
        limit=limit,
        role=normalized,
        search=None,
        is_active=None,
        school_id=None,
        db=db,
        current_user=current_user,
    )
