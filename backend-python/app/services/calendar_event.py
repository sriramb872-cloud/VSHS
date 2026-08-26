# app/services/calendar_event.py
from datetime import date
from typing import List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.calendar_event import calendar_event as crud_calendar_event
from app.models.calendar_event import CalendarEvent
from app.models.user import User
from app.schemas.calendar_event import CalendarEventCreate, CalendarEventUpdate


class CalendarEventService:
    @staticmethod
    def get_event(db: Session, event_id: int, current_user: User) -> CalendarEvent:
        event = crud_calendar_event.get(db, event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar event not found"
            )
        role = str(current_user.role).upper()
        if role != "SUPER_ADMIN" and event.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: event does not belong to your school"
            )
        return event

    @staticmethod
    def list_events(
        db: Session,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        is_active: Optional[bool] = None,
        school_id: Optional[int] = None,
    ) -> Tuple[List[CalendarEvent], int]:
        target_school_id = current_user.school_id
        role = str(current_user.role).upper()
        if role == "SUPER_ADMIN" and school_id is not None:
            target_school_id = school_id

        return crud_calendar_event.get_multi(
            db,
            skip=skip,
            limit=limit,
            school_id=target_school_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
        )

    @staticmethod
    def create_event(
        db: Session, obj_in: CalendarEventCreate, current_user: User
    ) -> CalendarEvent:
        role = str(current_user.role).upper()
        if role not in ["PRINCIPAL", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principals and Admins are authorized to create calendar events"
            )

        school_id = current_user.school_id
        if role == "SUPER_ADMIN" and obj_in.school_id:
            school_id = obj_in.school_id

        if not school_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School ID is required to create a calendar event"
            )

        return crud_calendar_event.create(db, obj_in=obj_in, school_id=school_id)

    @staticmethod
    def update_event(
        db: Session, event_id: int, obj_in: Union[CalendarEventUpdate, dict], current_user: User
    ) -> CalendarEvent:
        role = str(current_user.role).upper()
        if role not in ["PRINCIPAL", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principals and Admins are authorized to modify calendar events"
            )

        event = CalendarEventService.get_event(db, event_id, current_user=current_user)
        return crud_calendar_event.update(db, db_obj=event, obj_in=obj_in)

    @staticmethod
    def delete_event(
        db: Session, event_id: int, current_user: User
    ) -> CalendarEvent:
        role = str(current_user.role).upper()
        if role not in ["PRINCIPAL", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principals and Admins are authorized to delete calendar events"
            )

        event = CalendarEventService.get_event(db, event_id, current_user=current_user)
        deleted = crud_calendar_event.delete(db, id=event_id)
        return deleted if deleted else event

