# backend-python/app/routers/v1/files.py
import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/files", tags=["Files"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "media", "profile_photos"))


@router.post("/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files (JPEG, PNG, WebP) are permitted for profile photos."
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    unique_filename = f"photo_user_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    target_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    photo_url = f"/media/profile_photos/{unique_filename}"
    current_user.profile_photo = photo_url
    db.commit()
    db.refresh(current_user)

    return {
        "photo_url": photo_url,
        "message": "Profile photo uploaded successfully"
    }


@router.get("/metadata/{file_id}")
def get_file_metadata(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File metadata not found")