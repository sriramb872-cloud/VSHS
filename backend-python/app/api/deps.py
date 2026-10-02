from typing import Generator, Optional, Callable, List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import verify_access_token
from app.models.user import User


# HTTP Bearer authentication
# Swagger will now ask for a Bearer token instead of
# the OAuth2 username/password/client credentials form.
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Creates a new SQLAlchemy session,
    yields it for the request,
    and closes it afterward.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """
    Decodes the JWT Bearer token, extracts the user identity/identifier,
    queries the database, and returns the authenticated User object.

    Also enforces the server-side token version (``tv`` claim): a password
    change, password reset, logout-all or admin session revoke increments
    ``users.token_version`` and thereby instantly invalidates every access
    token previously issued to that user.

    Raises HTTP 401 if authentication fails or user does not exist.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # No Authorization header/token
    if not credentials:
        raise credentials_exception

    # Extract JWT from:
    # Authorization: Bearer <token>
    token = credentials.credentials

    # Verify and decode JWT
    token_data = verify_access_token(token)

    if token_data is None or not token_data.get("sub"):
        raise credentials_exception

    # Tokens issued before the token-version feature (or crafted without it)
    # are rejected: every legitimate token carries an integer ``tv`` claim.
    token_version = token_data.get("tv")
    if not isinstance(token_version, int):
        raise credentials_exception

    user_identifier = token_data.get("sub")

    # Support lookup by:
    # - User ID
    # - Email
    # - Mobile
    user = None

    if isinstance(user_identifier, int) or (
        isinstance(user_identifier, str)
        and user_identifier.isdigit()
    ):
        user = (
            db.query(User)
            .filter(User.id == int(user_identifier))
            .first()
        )
    else:
        user = (
            db.query(User)
            .filter(
                (User.email == user_identifier)
                | (User.mobile == user_identifier)
            )
            .first()
        )

    if user is None:
        raise credentials_exception

    # Session was invalidated after this token was issued.
    if token_version != int(user.token_version or 0):
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Verifies that the authenticated current user account is active,
    and (for non-Super-Admins) that their school is also active.

    Raises HTTP 403 Forbidden if the account or school is inactive.
    """

    account_status = getattr(
        current_user,
        "is_active",
        None,
    )

    if account_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    role = str(getattr(current_user, "role", "")).upper()
    if role != "SUPER_ADMIN" and current_user.school_id:
        from app.models.school import School
        school = db.query(School).filter(School.id == current_user.school_id).first()
        if school is not None and school.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your school account has been deactivated",
            )

    # Tenant context must fail CLOSED. Every school-scoped endpoint derives its
    # query filter from ``current_user.school_id``; for a non-super-admin this
    # is never ``None`` (all account-creation paths set it), so a ``None`` here
    # means a misconfigured account. Without this guard such an account would
    # silently receive UNFILTERED, cross-school data on every list endpoint.
    # SUPER_ADMIN is the only intentionally cross-school role and is exempt.
    if role != "SUPER_ADMIN" and current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="School context missing for this account",
        )

    return current_user


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Factory dependency to restrict route access to specific user roles.

    Normalizes roles to uppercase for robust matching.

    Raises HTTP 403 if the active user does not possess
    an allowed role.
    """

    def role_dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:

        normalized_allowed_roles = [
            role.upper()
            for role in allowed_roles
        ]

        user_role = str(
            current_user.role
        ).upper()

        # SUPER_ADMIN bypasses standard role restrictions
        # or can be explicitly included in allowed_roles.
        if (
            user_role == "SUPER_ADMIN"
            or user_role in normalized_allowed_roles
        ):
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for this user role",
        )

    return role_dependency


# ---------------------------------------------------------------------------
# Tenant (school) isolation helpers
# ---------------------------------------------------------------------------
#
# These are the canonical building blocks for server-side school scoping.
# Every endpoint that loads an object referenced by a client-supplied ID must
# verify the object belongs to the caller's school (SUPER_ADMIN is exempt by
# design - it is the only intentionally cross-school role).


def is_super_admin(current_user: User) -> bool:
    """True when the authenticated user is allowed cross-school access."""
    return str(getattr(current_user, "role", "")).upper() == "SUPER_ADMIN"


def scoped_school_id(current_user: User) -> Optional[int]:
    """School filter for list/detail queries: ``None`` (unfiltered) only for
    SUPER_ADMIN; the caller's own school for everybody else."""
    if is_super_admin(current_user):
        return None
    return current_user.school_id


