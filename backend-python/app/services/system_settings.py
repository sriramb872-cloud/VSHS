# app/services/settings.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.settings import settings_crud
from app.core.security import verify_password, get_password_hash
from app.schemas.settings import (
    SuperAdminSettingsUpdate,
    PrincipalSettingsUpdate,
    UserProfileSettingsBase,
    UserPasswordChange
)

class SettingsService:
    @staticmethod
    def get_super_admin(db: Session, current_user):
        if getattr(current_user, "role", None) != "SUPER_ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        settings = settings_crud.get_super_admin_settings(db)
        if not settings:
            return {
                "id": 1,
                "platform_name": "Scholaris ERP",
                "platform_logo": "",
                "default_language": "en",
                "time_zone": "UTC",
                "maintenance_mode": False,
                "email_configuration": {},
                "backup_settings": {}
            }
        return settings

    @staticmethod
    def update_super_admin(db: Session, current_user, payload: SuperAdminSettingsUpdate):
        if getattr(current_user, "role", None) != "SUPER_ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        return settings_crud.update_super_admin_settings(db, payload.model_dump(exclude_none=True))

    @staticmethod
    def _active_year_name(db: Session, school_id) -> str:
        """The ACTIVE academic year's name, or "" when the school has none.

        ``school_settings.academic_year`` is a display copy only - the
        ``academic_years`` table is the source of truth.
        """
        from app.crud.academic_year import get_active_academic_year

        try:
            year = get_active_academic_year(db, school_id)
        except Exception:  # noqa: BLE001
            year = None
        return getattr(year, "name", "") or ""

    @staticmethod
    def get_principal(db: Session, current_user):
        if getattr(current_user, "role", None) not in ["SUPER_ADMIN", "PRINCIPAL"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        school_id = getattr(current_user, "school_id", 1)
        settings = settings_crud.get_principal_settings(db, school_id)
        if not settings:
            return {
                "id": 1,
                "school_name": "Default School",
                "school_logo": "",
                "school_address": "123 Education Lane",
                "phone_number": "555-0199",
                "email": "school@scholaris.com",
                "academic_year": SettingsService._active_year_name(db, school_id),
                "school_working_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "school_timings": "08:00 - 15:00",
                "grade_settings": {},
                "section_settings": {}
            }
        active_name = SettingsService._active_year_name(db, school_id)
        if active_name:
            settings = {**settings, "academic_year": active_name}
        return settings

    @staticmethod
    def update_principal(db: Session, current_user, payload: PrincipalSettingsUpdate):
        if getattr(current_user, "role", None) not in ["SUPER_ADMIN", "PRINCIPAL"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        school_id = getattr(current_user, "school_id", 1)
        data = payload.model_dump(exclude_none=True)
        # The free-text academic year is no longer writable: the ACTIVE
        # AcademicYear is authoritative and settings must never contradict it.
        data.pop("academic_year", None)
        result = settings_crud.update_principal_settings(db, school_id, data)
        active_name = SettingsService._active_year_name(db, school_id)
        if active_name and result is not None:
            result = {**result, "academic_year": active_name}
        return result

    @staticmethod
    def get_user_profile(db: Session, current_user):
        user_id = getattr(current_user, "id", 1)
        settings = settings_crud.get_user_settings(db, user_id)
        if not settings:
            return {
                "id": user_id,
                "profile_information": {"name": getattr(current_user, "display_name", None) or "User", "email": getattr(current_user, "email", "user@scholaris.com")},
                "notification_preferences": {"email": True, "sms": False, "push": True}
            }
        return settings

    @staticmethod
    def update_user_profile(db: Session, current_user, payload: UserProfileSettingsBase):
        user_id = getattr(current_user, "id", 1)
        return settings_crud.update_user_settings(db, user_id, payload.model_dump(exclude_none=True))

    @staticmethod
    def change_password(db: Session, current_user, payload: UserPasswordChange):
        if len(payload.new_password) < 8:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long")
        if not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        current_user.password_hash = get_password_hash(payload.new_password)
        db.add(current_user)
        db.commit()
        return {"message": "Password updated successfully"}
