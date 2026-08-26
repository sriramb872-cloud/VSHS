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
                "academic_year": "2026-2027",
                "school_working_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "school_timings": "08:00 - 15:00",
                "grade_settings": {},
                "section_settings": {}
            }
        return settings

    @staticmethod
    def update_principal(db: Session, current_user, payload: PrincipalSettingsUpdate):
        if getattr(current_user, "role", None) not in ["SUPER_ADMIN", "PRINCIPAL"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        school_id = getattr(current_user, "school_id", 1)
        return settings_crud.update_principal_settings(db, school_id, payload.model_dump(exclude_none=True))

    @staticmethod
    def get_user_profile(db: Session, current_user):
        user_id = getattr(current_user, "id", 1)
        settings = settings_crud.get_user_settings(db, user_id)
        if not settings:
            return {
                "id": user_id,
                "profile_information": {"name": getattr(current_user, "name", "User"), "email": getattr(current_user, "email", "user@scholaris.com")},
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
