from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import teacher as teacher_crud
from app.models.teacher import Teacher
from app.models.user import User
from app.models.section import Section
from app.models.timetable import Timetable
from app.core.security import get_password_hash
from app.services.id_generator import generate_employee_id

router = APIRouter(prefix="/teachers", tags=["Teachers"])


def serialize_teacher(t: Teacher, db: Optional[Session] = None) -> dict:
    user = t.user
    assigned_subjects = []
    assigned_sections = []
    if hasattr(t, "grade_subjects") and t.grade_subjects:
        for gs in t.grade_subjects:
            if getattr(gs, "subject", None):
                sub_name = getattr(gs.subject, "name", None) or getattr(gs.subject, "subject_name", None)
                if sub_name:
                    assigned_subjects.append(sub_name)
            if getattr(gs, "grade", None):
                gr_name = getattr(gs.grade, "name", None) or getattr(gs.grade, "grade_name", None)
                if gr_name:
                    assigned_sections.append(gr_name)

    is_active = True
    status_str = "ACTIVE"
    if user and hasattr(user, "is_active"):
        is_active = (user.is_active == "ACTIVE" or user.is_active is True)
        if isinstance(user.is_active, str) and user.is_active.upper() in ["ACTIVE", "ON_LEAVE", "INACTIVE", "SUSPENDED"]:
            status_str = "ON_LEAVE" if user.is_active.upper() == "ON_LEAVE" else ("ACTIVE" if is_active else "INACTIVE")

    school_name = None
    school_code = None
    if getattr(t, "school", None):
        school_name = getattr(t.school, "name", None) or getattr(t.school, "school_name", None)
        school_code = getattr(t.school, "code", None) or getattr(t.school, "school_code", None)

    class_teacher_section = None
    teaching_assignments = []

    if db:
        sec_query = db.query(Section).filter(Section.class_teacher_id == t.id)
        if getattr(t, "school_id", None):
            sec_query = sec_query.filter(Section.school_id == t.school_id)
        sec = sec_query.first()
        if sec:
            gr_name = getattr(sec.grade, "name", "") if getattr(sec, "grade", None) else f"Class {sec.grade_id}"
            class_teacher_section = {
                "id": sec.id,
                "section_id": sec.id,
                "grade_id": sec.grade_id,
                "grade_name": gr_name,
                "name": sec.name,
                "section_name": sec.name,
            }

        tt_query = db.query(Timetable).filter(Timetable.teacher_id == t.id)
        if getattr(t, "school_id", None):
            tt_query = tt_query.filter(Timetable.school_id == t.school_id)
        tt_records = tt_query.all()
        assignments_map = {}
        for tt in tt_records:
            k = (tt.grade_id, tt.section_id, tt.subject_id)
            if k not in assignments_map:
                g_name = getattr(tt.grade, "name", "") if getattr(tt, "grade", None) else f"Class {tt.grade_id}"
                s_name = getattr(tt.section, "name", "") if getattr(tt, "section", None) else ""
                sub_name = getattr(tt.subject, "name", "") or getattr(tt.subject, "subject_name", "") if getattr(tt, "subject", None) else f"Subject #{tt.subject_id}"
                assignments_map[k] = {
                    "grade_id": tt.grade_id,
                    "grade_name": g_name,
                    "section_id": tt.section_id,
                    "section_name": s_name,
                    "subject_id": tt.subject_id,
                    "subject_name": sub_name,
                }
                if sub_name and sub_name not in assigned_subjects:
                    assigned_subjects.append(sub_name)
                sec_display = f"{g_name} - {s_name}" if s_name else g_name
                if sec_display and sec_display not in assigned_sections:
                    assigned_sections.append(sec_display)
        teaching_assignments = list(assignments_map.values())

    role_type = "Class Teacher" if class_teacher_section else "Subject Teacher"
    emp_id = getattr(t, "employee_id", None) or f"EMP{date.today().year}{t.id:03d}"

    return {
        "id": t.id,
        "teacher_id": t.id,
        "school_id": t.school_id,
        "school_name": school_name,
        "school_code": school_code,
        "user_id": t.user_id,
        "display_name": user.display_name if user else None,
        "full_name": user.display_name if user else None,
        "mobile": user.mobile if user else None,
        "email": user.email if user else None,
        "profile_photo": user.profile_photo if user else None,
        "role": "TEACHER",
        "employee_id": emp_id,
        "role_type": role_type,
        "qualification": getattr(t, "qualification", None),
        "department": getattr(t, "department", None),
        "specialization": getattr(t, "department", None) or getattr(t, "qualification", None),
        "joining_date": getattr(t, "joining_date", None),
        "address": getattr(t, "address", None),
        "status": status_str,
        "is_active": is_active,
        "assigned_subjects": list(set(assigned_subjects)),
        "assigned_sections": list(set(assigned_sections)),
        "class_teacher_section": class_teacher_section,
        "teaching_assignments": teaching_assignments,
        "created_at": getattr(t, "created_at", None),
        "updated_at": getattr(t, "updated_at", None),
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_teacher_profile(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))
):
    school_id = payload.get("school_id") or current_user.school_id
    if not school_id and str(current_user.role).upper() != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    # Generate or sanitize Employee ID
    employee_id = payload.get("employee_id")
    if not employee_id or str(employee_id).strip() == "":
        employee_id = generate_employee_id(db, school_id)
    else:
        employee_id = str(employee_id).strip()

    # Check for existing employee ID in school
    existing = db.query(Teacher).filter(Teacher.school_id == school_id, Teacher.employee_id == employee_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Employee ID '{employee_id}' already exists.")

    full_name = payload.get("full_name") or payload.get("display_name") or "New Faculty Member"
    mobile = payload.get("mobile")
    if not mobile or str(mobile).strip() == "":
        mobile = f"FAC{employee_id}"

    # Check for unique mobile in users
    existing_user = db.query(User).filter(User.mobile == mobile).first()
    if existing_user:
        mobile = f"FAC{employee_id}"

    initial_password = payload.get("password") or "Teacher@123"
    hashed_pwd = get_password_hash(initial_password)

    new_user = User(
        school_id=school_id,
        display_name=full_name,
        mobile=mobile,
        email=payload.get("email"),
        profile_photo=payload.get("profile_photo"),
        password_hash=hashed_pwd,
        role="TEACHER",
        is_active="ACTIVE",
    )
    db.add(new_user)
    db.flush()

    join_date = payload.get("joining_date")
    if isinstance(join_date, str) and join_date.strip():
        try:
            join_date = date.fromisoformat(join_date[:10])
        except Exception:
            join_date = date.today()
    elif not join_date:
        join_date = date.today()

    new_teacher = Teacher(
        user_id=new_user.id,
        school_id=school_id,
        employee_id=employee_id,
        qualification=payload.get("qualification"),
        department=payload.get("department") or payload.get("specialization"),
        joining_date=join_date,
        address=payload.get("address"),
    )
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)

    return serialize_teacher(new_teacher, db=db)


