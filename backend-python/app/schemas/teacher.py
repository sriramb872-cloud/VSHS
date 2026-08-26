from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class TeacherBase(BaseModel):
    employee_id: Optional[str] = Field(None, description="School-specific employee identifier or badge number")
    qualification: Optional[str] = Field(None, description="Educational qualifications")
    department: Optional[str] = Field(None, description="Department")
    specialization: Optional[str] = Field(None, description="Subject specialization")
    joining_date: Optional[date] = Field(None, description="Date of joining the school")
    address: Optional[str] = Field(None, description="Residential or contact address")


class TeacherCreate(TeacherBase):
    user_id: int = Field(..., description="Associated user ID in the users table")
    school_id: int = Field(..., description="Associated school ID")


class TeacherUpdate(BaseModel):
    employee_id: Optional[str] = None
    qualification: Optional[str] = None
    department: Optional[str] = None
    specialization: Optional[str] = None
    joining_date: Optional[date] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class TeacherResponse(TeacherBase):
    id: int
    user_id: int
    school_id: int
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    profile_photo: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    role_type: Optional[str] = "Subject Teacher"
    status: Optional[str] = "ACTIVE"
    is_active: Optional[bool] = True
    assigned_subjects: Optional[List[str]] = None
    assigned_sections: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
