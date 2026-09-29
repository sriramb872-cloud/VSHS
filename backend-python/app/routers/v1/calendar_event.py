# app/routers/v1/calendar_event.py
from datetime import date
from typing import Optional, Union
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from app.api import deps
from app.api.year_context import resolve_year_id
from app.schemas.calendar_event import (
    CalendarEventResponse,
    CalendarEventListResponse,
    CalendarEventCreate,
    CalendarEventUpdate,
)
from app.services.calendar_event import CalendarEventService
from app.models.user import UserModel
from app.core.audit import write_audit_log

router = APIRouter(prefix="/calendar-events", tags=["Calendar Events"])


def _as_date(value: Union[date, str]) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


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
    academic_year_id: Optional[int] = None,
    request: Request = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    # CalendarEvent has no academic_year_id column (and adding one would be
    # invented denormalisation): it is filtered by date-range overlap with
    # the selected year instead.
    if academic_year_id is None:
        academic_year_id = resolve_year_id(db, current_user, request, allow_all=False)

    if academic_year_id is not None:
        from app.models.academic_year import AcademicYear

        year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
        if year is not None and year.start_date and year.end_date:
            if start_date is None:
                start_date = year.start_date
            else:
                start_date = max(_as_date(start_date), year.start_date)
            if end_date is None:
                end_date = year.end_date
            else:
                end_date = min(_as_date(end_date), year.end_date)

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
    event = CalendarEventService.create_event(db, obj_in=obj_in, current_user=current_user)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="CREATE", resource_type="CalendarEvent", resource_id=event.id,
        details={},
    )
    return event


@router.put("/{event_id}", response_model=CalendarEventResponse)
def update_calendar_event_put(
    event_id: int,
    obj_in: CalendarEventUpdate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    event = CalendarEventService.update_event(db, event_id=event_id, obj_in=obj_in, current_user=current_user)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="UPDATE", resource_type="CalendarEvent", resource_id=event_id,
        details={},
    )
    return event


@router.patch("/{event_id}", response_model=CalendarEventResponse)
def update_calendar_event_patch(
    event_id: int,
    obj_in: CalendarEventUpdate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    event = CalendarEventService.update_event(db, event_id=event_id, obj_in=obj_in, current_user=current_user)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="UPDATE", resource_type="CalendarEvent", resource_id=event_id,
        details={},
    )
    return event


@router.delete("/{event_id}", response_model=CalendarEventResponse)
def delete_calendar_event(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    event = CalendarEventService.delete_event(db, event_id=event_id, current_user=current_user)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="DELETE", resource_type="CalendarEvent", resource_id=event_id,
        details={},
    )
    return event