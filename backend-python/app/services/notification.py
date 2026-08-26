# app/services/notification.py
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.crud.notification import notification as crud_notification
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationType,
    NotificationCategory,
    TeacherClassInfoResponse,
    StudentSummary,
)
from app.models.notification import Notification
from app.models.user import User
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.section import Section


class NotificationService:
    @staticmethod
    def get_notification(db: Session, notification_id: int) -> Optional[Notification]:
        return crud_notification.get(db, notification_id=notification_id)

    @staticmethod
    def get_user_notifications(
        db: Session,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        notification_type: Optional[str] = None,
        unread_only: Optional[bool] = None,
    ) -> Tuple[List[dict], int, int]:
        return crud_notification.get_multi_for_user(
            db,
            current_user=current_user,
            skip=skip,
            limit=limit,
            category=category,
            notification_type=notification_type,
            unread_only=unread_only,
        )

    @staticmethod
    def get_teacher_class_info(db: Session, current_user: User) -> TeacherClassInfoResponse:
        role = str(current_user.role).upper()
        if role not in ("TEACHER", "SUPER_ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only teachers can access class assignment info"
            )

        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not teacher:
            return TeacherClassInfoResponse(is_class_teacher=False, students=[])

        # Find section where teacher is assigned as class teacher
        section = db.query(Section).filter(Section.class_teacher_id == teacher.id).first()
        if not section:
            return TeacherClassInfoResponse(is_class_teacher=False, students=[])

        # Get enrolled students
        enrollments = db.query(StudentEnrollment).filter(StudentEnrollment.section_id == section.id).all()
        student_list: List[StudentSummary] = []

        for en in enrollments:
            student = en.student
            if student:
                full_name = student.user.display_name if (student.user and student.user.display_name) else f"Student #{student.id}"
                roll_num = en.roll_number or student.roll_number
                student_list.append(
                    StudentSummary(
                        id=student.id,
                        student_id=student.id,
                        full_name=full_name,
                        roll_number=roll_num
                    )
                )

        grade_name = section.grade.name if (section.grade and hasattr(section.grade, "name")) else ""
        section_name = section.name

        return TeacherClassInfoResponse(
            is_class_teacher=True,
            section_id=section.id,
            section_name=section_name,
            grade_name=grade_name,
            students=student_list
        )

    @staticmethod
    def create_notification(db: Session, obj_in: NotificationCreate, current_user: User) -> dict:
        user_role = str(current_user.role).upper()
        school_id = current_user.school_id
        sender_id = current_user.id
        notif_type = obj_in.notification_type.value if hasattr(obj_in.notification_type, "value") else str(obj_in.notification_type)

        # 1. Students are strictly prohibited from creating notifications
        if user_role == "STUDENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students are not permitted to create notifications"
            )

        target_class_id = None
        target_student_id = None
        target_user_id = None
        category = None

        # 2. PRINCIPAL logic (Allowed: PUBLIC, STAFF_ONLY, CLASS_ONLY)
        if user_role in ("PRINCIPAL", "SUPER_ADMIN"):
            allowed_principal_types = ("PUBLIC", "STAFF_ONLY", "CLASS_ONLY")
            if notif_type not in allowed_principal_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Principals can only create: {', '.join(allowed_principal_types)}"
                )

            if notif_type == "PUBLIC":
                category = "PUBLIC"
                target_class_id = None
                target_student_id = None

            elif notif_type == "STAFF_ONLY":
                category = "STAFF"
                target_class_id = None
                target_student_id = None

            elif notif_type == "CLASS_ONLY":
                category = "CLASS"
                if not obj_in.target_class_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="target_class_id is required for Class Only notifications"
                    )

                # Validate class exists and belongs to school
                section = db.query(Section).filter(Section.id == obj_in.target_class_id).first()
                if not section:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Target class not found"
                    )
                if school_id and section.school_id != school_id and user_role != "SUPER_ADMIN":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Target class does not belong to your school"
                    )
                target_class_id = section.id
                # Principal cannot target individual students
                target_student_id = None

        # 3. TEACHER logic (Allowed: ONLY_FOR_CLASS, ONLY_FOR_STUDENT, PUBLIC)
        elif user_role == "TEACHER":
            allowed_teacher_types = ("ONLY_FOR_CLASS", "ONLY_FOR_STUDENT", "PUBLIC")
            if notif_type not in allowed_teacher_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Teachers can only create: {', '.join(allowed_teacher_types)}"
                )

            teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
            if not teacher:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Teacher profile not found"
                )

            if notif_type in ("ONLY_FOR_CLASS", "ONLY_FOR_STUDENT"):
                # Must be a class teacher
                class_section = db.query(Section).filter(Section.class_teacher_id == teacher.id).first()
                if not class_section:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You are not assigned as a Class Teacher for any class"
                    )

                # Automatically lock target class to teacher's assigned class-teacher class
                target_class_id = class_section.id
                category = "CLASS_TEACHER"

                if notif_type == "ONLY_FOR_CLASS":
                    target_student_id = None

                elif notif_type == "ONLY_FOR_STUDENT":
                    if not obj_in.target_student_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="target_student_id is required for student-specific notification"
                        )

                    # Validate that target student belongs to teacher's class-teacher section
                    enrollment = db.query(StudentEnrollment).filter(
                        StudentEnrollment.student_id == obj_in.target_student_id,
                        StudentEnrollment.section_id == class_section.id
                    ).first()

                    if not enrollment:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Target student is not enrolled in your assigned class"
                        )

                    target_student_id = obj_in.target_student_id
                    target_student = db.query(Student).filter(Student.id == target_student_id).first()
                    if target_student:
                        target_user_id = target_student.user_id

            elif notif_type == "PUBLIC":
                category = "PUBLIC"
                target_class_id = None
                target_student_id = None

        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized role for creating notifications"
            )

        created_notif = crud_notification.create(
            db,
            title=obj_in.title,
            message=obj_in.message,
            notification_type=notif_type,
            sender_id=sender_id,
            sender_role=user_role,
            school_id=school_id,
            category=category,
            target_class_id=target_class_id,
            target_student_id=target_student_id,
            user_id=target_user_id,
        )

        return crud_notification.serialize(created_notif)

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, current_user: User) -> Optional[dict]:
        db_obj = crud_notification.get(db, notification_id=notification_id)
        if not db_obj:
            return None
        # User can mark as read if it's their direct notif, or broadcast
        updated = crud_notification.update(db, db_obj=db_obj, obj_in=NotificationUpdate(is_read=True))
        return crud_notification.serialize(updated)

    @staticmethod
    def mark_all_read(db: Session, user_id: int) -> int:
        return crud_notification.mark_all_as_read(db, user_id=user_id)

    @staticmethod
    def delete_notification(db: Session, notification_id: int, current_user: User) -> bool:
        db_obj = crud_notification.get(db, notification_id=notification_id)
        if not db_obj:
            return False

        user_role = str(current_user.role).upper()
        # Students can NEVER delete notifications
        if user_role == "STUDENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot delete notifications"
            )

        # Principal & Super Admin can delete notifications in their school
        if user_role in ("SUPER_ADMIN", "PRINCIPAL"):
            if user_role == "PRINCIPAL" and db_obj.school_id != current_user.school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot delete notification from another school"
                )
            crud_notification.remove(db, id=notification_id)
            return True

        # Teacher can only delete their own sent notifications
        if user_role == "TEACHER":
            if db_obj.sender_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Teachers can only delete their own notifications"
                )
            crud_notification.remove(db, id=notification_id)
            return True

        return False