# app/routers/v1/notification.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationUpdate,
    TeacherClassInfoResponse,
)
from app.services.notification import NotificationService
from app.models.user import UserModel

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
def read_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter by category: PUBLIC, CLASS, CLASS_TEACHER, STAFF"),
    notification_type: Optional[str] = Query(None, description="Filter by notification_type"),
    unread_only: Optional[bool] = None,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    items, total, unread_count = NotificationService.get_user_notifications(
        db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        category=category,
        notification_type=notification_type,
        unread_only=unread_only,
    )
    return {"total": total, "items": items, "unread_count": unread_count}


@router.get("/teacher/class-info", response_model=TeacherClassInfoResponse)
def get_teacher_class_info(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    return NotificationService.get_teacher_class_info(db, current_user=current_user)


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    obj_in: NotificationCreate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return NotificationService.create_notification(db, obj_in=obj_in, current_user=current_user)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    notification = NotificationService.mark_as_read(db, notification_id=notification_id, current_user=current_user)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or unauthorized",
        )
    return notification


@router.post("/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_as_read(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    count = NotificationService.mark_all_read(db, user_id=current_user.id)
    return {"message": "All notifications marked as read", "updated_count": count}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    success = NotificationService.delete_notification(db, notification_id=notification_id, current_user=current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or unauthorized",
        )
    return None