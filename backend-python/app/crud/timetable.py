# app/crud/timetable.py
from datetime import time, datetime
from typing import List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from app.models.timetable import Timetable


def parse_time(time_val: Union[str, time]) -> time:
    if isinstance(time_val, time):
        return time_val
    if not time_val:
        return time(9, 0)
    time_str = str(time_val).strip()
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            pass
    try:
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1][:2]))
    except Exception:
        return time(9, 0)


class CRUDTimetable:
    def get(self, db: Session, timetable_id: int) -> Optional[Timetable]:
        return db.query(Timetable).filter(Timetable.id == timetable_id).first()

    def get_by_section(
        self, db: Session, *, academic_year_id: int, grade_id: int, section_id: int
    ) -> Optional[Timetable]:
        return db.query(Timetable).filter(
            Timetable.academic_year_id == academic_year_id,
            Timetable.grade_id == grade_id,
            Timetable.section_id == section_id
        ).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        school_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        teacher_id: Optional[int] = None
    ) -> Tuple[List[Timetable], int]:
        query = db.query(Timetable)

        if school_id is not None:
            query = query.filter(Timetable.school_id == school_id)
        if academic_year_id is not None:
            query = query.filter(Timetable.academic_year_id == academic_year_id)
        if grade_id is not None:
            query = query.filter(Timetable.grade_id == grade_id)
        if section_id is not None:
            query = query.filter(Timetable.section_id == section_id)
        if teacher_id is not None:
            query = query.filter(Timetable.teacher_id == teacher_id)

        total = query.count()
        items = query.order_by(Timetable.start_time.asc(), Timetable.id.asc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, db: Session, *, school_id: int, obj_in: dict) -> Timetable:
        start_time = parse_time(obj_in.get("start_time", "09:00"))
        end_time = parse_time(obj_in.get("end_time", "10:00"))

        db_obj = Timetable(
            school_id=school_id,
            academic_year_id=obj_in.get("academic_year_id", 1),
            grade_id=obj_in.get("grade_id"),
            section_id=obj_in.get("section_id", 1),
            subject_id=obj_in.get("subject_id"),
            teacher_id=obj_in.get("teacher_id"),
            day_of_week=obj_in.get("day_of_week", "Monday"),
            start_time=start_time,
            end_time=end_time,
            room_number=obj_in.get("room_number") or obj_in.get("classroom"),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Timetable, obj_in: dict) -> Timetable:
        if "academic_year_id" in obj_in and obj_in["academic_year_id"] is not None:
            db_obj.academic_year_id = obj_in["academic_year_id"]
        if "grade_id" in obj_in and obj_in["grade_id"] is not None:
            db_obj.grade_id = obj_in["grade_id"]
        if "section_id" in obj_in and obj_in["section_id"] is not None:
            db_obj.section_id = obj_in["section_id"]
        if "subject_id" in obj_in and obj_in["subject_id"] is not None:
            db_obj.subject_id = obj_in["subject_id"]
        if "teacher_id" in obj_in and obj_in["teacher_id"] is not None:
            db_obj.teacher_id = obj_in["teacher_id"]
        if "day_of_week" in obj_in and obj_in["day_of_week"] is not None:
            db_obj.day_of_week = obj_in["day_of_week"]
        if "start_time" in obj_in and obj_in["start_time"] is not None:
            db_obj.start_time = parse_time(obj_in["start_time"])
        if "end_time" in obj_in and obj_in["end_time"] is not None:
            db_obj.end_time = parse_time(obj_in["end_time"])
        if "room_number" in obj_in and obj_in["room_number"] is not None:
            db_obj.room_number = obj_in["room_number"]
        elif "classroom" in obj_in and obj_in["classroom"] is not None:
            db_obj.room_number = obj_in["classroom"]

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> Optional[Timetable]:
        obj = db.query(Timetable).filter(Timetable.id == id).first()
        if not obj:
            return None
        db.delete(obj)
        db.commit()
        return obj


timetable = CRUDTimetable()

