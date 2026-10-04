# backend-python/app/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password
from app.models.user import User
from app.models.student import Student
from app.models.teacher import Teacher


def _is_locked(user: User) -> bool:
    return bool(user.locked_until and user.locked_until > datetime.utcnow())


def _register_failed_attempt(db: Session, user: User) -> None:
    """Count one failed login for this account; lock it at the threshold.

    Lockout is strictly per account and time-boxed (never school-wide), so
    one compromised/attacked login name cannot lock out a school. The HTTP
    rate limiter (slowapi, per-IP) remains the separate, first-line defence.
    """
    user.failed_login_attempts = int(user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(
            minutes=settings.LOGIN_LOCKOUT_MINUTES
        )
        user.failed_login_attempts = 0
    db.add(user)
    db.commit()


def _clear_failed_attempts(db: Session, user: User) -> None:
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.add(user)
        db.commit()


def find_users_by_identifier(db: Session, identifier: str) -> list[User]:
    """Resolve ONE login ID to the accounts that match it.

    A login ID is any of: mobile number, email address, student admission
    number (e.g. ``SCH2026001``) or staff employee ID (e.g. ``EMP2026001``).
    This is the single lookup shared by password login and by the password
    reset flow - they must accept exactly the same identifiers, or a user who
    can sign in would find they cannot recover their account.

    Returned in lookup order (mobile, email, student, teacher); callers decide
    which candidate to use. Nothing here filters by password or lock state.
    """
    identifier = str(identifier or "").strip()
    if not identifier:
        return []

    # 1. Check direct mobile match
    users = db.query(User).filter(User.mobile == identifier).all()

    # 2. Check email match
    if not users:
        users = db.query(User).filter(User.email == identifier).all()

    # 3. Check Student ID / admission_number match (e.g. SCH2026001)
    if not users:
        student = db.query(Student).filter(Student.admission_number == identifier).first()
        if student and student.user:
            users = [student.user]

    # 4. Check Teacher Employee ID match (e.g. EMP2026001)
    if not users:
        teacher = db.query(Teacher).filter(Teacher.employee_id == identifier).first()
        if teacher and teacher.user:
            users = [teacher.user]

    return users


def authenticate_user(db: Session, mobile: str, password: str) -> Optional[User]:
    identifier = str(mobile).strip()

    users = find_users_by_identifier(db, identifier)

    if not users:
        return None

    saw_locked_account = False

    for user in users:
        account_status = getattr(user, "is_active", "ACTIVE")
        if account_status != "ACTIVE":
            continue
        # Block login if the user's school has been deactivated
        role = str(getattr(user, "role", "")).upper()
        if role != "SUPER_ADMIN" and user.school_id:
            from app.models.school import School
            school = db.query(School).filter(School.id == user.school_id).first()
            if school is not None and school.is_active is False:
                continue  # treat deactivated school same as inactive account — skip this user

        if _is_locked(user):
            # Do not even test the password while locked, and do not reveal
            # the lock with a distinct error - the response stays a plain 401.
            saw_locked_account = True
            continue

        if verify_password(password, user.password_hash):
            _clear_failed_attempts(db, user)
            return user
        else:
            _register_failed_attempt(db, user)

    # Account exists but is locked (or nothing matched): behave exactly like
    # an unknown identifier so login responses cannot be used to enumerate.
    if saw_locked_account:
        return None
    return None
