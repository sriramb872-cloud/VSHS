# backend-python/app/routers/v1/files.py
import os
import uuid
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
    from PIL import Image
    import io

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5MB).")

    try:
        image = Image.open(io.BytesIO(contents))
        image.verify()
        detected_ext = f".{image.format.lower()}".replace(".jpeg", ".jpg")
    except Exception:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    if detected_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image type.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = detected_ext
    unique_filename = f"photo_user_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    target_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(target_path, "wb") as buffer:
        buffer.write(contents)

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
