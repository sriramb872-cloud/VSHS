# app/crud/notification.py
from datetime import datetime
from typing import List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.notification import Notification
from app.models.notification_read import NotificationRead
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.user import User
from app.models.section import Section
from app.models.grade import Grade
from app.schemas.notification import NotificationCreate, NotificationUpdate


class CRUDNotification:
    def get(self, db: Session, notification_id: int) -> Optional[Notification]:
        return db.query(Notification).filter(Notification.id == notification_id).first()

    def serialize(self, item: Notification, is_read: bool = False) -> dict:
        sender_name = None
        if item.sender:
            sender_name = getattr(item.sender, "display_name", None)

        target_class_name = None
        if item.target_class:
            grade_name = ""
            if item.target_class.grade:
                grade_name = getattr(item.target_class.grade, "name", "")
            sec_name = getattr(item.target_class, "name", "")
            target_class_name = f"{grade_name} - {sec_name}".strip(" -")

        target_student_name = None
        if item.target_student and item.target_student.user:
            target_student_name = getattr(item.target_student.user, "display_name", None)

        return {
            "id": item.id,
            "school_id": item.school_id,
            "sender_id": item.sender_id,
            "sender_name": sender_name,
            "sender_role": item.sender_role,
            "title": item.title,
            "message": item.message,
            "notification_type": item.notification_type,
            "target_class_id": item.target_class_id,
            "target_class_name": target_class_name,
            "target_student_id": item.target_student_id,
            "target_student_name": target_student_name,
            "category": item.category,
            "user_id": item.user_id,
            "is_read": is_read,
            "reference_id": item.reference_id,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def _visible_query(self, db: Session, current_user: User, category: Optional[str], notification_type: Optional[str]):
        """The role-based visibility filter, shared between listing and mark-all-read."""
        role = str(current_user.role).upper()
        school_id = current_user.school_id
        query = db.query(Notification)

        if role == "STUDENT":
            student = db.query(Student).filter(Student.user_id == current_user.id).first()
            student_id = student.id if student else -1

            enrollments = db.query(StudentEnrollment).filter(StudentEnrollment.student_id == student_id).all()
            section_ids = [e.section_id for e in enrollments] if enrollments else []

            cond_public = and_(
                Notification.notification_type == "PUBLIC",
                Notification.school_id == school_id if school_id else True
            )
            cond_class = and_(
                Notification.notification_type == "CLASS_ONLY",
                Notification.target_class_id.in_(section_ids) if section_ids else False
            )
            cond_class_teacher = or_(
                and_(
                    Notification.notification_type == "ONLY_FOR_CLASS",
                    Notification.target_class_id.in_(section_ids) if section_ids else False
                ),
                and_(
                    Notification.notification_type == "ONLY_FOR_STUDENT",
                    or_(
                        Notification.target_student_id == student_id,
                        Notification.user_id == current_user.id
                    )
                )
            )
            cond_direct = Notification.user_id == current_user.id

            if category == "PUBLIC":
                query = query.filter(cond_public)
            elif category == "CLASS":
                query = query.filter(cond_class)
            elif category == "CLASS_TEACHER":
                query = query.filter(cond_class_teacher)
            else:
                query = query.filter(or_(cond_public, cond_class, cond_class_teacher, cond_direct))

        elif role == "TEACHER":
            teacher_cond = or_(
                and_(Notification.notification_type == "PUBLIC", Notification.school_id == school_id) if school_id else (Notification.notification_type == "PUBLIC"),
                and_(Notification.notification_type == "STAFF_ONLY", Notification.school_id == school_id) if school_id else (Notification.notification_type == "STAFF_ONLY"),
                Notification.sender_id == current_user.id,
                Notification.user_id == current_user.id,
            )
            query = query.filter(teacher_cond)
            if category:
                query = query.filter(Notification.category == category)
            if notification_type:
                query = query.filter(Notification.notification_type == notification_type)

        elif role == "PRINCIPAL":
            if school_id:
                query = query.filter(
                    or_(
                        Notification.school_id == school_id,
                        Notification.sender_id == current_user.id,
                        Notification.user_id == current_user.id
                    )
                )
            if category:
                query = query.filter(Notification.category == category)
            if notification_type:
                query = query.filter(Notification.notification_type == notification_type)

        elif role == "SUPER_ADMIN":
            if school_id:
                query = query.filter(Notification.school_id == school_id)
            if category:
                query = query.filter(Notification.category == category)
            if notification_type:
                query = query.filter(Notification.notification_type == notification_type)

        return query

    def get_multi_for_user(
        self,
        db: Session,
        *,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        notification_type: Optional[str] = None,
        unread_only: Optional[bool] = None
    ) -> Tuple[List[dict], int, int]:
        query = self._visible_query(db, current_user, category, notification_type)

        read_ids_subq = db.query(NotificationRead.notification_id).filter(
            NotificationRead.user_id == current_user.id,
            NotificationRead.is_read == True,
        )
        read_ids = {row[0] for row in read_ids_subq.all()}

        if unread_only is True:
            query = query.filter(~Notification.id.in_(read_ids_subq))
        elif unread_only is False:
            query = query.filter(Notification.id.in_(read_ids_subq))

        total = query.count()

        base_query = self._visible_query(db, current_user, category, notification_type)
        unread_count = base_query.filter(~Notification.id.in_(read_ids_subq)).count()

        items = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
        serialized_items = [self.serialize(item, is_read=(item.id in read_ids)) for item in items]

        return serialized_items, total, unread_count

    def create(
        self,
        db: Session,
        *,
        title: str,
        message: str,
        notification_type: str,
        sender_id: int,
        sender_role: str,
        school_id: Optional[int],
        category: Optional[str] = None,
        target_class_id: Optional[int] = None,
        target_student_id: Optional[int] = None,
        user_id: Optional[int] = None,
        reference_id: Optional[int] = None
    ) -> Notification:
        db_obj = Notification(
            title=title,
            message=message,
            notification_type=notification_type,
            sender_id=sender_id,
            sender_role=sender_role,
            school_id=school_id,
            category=category,
            target_class_id=target_class_id,
            target_student_id=target_student_id,
            user_id=user_id,
            reference_id=reference_id,
            is_read=False,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Notification, obj_in: NotificationUpdate) -> Notification:
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def mark_read(self, db: Session, *, notification_id: int, user_id: int) -> None:
        existing = db.query(NotificationRead).filter(
            NotificationRead.notification_id == notification_id,
            NotificationRead.user_id == user_id,
        ).first()
        if existing:
            if not existing.is_read:
                existing.is_read = True
                existing.read_at = datetime.utcnow()
                db.add(existing)
                db.commit()
            return
        db.add(NotificationRead(
            notification_id=notification_id,
            user_id=user_id,
            is_read=True,
            read_at=datetime.utcnow(),
        ))
        db.commit()

    def mark_all_as_read(self, db: Session, *, current_user: User) -> int:
        visible_query = self._visible_query(db, current_user, category=None, notification_type=None)
        already_read_subq = db.query(NotificationRead.notification_id).filter(
            NotificationRead.user_id == current_user.id,
            NotificationRead.is_read == True,
        )
        unread_ids = [
            row[0] for row in
            visible_query.filter(~Notification.id.in_(already_read_subq)).with_entities(Notification.id).all()
        ]
        now = datetime.utcnow()
        for nid in unread_ids:
            existing = db.query(NotificationRead).filter(
                NotificationRead.notification_id == nid,
                NotificationRead.user_id == current_user.id,
            ).first()
            if existing:
                existing.is_read = True
                existing.read_at = now
                db.add(existing)
            else:
                db.add(NotificationRead(notification_id=nid, user_id=current_user.id, is_read=True, read_at=now))
        db.commit()
        return len(unread_ids)

    def remove(self, db: Session, *, id: int) -> Optional[Notification]:
        obj = db.query(Notification).filter(Notification.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


notification = CRUDNotification()