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

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verifies that the authenticated current user account is active.

    Raises HTTP 403 Forbidden if the account is inactive.
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