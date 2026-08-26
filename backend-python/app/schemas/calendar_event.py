# app/schemas/calendar_event.py
from datetime import datetime, date
from typing import Optional, Union, List
from pydantic import BaseModel, Field, field_validator


class CalendarEventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Event Title")
    description: Optional[str] = Field(None, description="Event Description")
    event_type: str = Field(..., min_length=1, max_length=100, description="Type of calendar event")
    start_date: Union[date, str] = Field(..., description="Event start date")
    end_date: Optional[Union[date, str]] = Field(None, description="Event end date")
    is_active: Optional[bool] = Field(True, description="Active status indicator")

    @field_validator("start_date", mode="before")
    @classmethod
    def validate_start_date(cls, v):
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            if "T" in v:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
            return date.fromisoformat(v[:10])
        return v

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_date(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            if "T" in v:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
            return date.fromisoformat(v[:10])
        return v


class CalendarEventCreate(CalendarEventBase):
    school_id: Optional[int] = None


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    event_type: Optional[str] = Field(None, min_length=1, max_length=100)
    start_date: Optional[Union[date, str]] = None
    end_date: Optional[Union[date, str]] = None
    is_active: Optional[bool] = None

    @field_validator("start_date", mode="before")
    @classmethod
    def validate_start_date(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            if "T" in v:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
            return date.fromisoformat(v[:10])
        return v

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_date(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            if "T" in v:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
            return date.fromisoformat(v[:10])
        return v


class CalendarEventResponse(BaseModel):
    id: int
    school_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    event_type: str
    start_date: date
    end_date: date
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CalendarEventListResponse(BaseModel):
    total: int
    items: List[CalendarEventResponse]

