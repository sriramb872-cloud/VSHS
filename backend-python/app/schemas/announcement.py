# app/schemas/announcement.py
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class AnnouncementAudience(str, Enum):
    SCHOOL_WIDE = "School-Wide"
    TEACHERS = "Teachers"
    STUDENTS = "Students"
    PARENTS = "Parents"
    GRADE = "Grade"
    SECTION = "Section"

class AnnouncementPriority(str, Enum):
    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"
    URGENT = "Urgent"

class AnnouncementStatus(str, Enum):
    DRAFT = "Draft"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"

class AnnouncementBase(BaseModel):
    title: str = Field(..., min_h=1, max_length=255, description="Announcement Title")
    description: str = Field(..., description="Announcement content description")
    audience: AnnouncementAudience = Field(..., description="Target audience")
    academic_year_id: Optional[int] = Field(None, description="Academic Year ID")
    grade_id: Optional[int] = Field(None, description="Grade ID")
    section_id: Optional[int] = Field(None, description="Section ID")
    priority: AnnouncementPriority = Field(AnnouncementPriority.NORMAL, description="Priority level")
    publish_date: datetime = Field(..., description="Publish date and time")
    expiry_date: Optional[datetime] = Field(None, description="Expiry date and time")
    status: AnnouncementStatus = Field(AnnouncementStatus.DRAFT, description="Status of announcement")

class AnnouncementCreate(AnnouncementBase):
    pass

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    audience: Optional[AnnouncementAudience] = None
    academic_year_id: Optional[int] = None
    grade_id: Optional[int] = None
    section_id: Optional[int] = None
    priority: Optional[AnnouncementPriority] = None
    publish_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: Optional[AnnouncementStatus] = None

class AnnouncementResponse(AnnouncementBase):
    id: int
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AnnouncementListResponse(BaseModel):
    total: int
    items: list[AnnouncementResponse]
    """
SCHOLARIS ERP

Module:
Description:

TODO:
"""
