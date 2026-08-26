# backend-python/app/routers/v1/slip_tests.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/slip-tests", tags=["Slip Tests"])


@router.get("", response_model=List[dict])
def list_slip_tests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return []