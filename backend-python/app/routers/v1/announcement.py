# app/routers/v1/announcement.py
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.announcement import (
    AnnouncementResponse,
    AnnouncementListResponse,
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementStatus,
    AnnouncementAudience,
)
from app.services.announcement import AnnouncementService
from app.models.user import UserModel

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("/", response_model=AnnouncementListResponse)
def list_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    audience: Optional[AnnouncementAudience] = None,
    grade_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status_filter: Optional[AnnouncementStatus] = Query(None, alias="status"),
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    items, total = AnnouncementService.list_announcements(
        db,
        skip=skip,
        limit=limit,
        audience=audience,
        grade_id=grade_id,
        section_id=section_id,
        status=status_filter,
        current_user=current_user,
    )
    return {"total": total, "items": items}

@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement(
    announcement_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return AnnouncementService.get_announcement(db, announcement_id=announcement_id, current_user=current_user)

@router.post("/", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    obj_in: AnnouncementCreate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_teacher),
):
    return AnnouncementService.create_announcement(db, obj_in=obj_in, current_user=current_user)

@router.put("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    obj_in: AnnouncementUpdate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return AnnouncementService.update_announcement(db, announcement_id=announcement_id, obj_in=obj_in, current_user=current_user)

@router.delete("/{announcement_id}", response_model=AnnouncementResponse)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return AnnouncementService.delete_announcement(db, announcement_id=announcement_id, current_user=current_user)

@router.post("/{announcement_id}/publish", response_model=AnnouncementResponse)
def publish_announcement(
    announcement_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    return AnnouncementService.publish_announcement(db, announcement_id=announcement_id, current_user=current_user)

@router.post("/{announcement_id}/archive", response_model=AnnouncementResponse)
def archive_announcement(
    announcement_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    return AnnouncementService.archive_announcement(db, announcement_id=announcement_id, current_user=current_user)