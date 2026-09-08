# app/crud/settings.py
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.models.app_settings import SystemSettings, SchoolSettings, UserAppSettings
from app.models.school import School


class SettingsCRUD:
    def get_super_admin_settings(self, db: Session) -> Optional[Dict[str, Any]]:
        row = db.query(SystemSettings).first()
        if not row:
            return None
        return {
            "id": row.id,
            "platform_name": row.platform_name,
            "platform_logo": row.platform_logo or "",
            "default_language": row.default_language or "en",
            "time_zone": row.time_zone or "UTC",
            "maintenance_mode": row.maintenance_mode or False,
            "email_configuration": row.email_configuration or {},
            "backup_settings": row.backup_settings or {},
        }

    def update_super_admin_settings(self, db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
        row = db.query(SystemSettings).first()
        if not row:
            row = SystemSettings(id=1)
            db.add(row)

        for key in [
            "platform_name",
            "platform_logo",
            "default_language",
            "time_zone",
            "maintenance_mode",
            "email_configuration",
            "backup_settings",
        ]:
            if key in data and data[key] is not None:
                setattr(row, key, data[key])

        db.commit()
        db.refresh(row)
        return {
            "id": row.id,
            "platform_name": row.platform_name,
            "platform_logo": row.platform_logo or "",
            "default_language": row.default_language or "en",
            "time_zone": row.time_zone or "UTC",
            "maintenance_mode": row.maintenance_mode or False,
            "email_configuration": row.email_configuration or {},
            "backup_settings": row.backup_settings or {},
        }

    def get_principal_settings(self, db: Session, school_id: int) -> Optional[Dict[str, Any]]:
        row = db.query(SchoolSettings).filter(SchoolSettings.school_id == school_id).first()
        if not row:
            return None

        school = db.query(School).filter(School.id == school_id).first()
        school_name = (school.name if school else None) or row.school_name or "Default School"

        return {
            "id": row.id,
            "school_name": school_name,
            "school_logo": row.school_logo or "",
            "school_address": row.school_address or "",
            "phone_number": row.phone_number or "",
            "email": row.email or "",
            "academic_year": row.academic_year or "",
            "school_working_days": row.school_working_days or [],
            "school_timings": row.school_timings or "",
            "grade_settings": row.grade_settings or {},
            "section_settings": row.section_settings or {},
        }

    def update_principal_settings(self, db: Session, school_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        row = db.query(SchoolSettings).filter(SchoolSettings.school_id == school_id).first()
        if not row:
            row = SchoolSettings(school_id=school_id)
            db.add(row)

        for key in [
            "school_name",
            "school_logo",
            "school_address",
            "phone_number",
            "email",
            "academic_year",
            "school_working_days",
            "school_timings",
            "grade_settings",
            "section_settings",
        ]:
            if key in data and data[key] is not None:
                setattr(row, key, data[key])

        db.commit()
        db.refresh(row)

        school = db.query(School).filter(School.id == school_id).first()
        school_name = (school.name if school else None) or row.school_name or "Default School"

        return {
            "id": row.id,
            "school_name": school_name,
            "school_logo": row.school_logo or "",
            "school_address": row.school_address or "",
            "phone_number": row.phone_number or "",
            "email": row.email or "",
            "academic_year": row.academic_year or "",
            "school_working_days": row.school_working_days or [],
            "school_timings": row.school_timings or "",
            "grade_settings": row.grade_settings or {},
            "section_settings": row.section_settings or {},
        }

    def get_user_settings(self, db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        row = db.query(UserAppSettings).filter(UserAppSettings.user_id == user_id).first()
        if not row:
            return None
        return {
            "id": row.id,
            "profile_information": row.profile_information or {},
            "notification_preferences": row.notification_preferences or {},
        }

    def update_user_settings(self, db: Session, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        row = db.query(UserAppSettings).filter(UserAppSettings.user_id == user_id).first()
        if not row:
            row = UserAppSettings(user_id=user_id)
            db.add(row)

        for key in ["profile_information", "notification_preferences"]:
            if key in data and data[key] is not None:
                setattr(row, key, data[key])

        db.commit()
        db.refresh(row)

        return {
            "id": row.id,
            "profile_information": row.profile_information or {},
            "notification_preferences": row.notification_preferences or {},
        }


settings_crud = SettingsCRUD()
