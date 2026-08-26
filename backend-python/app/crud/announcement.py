# app/crud/announcement.py
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.announcement import Announcement
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementStatus, AnnouncementAudience

class CRUDAnnouncement:
    def get(self, db: Session, announcement_id: int, school_id: Optional[int] = None) -> Optional[Announcement]:
        query = db.query(Announcement).filter(Announcement.id == announcement_id)
        if school_id is not None:
            query = query.filter(Announcement.school_id == school_id)
        return query.first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50,
        school_id: Optional[int] = None,
        audience: Optional[AnnouncementAudience] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        status: Optional[AnnouncementStatus] = None,
        author_id: Optional[int] = None
    ) -> Tuple[List[Announcement], int]:
        query = db.query(Announcement)

        if school_id is not None:
            query = query.filter(Announcement.school_id == school_id)
        if audience is not None:
            query = query.filter(Announcement.target_role == str(audience))
        if status is not None:
            query = query.filter(Announcement.is_active == (status == AnnouncementStatus.PUBLISHED))
        if author_id is not None:
            query = query.filter(Announcement.created_by == author_id)

        total = query.count()
        items = query.order_by(Announcement.publish_date.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, db: Session, *, obj_in: AnnouncementCreate, author_id: int, school_id: int) -> Announcement:
        audience_val = obj_in.audience.value if hasattr(obj_in.audience, "value") else str(obj_in.audience) if obj_in.audience else "School-Wide"
        priority_val = obj_in.priority.value if hasattr(obj_in.priority, "value") else str(obj_in.priority) if obj_in.priority else "Normal"
        status_val = obj_in.status.value if hasattr(obj_in.status, "value") else str(obj_in.status) if obj_in.status else "Draft"

        db_obj = Announcement(
            school_id=school_id,
            title=obj_in.title,
            content=getattr(obj_in, "description", getattr(obj_in, "content", "")),
            target_role=audience_val,
            priority=priority_val,
            is_active=(status_val == "Published" or obj_in.status == AnnouncementStatus.PUBLISHED),
            publish_date=getattr(obj_in, "publish_date", None),
            expiry_date=getattr(obj_in, "expiry_date", None),
            created_by=author_id,
            academic_year_id=getattr(obj_in, "academic_year_id", None),
            grade_id=getattr(obj_in, "grade_id", None),
            section_id=getattr(obj_in, "section_id", None),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Announcement, obj_in: AnnouncementUpdate
    ) -> Announcement:
        update_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, "dict") else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "title" and value is not None:
                db_obj.title = value
            elif (field == "description" or field == "content") and value is not None:
                db_obj.content = value
            elif field == "audience" and value is not None:
                db_obj.target_role = value.value if hasattr(value, "value") else str(value)
            elif field == "priority" and value is not None:
                db_obj.priority = value.value if hasattr(value, "value") else str(value)
            elif field == "status" and value is not None:
                status_str = value.value if hasattr(value, "value") else str(value)
                db_obj.is_active = (status_str == "Published")
            elif field == "author_id" and value is not None:
                db_obj.created_by = value
            elif field == "publish_date" and value is not None:
                db_obj.publish_date = value
            elif field == "expiry_date" and value is not None:
                db_obj.expiry_date = value
            elif field == "academic_year_id":
                db_obj.academic_year_id = value
            elif field == "grade_id":
                db_obj.grade_id = value
            elif field == "section_id":
                db_obj.section_id = value

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> Announcement:
        obj = db.query(Announcement).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


announcement = CRUDAnnouncement()
"""
SCHOLARIS ERP

Module:
Description:

TODO:
"""
