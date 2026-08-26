# app/routers/v1/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import UserModel
from app.schemas.dashboard import (
    SuperAdminDashboardResponse,
    PrincipalDashboardResponse,
    TeacherDashboardResponse,
    StudentDashboardResponse,
    ParentDashboardResponse,
)
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/super-admin", response_model=SuperAdminDashboardResponse)
def get_super_admin_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return DashboardService.get_super_admin_dashboard(db, current_user)

@router.get("/principal", response_model=PrincipalDashboardResponse)
def get_principal_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return DashboardService.get_principal_dashboard(db, current_user)

@router.get("/teacher", response_model=TeacherDashboardResponse)
def get_teacher_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return DashboardService.get_teacher_dashboard(db, current_user)

@router.get("/student", response_model=StudentDashboardResponse)
def get_student_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return DashboardService.get_student_dashboard(db, current_user)

@router.get("/parent", response_model=ParentDashboardResponse)
def get_parent_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    return DashboardService.get_parent_dashboard(db, current_user)