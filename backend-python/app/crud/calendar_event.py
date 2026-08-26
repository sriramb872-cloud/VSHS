# app/crud/calendar_event.py
from datetime import date
from typing import List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from app.models.calendar_event import CalendarEvent
from app.schemas.calendar_event import CalendarEventCreate, CalendarEventUpdate


class CRUDCalendarEvent:
    def get(self, db: Session, event_id: int) -> Optional[CalendarEvent]:
        return db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        school_id: Optional[int] = None,
        event_type: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[CalendarEvent], int]:
        query = db.query(CalendarEvent)

        if school_id is not None:
            query = query.filter(CalendarEvent.school_id == school_id)
        if event_type is not None and event_type != "" and event_type != "All":
            query = query.filter(CalendarEvent.event_type.ilike(f"%{event_type}%"))
        if is_active is not None:
            query = query.filter(CalendarEvent.is_active == is_active)
        if start_date is not None:
            query = query.filter(CalendarEvent.end_date >= start_date)
        if end_date is not None:
            query = query.filter(CalendarEvent.start_date <= end_date)

        total = query.count()
        items = query.order_by(CalendarEvent.start_date.asc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, db: Session, *, obj_in: CalendarEventCreate, school_id: int) -> CalendarEvent:
        end_dt = obj_in.end_date if obj_in.end_date is not None else obj_in.start_date
        db_obj = CalendarEvent(
            school_id=school_id,
            title=obj_in.title,
            description=obj_in.description,
            event_type=obj_in.event_type,
            start_date=obj_in.start_date,
            end_date=end_dt,
            is_active=obj_in.is_active if obj_in.is_active is not None else True,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: CalendarEvent, obj_in: Union[CalendarEventUpdate, dict]
    ) -> CalendarEvent:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else obj_in.dict(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)

        if "start_date" in update_data and "end_date" not in update_data:
            if db_obj.end_date < db_obj.start_date:
                db_obj.end_date = db_obj.start_date

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> Optional[CalendarEvent]:
        obj = db.query(CalendarEvent).filter(CalendarEvent.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


calendar_event = CRUDCalendarEvent()