def ensure_same_school(
    current_user: User,
    obj_school_id: Optional[int],
    *,
    detail: str = "Access denied",
    status_code: int = status.HTTP_403_FORBIDDEN,
) -> None:
    """Raise unless ``obj_school_id`` belongs to the caller's school.

    SUPER_ADMIN passes always. A caller without a school (misconfigured
    non-super-admin account) never passes - missing tenant context must fail
    closed, not open.
    """
    if is_super_admin(current_user):
        return
    if (
        obj_school_id is None
        or current_user.school_id is None
        or obj_school_id != current_user.school_id
    ):
        raise HTTPException(status_code=status_code, detail=detail)


def ensure_referenced_in_school(
    current_user: User,
    obj_school_id: Optional[int],
    *,
    reference_name: str = "reference",
    detail: Optional[str] = None,
) -> None:
    """Validate a *client-supplied foreign reference* (student_id, section_id,
    exam_id, ...) against the caller's school.

    A missing object (``obj_school_id is None``) and a foreign object are both
    rejected with 400, so invalid/mismatched IDs can never be persisted as
    cross-school references.
    """
    if is_super_admin(current_user):
        if obj_school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail or f"Invalid {reference_name}",
            )
        return
    if (
        obj_school_id is None
        or current_user.school_id is None
        or obj_school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail or f"{reference_name.capitalize()} must belong to your school",
        )


def get_current_school(
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves the school context associated with the current user.

    SUPER_ADMIN may return None or global context
    since they are multi-school.
    """

    if str(current_user.role).upper() == "SUPER_ADMIN":
        return None

    if not current_user.school_id or not current_user.school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School context not found for user",
        )

    return current_user.school


def get_current_active_teacher(
    current_user: User = Depends(
        require_roles(
            [
                "TEACHER",
                "SUPER_ADMIN",
                "PRINCIPAL",
            ]
        )
    ),
) -> User:
    return current_user


def get_current_active_principal(
    current_user: User = Depends(
        require_roles(
            [
                "PRINCIPAL",
                "SUPER_ADMIN",
            ]
        )
    ),
) -> User:
    return current_user


def get_current_active_admin(
    current_user: User = Depends(
        require_roles(
            [
                "SUPER_ADMIN",
                "PRINCIPAL",
            ]
        )
    ),
) -> User:
    return current_user


# ---------------------------------------------------------------------------
# Subscription access enforcement
# ---------------------------------------------------------------------------
#
# Applied as a ROUTER-level dependency to the paid ERP modules
# (attendance, homework, exams, marks, timetable, report cards, calendar).
# Authentication validity and subscription validity are deliberately
# separate: a JWT minted before the subscription expired must NOT keep
# unlocking the API, so this check runs against the DATABASE on every
# request (never against token claims or a cached flag).
#
# Default posture: a school with no subscription settings row does NOT
# require subscriptions (nothing locks out on rollout); once Super Admin
# enables them, precedence rules in SubscriptionService decide.


def require_subscription_access(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """403 ``SUBSCRIPTION_REQUIRED`` unless the caller is entitled right now.

    The error detail is structured (``{"code": ...}``) so the frontend can
    distinguish "subscription required" from ordinary authorization
    failures and show the subscription lock screen instead of a generic
    error.
    """
    from app.services.subscription import SubscriptionService

    SubscriptionService.require_access(db, current_user)
    return current_user


def require_subscription_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Super Admin only. Subscription management is never exposed to
    PRINCIPAL/TEACHER/STUDENT - they get a structured 403."""
    from app.services.subscription import SubscriptionError

    if str(getattr(current_user, "role", "")).upper() != "SUPER_ADMIN":
        raise SubscriptionError(
            "UNAUTHORIZED_SUBSCRIPTION_ACTION",
            "Only Super Admin can manage subscriptions",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return current_user
