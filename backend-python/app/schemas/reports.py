"""Schemas for the platform reporting endpoints.

These back the Super Admin "System Reports" screen. Every field is derived from
a real aggregate query; nothing here is synthesised in Python or hard-coded.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class PlatformReportSummary(BaseModel):
    """Platform-wide totals for a date window."""

    generated_at: str
    window_start: str
    window_end: str
    school_count: int
    active_school_count: int
    user_count: int
    active_user_count: int
    inactive_user_count: int
    # Users attached to one of the schools in scope. Platform-level accounts
    # (a Super Admin has school_id = NULL) are counted here, so `user_count` is
    # the platform total and these two always add up to it.
    school_user_count: int
    platform_user_count: int
    users_by_role: dict = Field(default_factory=dict)
    student_count: int
    teacher_count: int
    grade_count: int
    section_count: int
    subject_count: int
    exam_count: int
    published_exam_count: int
    marks_record_count: int
    report_card_count: int
    attendance_record_count: int
    audit_event_count: int


class SchoolRollup(BaseModel):
    """One row per school in the platform rollup."""

    school_id: int
    school_name: str
    school_code: Optional[str] = None
    is_active: bool
    student_count: int = 0
    teacher_count: int = 0
    staff_count: int = 0
    section_count: int = 0
    exam_count: int = 0
    report_card_count: int = 0
    attendance_record_count: int = 0
    last_audit_at: Optional[str] = None


class PlatformReportResponse(BaseModel):
    summary: PlatformReportSummary
    schools: List[SchoolRollup] = Field(default_factory=list)
