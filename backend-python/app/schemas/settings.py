# app/schemas/settings.py
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SuperAdminSettingsResponse(BaseModel):
    id: int
    platform_name: str = "Scholaris ERP"
    platform_logo: str = ""
    default_language: str = "en"
    time_zone: str = "UTC"
    maintenance_mode: bool = False
    email_configuration: Dict[str, Any] = {}
    backup_settings: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class SuperAdminSettingsUpdate(BaseModel):
    platform_name: Optional[str] = None
    platform_logo: Optional[str] = None
    default_language: Optional[str] = None
    time_zone: Optional[str] = None
    maintenance_mode: Optional[bool] = None
    email_configuration: Optional[Dict[str, Any]] = None
    backup_settings: Optional[Dict[str, Any]] = None


class PrincipalSettingsResponse(BaseModel):
    id: int
    school_name: str = "Default School"
    school_logo: str = ""
    school_address: str = ""
    phone_number: str = ""
    email: str = ""
    academic_year: str = ""
    school_working_days: List[str] = []
    school_timings: str = ""
    grade_settings: Dict[str, Any] = {}
    section_settings: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class PrincipalSettingsUpdate(BaseModel):
    school_name: Optional[str] = None
    school_logo: Optional[str] = None
    school_address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    academic_year: Optional[str] = None
    school_working_days: Optional[List[str]] = None
    school_timings: Optional[str] = None
    grade_settings: Optional[Dict[str, Any]] = None
    section_settings: Optional[Dict[str, Any]] = None


class UserProfileSettingsResponse(BaseModel):
    id: int
    profile_information: Dict[str, Any] = {}
    notification_preferences: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class UserProfileSettingsBase(BaseModel):
    profile_information: Optional[Dict[str, Any]] = None
    notification_preferences: Optional[Dict[str, Any]] = None


class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str
