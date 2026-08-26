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

        school_id = current_user.school_id
        if not school_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School context required"
            )

        created = crud_announcement.create(db, obj_in=obj_in, author_id=current_user.id, school_id=school_id)

        if getattr(created, "status", None) == AnnouncementStatus.PUBLISHED:
            AnnouncementService._trigger_notifications(created)

        return created

    @staticmethod
    def update_announcement(
        db: Session, announcement_id: int, obj_in: AnnouncementUpdate, current_user: User
    ) -> Announcement:
        announcement = AnnouncementService.get_announcement(db, announcement_id, current_user=current_user)
        user_role = str(current_user.role).upper()
        if user_role == "TEACHER" and getattr(announcement, "created_by", None) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teachers can only edit their own announcements"
            )

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
    def _trigger_notifications(announcement: Announcement) -> None:
        # Structure for notification integration without modifying existing module
        pass

    """
SCHOLARIS ERP

Module:
Description:

TODO:
"""
