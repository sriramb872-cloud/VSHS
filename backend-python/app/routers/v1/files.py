# backend-python/app/routers/v1/files.py
import io
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.upload import Upload
from app.models.user import User

router = APIRouter(prefix="/files", tags=["Files"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "media", "profile_photos"))

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def _verify_image(contents: bytes) -> str:
    """Validate the bytes really are an image and return the detected extension.

    Pillow is a declared dependency (requirements.txt pins it), but a missing or
    broken install used to surface as an unhandled 500 for *every* upload,
    including obviously invalid ones, because the import sat above all
    validation. The cheap checks now run first and a genuinely unavailable
    decoder reports 503 instead of 500.
    """
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - environment problem
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image validation is unavailable on this server (Pillow is not installed).",
        ) from exc

    try:
        image = Image.open(io.BytesIO(contents))
        image.verify()
        detected_ext = f".{image.format.lower()}".replace(".jpeg", ".jpg")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image.",
        ) from exc

    if detected_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
        )
    return detected_ext


@router.post("/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    contents = await file.read()

    # Cheap checks first: they need no third-party decoder, so an oversized or
    # obviously wrong file is rejected even if image decoding is unavailable.
    if len(contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 5MB).",
        )

    declared_ext = os.path.splitext(file.filename or "")[1].lower()
    if declared_ext and declared_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
        )

    ext = _verify_image(contents)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_filename = f"photo_user_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    target_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(target_path, "wb") as buffer:
        buffer.write(contents)

    photo_url = f"/media/profile_photos/{unique_filename}"
    current_user.profile_photo = photo_url
    db.commit()
    db.refresh(current_user)

    # Record the upload so the file is auditable and retrievable by id. The
    # `Upload` row is what `GET /files/metadata/{id}` reads; previously that
    # endpoint was an unconditional 404 stub and nothing was ever stored.
    record = Upload(
        filename=unique_filename,
        original_filename=file.filename or unique_filename,
        file_path=os.path.relpath(target_path, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))).replace("\\", "/"),
        content_type=file.content_type or "application/octet-stream",
        file_size=len(contents),
        entity_type="USER_PROFILE_PHOTO",
        entity_id=str(current_user.id),
        uploaded_by_id=current_user.id,
        school_id=current_user.school_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "photo_url": photo_url,
        "file_id": record.id,
        "file_size": record.file_size,
        "content_type": record.content_type,
        "message": "Profile photo uploaded successfully"
    }


@router.get("/metadata/{file_id}")
def get_file_metadata(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Metadata for a stored upload.

    Was an unconditional 404 stub, which advertised a capability the API did
    not have. It now reads the real `uploads` row written by the upload
    endpoints.

    Authorization: a Super Admin sees any upload; everyone else only uploads
    they own or that belong to their own school, so metadata (which discloses
    original filenames and storage paths) cannot leak across tenants.
    """
    record = db.query(Upload).filter(Upload.id == file_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File metadata not found")

    role = str(getattr(current_user.role, "value", current_user.role)).upper()
    if role != "SUPER_ADMIN":
        if record.uploaded_by_id != current_user.id and record.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    absolute_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", record.file_path)
    )
    exists = os.path.isfile(absolute_path)

    return {
        "id": record.id,
        "filename": record.filename,
        "original_filename": record.original_filename,
        "file_path": record.file_path,
        "content_type": record.content_type,
        "file_size": record.file_size,
        "entity_type": record.entity_type,
        "entity_id": record.entity_id,
        "uploaded_by_id": record.uploaded_by_id,
        "school_id": record.school_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "exists_on_disk": exists,
    }


@router.delete("/profile-photo")
def delete_profile_photo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Clear the caller's profile photo.

    The stored file and its `uploads` row are deliberately kept so the history
    of what was uploaded stays auditable; only the pointer on the user is
    dropped, so the UI cannot keep rendering a photo the user removed.
    """
    if not current_user.profile_photo:
        return {"message": "No profile photo to remove.", "profile_photo": None}

    current_user.profile_photo = None
    db.commit()
    db.refresh(current_user)
    return {"message": "Profile photo removed.", "profile_photo": None}


@router.get("/metadata")
def list_file_metadata(    entity_type: str | None = None,
    entity_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List uploads visible to the caller, newest first."""
    if skip < 0 or not 1 <= limit <= 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="limit must be between 1 and 200 and skip must be >= 0",
        )

    query = db.query(Upload)
    role = str(getattr(current_user.role, "value", current_user.role)).upper()
    if role != "SUPER_ADMIN":
        query = query.filter(
            (Upload.uploaded_by_id == current_user.id) | (Upload.school_id == current_user.school_id)
        )
    if entity_type:
        query = query.filter(Upload.entity_type == entity_type)
    if entity_id:
        query = query.filter(Upload.entity_id == str(entity_id))

    return [
        {
            "id": u.id,
            "filename": u.filename,
            "original_filename": u.original_filename,
            "file_path": u.file_path,
            "content_type": u.content_type,
            "file_size": u.file_size,
            "entity_type": u.entity_type,
            "entity_id": u.entity_id,
            "uploaded_by_id": u.uploaded_by_id,
            "school_id": u.school_id,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in query.order_by(Upload.created_at.desc(), Upload.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    ]
