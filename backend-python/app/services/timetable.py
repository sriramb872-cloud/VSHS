# app/services/timetable.py
from datetime import time, datetime
from typing import List, Optional, Tuple, Dict, Any, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.timetable import timetable as crud_timetable, parse_time
from app.models.timetable import Timetable
from app.models.academic_year import AcademicYear
from app.models.section import Section
from app.models.grade import Grade
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.schemas.timetable import TimetableCreate, TimetableUpdate, TimetableCopy


def serialize_timetable(t: Union[Timetable, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(t, dict):
        return t

    subject_name = ""
    if getattr(t, "subject", None):
        subject_name = getattr(t.subject, "name", None) or getattr(t.subject, "subject_name", "")
    if not subject_name and t.subject_id:
        subject_name = f"Subject #{t.subject_id}"

    teacher_name = ""
    if getattr(t, "teacher", None):
        if getattr(t.teacher, "user", None):
            teacher_name = getattr(t.teacher.user, "display_name", None) or getattr(t.teacher.user, "full_name", "")
        if not teacher_name:
            teacher_name = getattr(t.teacher, "full_name", None) or getattr(t.teacher, "name", "")
    if not teacher_name and t.teacher_id:
        teacher_name = f"Teacher #{t.teacher_id}"

    grade_name = ""
    if getattr(t, "grade", None):
        grade_name = getattr(t.grade, "name", None) or getattr(t.grade, "grade_name", "")
    if not grade_name and t.grade_id:
        grade_name = f"Grade {t.grade_id}"

    section_name = ""
    if getattr(t, "section", None):
        section_name = getattr(t.section, "name", None) or getattr(t.section, "section_name", "")

    start_str = t.start_time.strftime("%I:%M %p").lstrip("0") if hasattr(t.start_time, "strftime") else str(t.start_time or "")
    end_str = t.end_time.strftime("%I:%M %p").lstrip("0") if hasattr(t.end_time, "strftime") else str(t.end_time or "")

    return {
        "id": t.id,
        "school_id": t.school_id,
        "academic_year_id": t.academic_year_id,
        "grade_id": t.grade_id,
        "grade_name": grade_name,
        "section_id": t.section_id,
        "section_name": section_name,
        "subject_id": t.subject_id,
        "subject_name": subject_name,
        "teacher_id": t.teacher_id,
        "teacher_name": teacher_name,
        "day_of_week": t.day_of_week or "Monday",
        "start_time": start_str,
        "end_time": end_str,
        "room_number": getattr(t, "room_number", None),
        "period_number": getattr(t, "period_number", None),
    }


class TimetableService:
    @staticmethod
    def get_timetable(db: Session, timetable_id: int, school_id: Optional[int] = None) -> Dict[str, Any]:
        timetable = crud_timetable.get(db, timetable_id)
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable entry not found"
            )
        if school_id is not None and timetable.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: timetable does not belong to your school"
            )
        return serialize_timetable(timetable)

    @staticmethod
    def list_timetables(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        academic_year_id: Optional[int] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        school_id: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        items, total = crud_timetable.get_multi(
            db,
            skip=skip,
            limit=limit,
            school_id=school_id,
            academic_year_id=academic_year_id,
            grade_id=grade_id,
            section_id=section_id,
            teacher_id=teacher_id,
        )
        # Do not expose legacy/cross-school foreign-key records through any portal.
        valid_items = [item for item in items if school_id is None or not getattr(item, "subject", None) or item.subject.school_id == school_id]
        return [serialize_timetable(item) for item in valid_items], len(valid_items)

    @staticmethod
    def create_timetable(db: Session, obj_in: Union[TimetableCreate, dict], school_id: int) -> Dict[str, Any]:
        data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else (obj_in.dict() if hasattr(obj_in, "dict") else dict(obj_in))

        # Validate required fields
        if not data.get("grade_id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade/Class is required")
        if not data.get("section_id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section is required")
        if not data.get("subject_id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject is required")
        if not data.get("teacher_id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Teacher is required")
        if not data.get("start_time"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start time is required")
        if not data.get("end_time"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End time is required")

        start_t = parse_time(data["start_time"])
        end_t = parse_time(data["end_time"])
        if end_t <= start_t:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be later than start time"
            )

        grade = db.query(Grade).filter(Grade.id == data["grade_id"], Grade.school_id == school_id).first()
        if not grade:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade does not belong to this school")
        section = db.query(Section).filter(Section.id == data["section_id"]).first()
        if not section or section.school_id != school_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section does not belong to this school")
        if section.grade_id != grade.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section does not belong to the selected class")
        subject = db.query(Subject).filter(Subject.id == data["subject_id"], Subject.school_id == school_id).first()
        if not subject:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject does not belong to this school")
        teacher = db.query(Teacher).filter(Teacher.id == data["teacher_id"], Teacher.school_id == school_id).first()
        if not teacher:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Teacher does not belong to this school")

        # Prevent double-booking: same teacher, same day, overlapping time window,
        # regardless of section — a teacher physically cannot teach two classes at once.
        day = data.get("day_of_week")
        conflict = db.query(Timetable).filter(
            Timetable.teacher_id == data["teacher_id"],
            Timetable.day_of_week == day,
            Timetable.start_time < end_t,
            Timetable.end_time > start_t,
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"This teacher is already scheduled on {day} from "
                    f"{conflict.start_time} to {conflict.end_time} (section {conflict.section_id})."
                ),
            )

        # Resolve academic_year_id if missing, but never invent a foreign key.
        if not data.get("academic_year_id"):
            ay = db.query(AcademicYear).filter(
                AcademicYear.school_id == school_id,
                AcademicYear.is_active == True
            ).first() or db.query(AcademicYear).filter(
                AcademicYear.school_id == school_id
            ).first()
            if not ay:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No academic year is configured for this school")
            data["academic_year_id"] = ay.id
        academic_year = db.query(AcademicYear).filter(
            AcademicYear.id == data["academic_year_id"], AcademicYear.school_id == school_id
        ).first()
        if not academic_year:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Academic year does not belong to this school")

        created = crud_timetable.create(db, school_id=school_id, obj_in=data)
        return serialize_timetable(created)

    @staticmethod
    def update_timetable(
        db: Session,
        timetable_id: int,
        obj_in: Union[TimetableUpdate, dict],
        school_id: Optional[int] = None
    ) -> Dict[str, Any]:
        timetable = crud_timetable.get(db, timetable_id)
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable entry not found"
            )
        if school_id is not None and timetable.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: timetable does not belong to your school"
            )

        data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else (
            obj_in.dict(exclude_unset=True) if hasattr(obj_in, "dict") else dict(obj_in)
        )

        effective_grade_id = data.get("grade_id") or timetable.grade_id
        effective_section_id = data.get("section_id") or timetable.section_id
        grade = db.query(Grade).filter(Grade.id == effective_grade_id, Grade.school_id == (school_id or timetable.school_id)).first()
        section = db.query(Section).filter(Section.id == effective_section_id).first()
        if not grade or not section or section.school_id != (school_id or timetable.school_id) or section.grade_id != effective_grade_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section must belong to the selected class and school")
        if "subject_id" in data:
            subject = db.query(Subject).filter(Subject.id == data["subject_id"], Subject.school_id == (school_id or timetable.school_id)).first()
            if not subject:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject does not belong to this school")
        if "teacher_id" in data:
            teacher = db.query(Teacher).filter(Teacher.id == data["teacher_id"], Teacher.school_id == (school_id or timetable.school_id)).first()
            if not teacher:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Teacher does not belong to this school")
        if "academic_year_id" in data:
            ay = db.query(AcademicYear).filter(AcademicYear.id == data["academic_year_id"], AcademicYear.school_id == (school_id or timetable.school_id)).first()
            if not ay:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Academic year does not belong to this school")

        start_val = data.get("start_time") or timetable.start_time
        end_val = data.get("end_time") or timetable.end_time

        start_t = parse_time(start_val)
        end_t = parse_time(end_val)
        if end_t <= start_t:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be later than start time"
            )

        updated = crud_timetable.update(db, db_obj=timetable, obj_in=data)
        return serialize_timetable(updated)

    @staticmethod
    def delete_timetable(db: Session, timetable_id: int, school_id: Optional[int] = None) -> Dict[str, Any]:
        timetable = crud_timetable.get(db, timetable_id)
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable entry not found"
            )
        if school_id is not None and timetable.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: timetable does not belong to your school"
            )
        result = serialize_timetable(timetable)
        crud_timetable.delete(db, id=timetable_id)
        return result

    @staticmethod
    def copy_timetable(db: Session, timetable_id: int, copy_in: TimetableCopy, school_id: Optional[int] = None) -> Dict[str, Any]:
        source = crud_timetable.get(db, timetable_id)
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source timetable not found"
            )
        if school_id is not None and source.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: source timetable does not belong to your school"
            )
        
        target_grade_id = copy_in.target_grade_id if copy_in.target_grade_id is not None else source.grade_id
        target_section_id = copy_in.target_section_id if copy_in.target_section_id is not None else source.section_id

        data = {
            "academic_year_id": source.academic_year_id,
            "grade_id": target_grade_id,
            "section_id": target_section_id,
            "subject_id": source.subject_id,
            "teacher_id": source.teacher_id,
            "day_of_week": source.day_of_week,
            "start_time": source.start_time,
            "end_time": source.end_time,
            "room_number": source.room_number,
        }
        created = crud_timetable.create(db, school_id=source.school_id, obj_in=data)
        return serialize_timetable(created)

