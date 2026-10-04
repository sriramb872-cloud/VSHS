# backend-python/app/routers/v1/admin_password_reset.py
"""Flow B - admin-assisted password resets.

There is no Parent role in SCHOLARIS, so when an account has no email on file
(mainly students) recovery is a staff action:

    SUPER_ADMIN  -> handles Principals and everyone else, across schools
    PRINCIPAL    -> handles Teachers and Students of their OWN school
    TEACHER      -> nothing, ever (the role is not in ``require_roles`` below)

Every action is tenant-checked server-side (never on the client's word) and
written to ``audit_logs``. The temporary password is generated here, returned
exactly once to the admin who asked for it, and stored only as a bcrypt hash -
it cannot be read back by anyone, including Super Admin.
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.audit import write_audit_log
from app.core.security import get_password_hash
from app.core.token_service import revoke_all_sessions
from app.models.password_reset import PasswordResetRequest
from app.models.user import User
from app.services.password_reset import (
    close_pending_requests,
    generate_temp_password,
)

router = APIRouter(prefix="/admin", tags=["Admin - Password Resets"])

#: A Principal may only act on these roles (within their own school).
#: SUPER_ADMIN is handled separately and may act on any role.
PRINCIPAL_MANAGEABLE_ROLES = ("TEACHER", "STUDENT")


def _role(user: User) -> str:
    return str(getattr(user, "role", "") or "").upper()


def _ensure_may_manage(actor: User, target: User) -> None:
    """Server-side role hierarchy + tenant check for acting on ``target``."""
    actor_role = _role(actor)
    if actor_role == "SUPER_ADMIN":
        return
    if (
        actor_role == "PRINCIPAL"
        and _role(target) in PRINCIPAL_MANAGEABLE_ROLES
        and target.school_id is not None
        and target.school_id == actor.school_id
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "message": "You are not allowed to reset this account",
            "code": "FORBIDDEN_ROLE",
        },
    )


def _serialize(row: PasswordResetRequest, user: User, handled_by_name: Optional[str]) -> dict:
    return {
        "id": row.id,
        "user_id": user.id,
        "user_name": user.display_name,
        "role": _role(user),
        "mobile": user.mobile,
        "email": user.email,
        "has_email": bool(str(user.email or "").strip()),
        "school_id": user.school_id,
        "status": row.status,
        "requested_at": row.requested_at,
        "handled_by": row.handled_by,
        "handled_by_name": handled_by_name,
        "handled_at": row.handled_at,
    }


@router.get("/password-reset-requests", response_model=List[dict])
def list_password_reset_requests(
    status_filter: Optional[str] = Query(
        "pending", alias="status", description="pending | completed | rejected | all"
    ),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    """Queue of accounts waiting for a staff-issued temporary password.

    Scoped by role hierarchy: a Principal sees only Teachers and Students of
    their own school; a Super Admin sees every request.
    """
    query = (
        db.query(PasswordResetRequest, User)
        .join(User, User.id == PasswordResetRequest.user_id)
    )
    if _role(current_user) != "SUPER_ADMIN":
        query = query.filter(
            User.school_id == current_user.school_id,
            User.role.in_(PRINCIPAL_MANAGEABLE_ROLES),
        )
    if status_filter and status_filter.lower() != "all":
        query = query.filter(PasswordResetRequest.status == status_filter.lower())

    rows = query.order_by(PasswordResetRequest.requested_at.desc()).limit(limit).all()

    handler_names = {}
    handler_ids = {row.handled_by for row, _ in rows if row.handled_by}
    if handler_ids:
        for handler in db.query(User).filter(User.id.in_(handler_ids)).all():
            handler_names[handler.id] = handler.display_name

    return [
        _serialize(row, user, handler_names.get(row.handled_by))
        for row, user in rows
    ]


@router.post("/password-reset-requests/{request_id}/reject", response_model=dict)
def reject_password_reset_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    """Decline a request (e.g. verified in person) without changing the password."""
    row = db.query(PasswordResetRequest).filter(PasswordResetRequest.id == request_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    target = db.query(User).filter(User.id == row.user_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _ensure_may_manage(current_user, target)
    if row.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "This request has already been handled", "code": "ALREADY_HANDLED"},
        )

    row.status = "rejected"
    row.handled_by = current_user.id
    row.handled_at = datetime.utcnow()
    db.add(row)
    db.commit()

    write_audit_log(
        db,
        user_id=current_user.id,
        school_id=target.school_id,
        action="PASSWORD_RESET_REJECTED",
        resource_type="PasswordResetRequest",
        resource_id=row.id,
        details={"target_user_id": target.id},
    )
    return {"message": "Request rejected", "id": row.id, "status": row.status}


@router.post("/users/{user_id}/reset-password", response_model=dict)
def admin_reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    """Issue a one-time temporary password for ``user_id``.

    The plaintext appears in THIS response only (never stored, never logged,
    never retrievable again): the admin reads it out / shares it in person, the
    user signs in with it and is forced to choose a new password before
    anything else loads (``must_change_password``).

    Also: every live session of that account is revoked immediately and the
    action is written to ``audit_logs``.
    """
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _ensure_may_manage(current_user, target)

    temporary_password = generate_temp_password()
    target.password_hash = get_password_hash(temporary_password)
    target.must_change_password = True
    # A staff reset is also the recovery path out of a lockout.
    target.failed_login_attempts = 0
    target.locked_until = None
    # Legacy raw-token columns from the retired flow: never leave a credential.
    target.reset_token = None
    target.reset_token_expires_at = None
    db.add(target)
    db.commit()

    close_pending_requests(db, target.id, handled_by=current_user.id)
    # The old credentials may have been compromised: kill every live session.
    revoke_all_sessions(db, target)

    write_audit_log(
        db,
        user_id=current_user.id,
        school_id=target.school_id,
        action="RESET_PASSWORD",
        resource_type="User",
        resource_id=target.id,
        details={"channel": "admin", "must_change_password": True},
    )

    return {
        "message": "Temporary password generated. Share it with the user in person - it will not be shown again.",
        "temporary_password": temporary_password,
        "must_change_password": True,
        "user": {
            "id": target.id,
            "display_name": target.display_name,
            "role": _role(target),
        },
    }