@router.get("", response_model=List[dict])
def list_teachers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    school_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    target_school_id = current_user.school_id
    if str(current_user.role).upper() == "SUPER_ADMIN" and school_id:
        target_school_id = school_id

    if not target_school_id and str(current_user.role).upper() != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    if target_school_id:
        teachers = teacher_crud.get_teachers_by_school(db, school_id=target_school_id, skip=skip, limit=limit)
    else:
        teachers = db.query(Teacher).offset(skip).limit(limit).all()

    return [serialize_teacher(t, db=db) for t in teachers]


@router.get("/me", response_model=dict)
def get_my_teacher_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if str(current_user.role).upper() != "TEACHER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")

    return serialize_teacher(teacher, db=db)


@router.get("/me/teaching-classes", response_model=List[dict])
def get_my_teaching_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if str(current_user.role).upper() != "TEACHER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")

    tt_query = db.query(Timetable).filter(Timetable.teacher_id == teacher.id)
    if getattr(teacher, "school_id", None):
        tt_query = tt_query.filter(Timetable.school_id == teacher.school_id)
    tt_records = tt_query.all()
    assignments_map = {}
    for tt in tt_records:
        k = (tt.grade_id, tt.section_id, tt.subject_id)
        if k not in assignments_map:
            g_name = getattr(tt.grade, "name", "") if getattr(tt, "grade", None) else f"Class {tt.grade_id}"
            s_name = getattr(tt.section, "name", "") if getattr(tt, "section", None) else ""
            sub_name = getattr(tt.subject, "name", "") or getattr(tt.subject, "subject_name", "") if getattr(tt, "subject", None) else f"Subject #{tt.subject_id}"
            assignments_map[k] = {
                "grade_id": tt.grade_id,
                "grade_name": g_name,
                "section_id": tt.section_id,
                "section_name": s_name,
                "subject_id": tt.subject_id,
                "subject_name": sub_name,
            }
    return list(assignments_map.values())


