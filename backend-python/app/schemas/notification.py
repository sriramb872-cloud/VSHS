# app/schemas/notification.py
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    PUBLIC = "PUBLIC"
    STAFF_ONLY = "STAFF_ONLY"
    CLASS_ONLY = "CLASS_ONLY"
    ONLY_FOR_CLASS = "ONLY_FOR_CLASS"
    ONLY_FOR_STUDENT = "ONLY_FOR_STUDENT"

    def __str__(self) -> str:
        return str(self.value)


class NotificationCategory(str, Enum):
    PUBLIC = "PUBLIC"
    CLASS = "CLASS"
    CLASS_TEACHER = "CLASS_TEACHER"
    STAFF = "STAFF"

    def __str__(self) -> str:
        return str(self.value)


class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    message: str = Field(..., min_length=1, description="Notification body content")
    notification_type: NotificationType = Field(..., description="Notification category or type")
    target_class_id: Optional[int] = Field(default=None, description="Target class/section ID")
    target_student_id: Optional[int] = Field(default=None, description="Target student ID")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata payload")


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class NotificationResponse(BaseModel):
    id: int
    school_id: Optional[int] = None
    sender_id: Optional[int] = None
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None
    title: str
    message: str
    notification_type: str
    target_class_id: Optional[int] = None
    target_class_name: Optional[str] = None
    target_student_id: Optional[int] = None
    target_student_name: Optional[str] = None
    category: Optional[str] = None
    user_id: Optional[int] = None
    is_read: bool = False
    reference_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    total: int
    items: List[NotificationResponse]
    unread_count: int


class StudentSummary(BaseModel):
    id: int
    student_id: int
    full_name: str
    roll_number: Optional[str] = None


class TeacherClassInfoResponse(BaseModel):
    is_class_teacher: bool
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    grade_name: Optional[str] = None
    students: List[StudentSummary] = []