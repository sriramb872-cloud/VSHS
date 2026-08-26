# app/routers/v1/settings.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.settings import (
    SuperAdminSettingsResponse,
    SuperAdminSettingsUpdate,
    PrincipalSettingsResponse,
    PrincipalSettingsUpdate,
    UserProfileSettingsResponse,
    UserProfileSettingsBase,
    UserPasswordChange
)
from app.services.settings import SettingsService

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/super-admin", response_model=SuperAdminSettingsResponse)
def get_super_admin_settings(db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_active_user)):
    return SettingsService.get_super_admin(db, current_user)

@router.put("/super-admin", response_model=SuperAdminSettingsResponse)
def update_super_admin_settings(payload: SuperAdminSettingsUpdate, db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_active_user)):
    return SettingsService.update_super_admin(db, current_user, payload)

@router.get("/principal", response_model=PrincipalSettingsResponse)
def get_principal_settings(db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_active_user)):
    return SettingsService.get_principal(db, current_user)

@router.put("/principal", response_model=PrincipalSettingsResponse)
def update_principal_settings(payload: PrincipalSettingsUpdate, db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_active_user)):
    return SettingsService.update_principal(db, current_user, payload)

@router.get("/user", response_model=UserProfileSettingsResponse)
def get_user_settings(db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_active_user)):
    return SettingsService.get_user_profile(db, current_user)

@router.put("/user", response_model=UserProfileSettingsResponse)
def update_user_settings(payload: UserProfileSettingsBase, db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_active_user)):
    return SettingsService.update_user_profile(db, current_user, payload)

@router.post("/user/change-password")
def change_user_password(payload: UserPasswordChange, db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_active_user)):
    return SettingsService.change_password(db, current_user, payload)