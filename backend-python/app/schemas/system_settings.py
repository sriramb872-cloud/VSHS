# app/schemas/settings.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr

class SuperAdminSettingsBase(BaseModel):
    platform_name: str
    platform_logo: Optional[str] = None
    default_language: str = "en"
    time_zone: str = "UTC"
    maintenance_mode: bool = False
    email_configuration: Optional[dict] = {}
    backup_settings: Optional[dict] = {}

class SuperAdminSettingsUpdate(SuperAdminSettingsBase):
    pass

class SuperAdminSettingsResponse(SuperAdminSettingsBase):
    id: int

    class Config:
        from_attributes = True

class PrincipalSettingsBase(BaseModel):
    school_name: str
    school_logo: Optional[str] = None
    school_address: str
    phone_number: str
    email: EmailStr
    academic_year: str
    school_working_days: List[str] = []
    school_timings: str
    grade_settings: Optional[dict] = {}
    section_settings: Optional[dict] = {}

class PrincipalSettingsUpdate(PrincipalSettingsBase):
    pass

class PrincipalSettingsResponse(PrincipalSettingsBase):
    id: int

    class Config:
        from_attributes = True

class UserProfileSettingsBase(BaseModel):
    profile_information: Optional[dict] = {}
    notification_preferences: Optional[dict] = {}

class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str

class UserProfileSettingsResponse(UserProfileSettingsBase):
    id: int

    class Config:
        from_attributes = True
        """
SCHOLARIS ERP

Module:
Description:

TODO:
"""
