# app/services/announcement.py
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.announcement import announcement as crud_announcement
from app.models.announcement import Announcement
from app.models.user import User
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementStatus,
    AnnouncementAudience,
)

class AnnouncementService:
    @staticmethod
    def get_announcement(
        db: Session, announcement_id: int, current_user: Optional[User] = None
    ) -> Announcement:
        school_id = current_user.school_id if (current_user and str(current_user.role).upper() != "SUPER_ADMIN") else None
        announcement = crud_announcement.get(db, announcement_id, school_id=school_id)
        if not announcement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found"
            )
        return announcement

    @staticmethod
    def list_announcements(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        audience: Optional[AnnouncementAudience] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        status: Optional[AnnouncementStatus] = None,
        author_id: Optional[int] = None,
        current_user: Optional[User] = None,
    ) -> Tuple[List[Announcement], int]:
        school_id = current_user.school_id if (current_user and str(current_user.role).upper() != "SUPER_ADMIN") else None
        user_role = str(current_user.role).upper() if current_user else None

        if user_role == "STUDENT":
            # Force published and resolve student's current grade/section
            from app.models.student import Student
            from app.models.student_enrollment import StudentEnrollment
            student = db.query(Student).filter(Student.user_id == current_user.id).first()
            enrollment = None
            if student:
                enrollment = (
                    db.query(StudentEnrollment)
                    .filter(StudentEnrollment.student_id == student.id)
                    .order_by(StudentEnrollment.id.desc())
                    .first()
                )
            student_grade_id = enrollment.section.grade_id if (enrollment and enrollment.section) else None
            student_section_id = enrollment.section_id if enrollment else None
            return crud_announcement.get_multi_for_student(
                db, skip=skip, limit=limit, school_id=school_id,
                grade_id=student_grade_id, section_id=student_section_id,
            )

        return crud_announcement.get_multi(
            db,
            skip=skip,
            limit=limit,
            school_id=school_id,
            audience=audience,
            grade_id=grade_id,
            section_id=section_id,
            status=status,
            author_id=author_id,
        )

    @staticmethod
    def create_announcement(
        db: Session, obj_in: AnnouncementCreate, current_user: User
    ) -> Announcement:
        user_role = str(current_user.role).upper()
        if user_role == "STUDENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students are not permitted to create announcements"
            )
        if user_role == "TEACHER":
            if obj_in.audience == AnnouncementAudience.SCHOOL_WIDE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Teachers cannot create school-wide announcements"
                )
        if obj_in.audience == AnnouncementAudience.PARENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parents audience is not supported in this version"
            )

        school_id = current_user.school_id
        if user_role == "SUPER_ADMIN":
            if not obj_in.school_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="school_id is required for Super Admin announcements"
                )
            from app.models.school import School
            school = db.query(School).filter(School.id == obj_in.school_id).first()
            if not school:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="School not found"
                )
            school_id = obj_in.school_id
        elif not school_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School context required"
            )

        from app.models.grade import Grade
        from app.models.section import Section
        from app.models.academic_year import AcademicYear

        if school_id:
            if obj_in.grade_id:
                grade = db.query(Grade).filter(Grade.id == obj_in.grade_id, Grade.school_id == school_id).first()
                if not grade:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade does not belong to this school")
            if obj_in.section_id:
                section = db.query(Section).filter(Section.id == obj_in.section_id, Section.school_id == school_id).first()
                if not section:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section does not belong to this school")
                if obj_in.grade_id and section.grade_id != obj_in.grade_id:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section does not belong to the selected grade")
            if obj_in.academic_year_id:
                ay = db.query(AcademicYear).filter(AcademicYear.id == obj_in.academic_year_id, AcademicYear.school_id == school_id).first()
                if not ay:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Academic year does not belong to this school")

        created = crud_announcement.create(db, obj_in=obj_in, author_id=current_user.id, school_id=school_id)

        if getattr(created, "status", None) == AnnouncementStatus.PUBLISHED:
            AnnouncementService._trigger_notifications(db, created)

        return created

    @staticmethod
    def update_announcement(
        db: Session, announcement_id: int, obj_in: AnnouncementUpdate, current_user: User
    ) -> Announcement:
        announcement = AnnouncementService.get_announcement(db, announcement_id, current_user=current_user)
        user_role = str(current_user.role).upper()
        if user_role == "STUDENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot modify announcements"
            )
        if user_role == "TEACHER" and getattr(announcement, "created_by", None) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teachers can only edit their own announcements"
            )
        if obj_in.audience == AnnouncementAudience.PARENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parents audience is not supported in this version"
            )

        school_id = announcement.school_id
        from app.models.grade import Grade
        from app.models.section import Section
        from app.models.academic_year import AcademicYear

        if obj_in.grade_id:
            grade = db.query(Grade).filter(Grade.id == obj_in.grade_id, Grade.school_id == school_id).first()
            if not grade:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade does not belong to this school")
        if obj_in.section_id:
            section = db.query(Section).filter(Section.id == obj_in.section_id, Section.school_id == school_id).first()
            if not section:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section does not belong to this school")
            effective_grade = obj_in.grade_id or announcement.grade_id
            if effective_grade and section.grade_id != effective_grade:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section does not belong to the selected grade")
        if obj_in.academic_year_id:
            ay = db.query(AcademicYear).filter(AcademicYear.id == obj_in.academic_year_id, AcademicYear.school_id == school_id).first()
            if not ay:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Academic year does not belong to this school")

        updated = crud_announcement.update(db, db_obj=announcement, obj_in=obj_in)

        if getattr(updated, "status", None) == AnnouncementStatus.PUBLISHED:
            AnnouncementService._trigger_notifications(updated)

        return updated

    @staticmethod
    def delete_announcement(
        db: Session, announcement_id: int, current_user: User
    ) -> Announcement:
        announcement = AnnouncementService.get_announcement(db, announcement_id, current_user=current_user)
        user_role = str(current_user.role).upper()
        if user_role == "STUDENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot modify announcements"
            )
        if user_role == "TEACHER" and getattr(announcement, "created_by", None) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teachers can only delete their own announcements"
            )

        return crud_announcement.delete(db, id=announcement_id)

    @staticmethod
    def publish_announcement(db: Session, announcement_id: int, current_user: User) -> Announcement:
        announcement = AnnouncementService.get_announcement(db, announcement_id, current_user=current_user)
        update_in = AnnouncementUpdate(status=AnnouncementStatus.PUBLISHED)
        updated = crud_announcement.update(db, db_obj=announcement, obj_in=update_in)

        AnnouncementService._trigger_notifications(updated)
        return updated

    @staticmethod
    def archive_announcement(db: Session, announcement_id: int, current_user: User) -> Announcement:
        user_role = str(current_user.role).upper()
        if user_role not in ("SUPER_ADMIN", "PRINCIPAL"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principals and Super Admins can archive announcements"
            )
        announcement = AnnouncementService.get_announcement(db, announcement_id, current_user=current_user)
        update_in = AnnouncementUpdate(status=AnnouncementStatus.ARCHIVED)
        return crud_announcement.update(db, db_obj=announcement, obj_in=update_in)

    @staticmethod
    def _trigger_notifications(db: Session, announcement: Announcement) -> None:
        from app.services.notification import NotificationService
        NotificationService.notify_announcement(db, announcement)

    """
SCHOLARIS ERP

Module:
Description:

TODO:
"""