@router.post("/me/assign-class-teacher", response_model=dict)
def assign_me_as_class_teacher(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if str(current_user.role).upper() != "TEACHER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")

    section_id = payload.get("section_id")
    if not section_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="section_id is required")

    try:
        section_id = int(section_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid section_id")

    # Check if teacher is already assigned to a class in her school
    existing_assigned_sec = db.query(Section).filter(
        Section.class_teacher_id == teacher.id,
        Section.school_id == teacher.school_id
    ).first()
    if existing_assigned_sec:
        if existing_assigned_sec.id == section_id:
            return serialize_teacher(teacher, db=db)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already assigned as Class Teacher to another class."
        )

    # Check target section exists and belongs to teacher's school
    target_section = db.query(Section).filter(
        Section.id == section_id,
        Section.school_id == teacher.school_id
    ).first()
    if not target_section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class/Section not found or does not belong to your school"
        )

    # Check if class already has a Class Teacher
    if target_section.class_teacher_id and target_section.class_teacher_id != teacher.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This class already has a Class Teacher."
        )

    target_section.class_teacher_id = teacher.id
    db.commit()
    db.refresh(target_section)
    db.refresh(teacher)

    return serialize_teacher(teacher, db=db)


@router.patch("/me", response_model=dict)
def update_my_teacher_profile(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if str(current_user.role).upper() != "TEACHER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")

    # Teachers can update permitted personal/professional fields
    allowed_fields = {"display_name", "full_name", "email", "mobile", "qualification", "department", "specialization", "address", "profile_photo"}
    sanitized_payload = {k: v for k, v in payload.items() if k in allowed_fields}

    updated = teacher_crud.update_teacher(db, teacher, sanitized_payload)
    return serialize_teacher(updated, db=db)


@router.get("/{teacher_id}", response_model=dict)
def get_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    teacher = teacher_crud.get_teacher(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

    if str(current_user.role).upper() != "SUPER_ADMIN" and teacher.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return serialize_teacher(teacher, db=db)


@router.patch("/{teacher_id}", response_model=dict)
def update_teacher(
    teacher_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    teacher = teacher_crud.get_teacher(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

    role = str(current_user.role).upper()
    is_self = (current_user.id == teacher.user_id)
    is_admin = (role in ["SUPER_ADMIN", "PRINCIPAL"])

    if not is_self and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if is_admin and role != "SUPER_ADMIN" and teacher.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed_fields = {"display_name", "full_name", "email", "mobile", "qualification", "department", "specialization", "address", "profile_photo"}
    if is_admin:
        allowed_fields.update({"employee_id", "joining_date", "is_active", "status"})

    sanitized_payload = {k: v for k, v in payload.items() if k in allowed_fields}
    if "status" in sanitized_payload and teacher.user:
        teacher.user.is_active = sanitized_payload["status"]
    updated = teacher_crud.update_teacher(db, teacher, sanitized_payload)
    return serialize_teacher(updated, db=db)