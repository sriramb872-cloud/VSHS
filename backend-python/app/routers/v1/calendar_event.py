# app/routers/v1/calendar_event.py
from datetime import date
from typing import Optional, Union
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.calendar_event import (
    CalendarEventResponse,
    CalendarEventListResponse,
    CalendarEventCreate,
    CalendarEventUpdate,
)
from app.services.calendar_event import CalendarEventService
from app.models.user import UserModel

router = APIRouter(prefix="/calendar-events", tags=["Calendar Events"])


@router.get("", response_model=CalendarEventListResponse)
@router.get("/", response_model=CalendarEventListResponse)
def list_calendar_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    event_type: Optional[str] = None,
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    is_active: Optional[bool] = None,
    school_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    items, total = CalendarEventService.list_events(
        db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
        school_id=school_id,
    )
    return {"total": total, "items": items}


@router.get("/{event_id}", response_model=CalendarEventResponse)
def get_calendar_event(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return CalendarEventService.get_event(db, event_id=event_id, current_user=current_user)


@router.post("", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_calendar_event(
    obj_in: CalendarEventCreate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    return CalendarEventService.create_event(db, obj_in=obj_in, current_user=current_user)


@router.put("/{event_id}", response_model=CalendarEventResponse)
def update_calendar_event_put(
    event_id: int,
    obj_in: CalendarEventUpdate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    return CalendarEventService.update_event(db, event_id=event_id, obj_in=obj_in, current_user=current_user)


@router.patch("/{event_id}", response_model=CalendarEventResponse)
def update_calendar_event_patch(
    event_id: int,
    obj_in: CalendarEventUpdate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    return CalendarEventService.update_event(db, event_id=event_id, obj_in=obj_in, current_user=current_user)


@router.delete("/{event_id}", response_model=CalendarEventResponse)
def delete_calendar_event(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    return CalendarEventService.delete_event(db, event_id=event_id, current_user=current_user)