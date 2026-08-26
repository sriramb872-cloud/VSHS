"""
SCHOLARIS ERP - Student Schemas
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentBase(BaseModel):
    admission_number: Optional[str] = Field(None, max_length=50)
    roll_number: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    blood_group: Optional[str] = Field(None, max_length=10)
    father_name: Optional[str] = Field(None, max_length=100)
    father_mobile: Optional[str] = Field(None, max_length=15)
    mother_name: Optional[str] = Field(None, max_length=100)
    mother_mobile: Optional[str] = Field(None, max_length=15)
    guardian_mobile: Optional[str] = Field(None, max_length=15)
    address: Optional[str] = Field(None, max_length=500)


class StudentCreate(StudentBase):
    user_id: Optional[int] = None
    school_id: int
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[EmailStr] = None
    grade_id: Optional[int] = None
    section_id: Optional[int] = None


class StudentUpdate(BaseModel):
    admission_number: Optional[str] = None
    roll_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    father_name: Optional[str] = None
    father_mobile: Optional[str] = None
    mother_name: Optional[str] = None
    mother_mobile: Optional[str] = None
    guardian_mobile: Optional[str] = None
    address: Optional[str] = None
    grade_id: Optional[int] = None
    section_id: Optional[int] = None


class StudentResponse(StudentBase):
    id: int
    user_id: Optional[int] = None
    school_id: int
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    profile_photo: Optional[str] = None
    admission_date: Optional[date] = None
    student_id_formatted: Optional[str] = None
    age: Optional[int] = None
    grade_id: Optional[int] = None
    grade_name: Optional[str] = None
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    academic_year_id: Optional[int] = None
    academic_year_name: Optional[str] = None
    enrollment_date: Optional[date] = None
    attendance_percentage: Optional[float] = None
    status: Optional[str] = "ACTIVE"
    student_status: Optional[str] = "ACTIVE"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
