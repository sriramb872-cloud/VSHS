from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_active_user
from app.crud import student as student_crud, teacher as teacher_crud
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.section import Section
from app.models.academic_year import AcademicYear
from app.models.user import User
from app.core.security import get_password_hash
from app.services.id_generator import generate_student_id

router = APIRouter(prefix="/students", tags=["Students"])


def serialize_student(s: Student) -> dict:
    user = s.user
    age = None
    if s.date_of_birth:
        today = date.today()
        age = today.year - s.date_of_birth.year - ((today.month, today.day) < (s.date_of_birth.month, s.date_of_birth.day))

    grade_id = None
    grade_name = None
    section_id = None
    section_name = None
    academic_year_id = None
    academic_year_name = None
    enrollment_date = None
    roll_no = s.roll_number

    if hasattr(s, "enrollments") and s.enrollments:
        latest_enroll = sorted(s.enrollments, key=lambda e: e.id, reverse=True)[0]
        section_id = latest_enroll.section_id
        if latest_enroll.section:
            section_name = getattr(latest_enroll.section, "name", None) or getattr(latest_enroll.section, "section_name", None)
            grade_id = latest_enroll.section.grade_id
            if latest_enroll.section.grade:
                grade_name = getattr(latest_enroll.section.grade, "name", None) or getattr(latest_enroll.section.grade, "grade_name", None)
        academic_year_id = latest_enroll.academic_year_id
        if latest_enroll.academic_year:
            academic_year_name = getattr(latest_enroll.academic_year, "name", None) or getattr(latest_enroll.academic_year, "year_name", None)
        enrollment_date = latest_enroll.created_at.date() if latest_enroll.created_at else None
        if not roll_no and latest_enroll.roll_number:
            roll_no = latest_enroll.roll_number

    attendance_pct = None
    if hasattr(s, "attendance_records") and s.attendance_records:
        tot = len(s.attendance_records)
        pres = sum(1 for a in s.attendance_records if getattr(a, "status", None) == "PRESENT")
        if tot > 0:
            attendance_pct = round((pres / tot) * 100, 1)

    is_active = True
    if user and hasattr(user, "is_active"):
        is_active = (user.is_active == "ACTIVE" or user.is_active is True)

    raw_status = getattr(s, "student_status", None) or ("ACTIVE" if is_active else "INACTIVE")
    if raw_status in ["PASSED_OUT", "DROPPED"]:
        status_label = "ALUMNI" if raw_status == "PASSED_OUT" else "INACTIVE"
    else:
        status_label = raw_status

    school_name = None
    school_code = None
    if getattr(s, "school", None):
        school_name = getattr(s.school, "name", None) or getattr(s.school, "school_name", None)
        school_code = getattr(s.school, "code", None) or getattr(s.school, "school_code", None)

    admission_num = getattr(s, "admission_number", None) or f"SCH{date.today().year}{s.id:03d}"

    return {
        "id": s.id,
        "student_id": s.id,
        "school_id": s.school_id,
        "school_name": school_name,
        "school_code": school_code,
        "user_id": s.user_id,
        "display_name": user.display_name if user else None,
        "full_name": user.display_name if user else None,
        "mobile": user.mobile if user else None,
        "email": user.email if user else None,
        "profile_photo": user.profile_photo if user else None,
        "role": "STUDENT",
        "admission_number": admission_num,
        "student_id_formatted": admission_num,
        "admission_date": getattr(s, "admission_date", None),
        "roll_number": roll_no,
        "date_of_birth": getattr(s, "date_of_birth", None),
        "age": age,
        "gender": getattr(s, "gender", None),
        "blood_group": getattr(s, "blood_group", None),
        "address": getattr(s, "address", None),
        "father_name": getattr(s, "father_name", None),
        "father_mobile": getattr(s, "father_mobile", None),
        "mother_name": getattr(s, "mother_name", None),
        "mother_mobile": getattr(s, "mother_mobile", None),
        "guardian_mobile": getattr(s, "guardian_mobile", None),
        "grade_id": grade_id,
        "grade_name": grade_name,
        "section_id": section_id,
        "section_name": section_name,
        "academic_year_id": academic_year_id,
        "academic_year_name": academic_year_name,
        "enrollment_date": enrollment_date,
        "attendance_percentage": attendance_pct,
        "status": status_label,
        "student_status": status_label,
        "is_active": is_active,
        "created_at": getattr(s, "created_at", None),
        "updated_at": getattr(s, "updated_at", None),
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_student_profile(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"]))
):
    user_role = str(current_user.role).upper()
    section_id = None

    if user_role == "TEACHER":
        teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
        if not teacher:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")

        assigned_sec = db.query(Section).filter(
            Section.class_teacher_id == teacher.id,
            Section.school_id == teacher.school_id
        ).first()
        if not assigned_sec:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned as a Class Teacher. Please assign yourself to a class first."
            )

        school_id = teacher.school_id
        section_id = assigned_sec.id
    else:
        school_id = payload.get("school_id") or current_user.school_id
        if not school_id and user_role != "SUPER_ADMIN":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")
        section_id = payload.get("section_id")

    # Generate or sanitize Student ID (admission number)
    admission_number = payload.get("admission_number") or payload.get("student_id_formatted")
    if not admission_number or str(admission_number).strip() == "":
        admission_number = generate_student_id(db, school_id)
    else:
        admission_number = str(admission_number).strip()

    # Check for existing student with same admission number in school
    existing = db.query(Student).filter(Student.school_id == school_id, Student.admission_number == admission_number).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Student ID / Admission number '{admission_number}' already exists.")

    # Prepare user account
    full_name = payload.get("full_name") or payload.get("display_name") or "New Student"
    mobile = payload.get("mobile") or payload.get("guardian_mobile") or payload.get("father_mobile") or payload.get("mother_mobile")
    if not mobile or str(mobile).strip() == "":
        mobile = f"STU{admission_number}"

    # Check if mobile exists in users table
    existing_user = db.query(User).filter(User.mobile == mobile).first()
    if existing_user:
        # Generate unique mobile identifier based on admission number
        mobile = f"STU{admission_number}"

    initial_password = payload.get("password") or "Student@123"
    hashed_pwd = get_password_hash(initial_password)

    new_user = User(
        school_id=school_id,
        display_name=full_name,
        mobile=mobile,
        email=payload.get("email"),
        profile_photo=payload.get("profile_photo"),
        password_hash=hashed_pwd,
        role="STUDENT",
        is_active="ACTIVE",
    )
    db.add(new_user)
    db.flush()

    dob = payload.get("date_of_birth")
    if isinstance(dob, str) and dob.strip():
        try:
            dob = date.fromisoformat(dob[:10])
        except Exception:
            dob = None

    adm_date = payload.get("admission_date")
    if isinstance(adm_date, str) and adm_date.strip():
        try:
            adm_date = date.fromisoformat(adm_date[:10])
        except Exception:
            adm_date = None
    elif not adm_date:
        adm_date = date.today()

    new_student = Student(
        user_id=new_user.id,
        school_id=school_id,
        admission_number=admission_number,
        roll_number=payload.get("roll_number"),
        admission_date=adm_date,
        gender=payload.get("gender") or "OTHER",
        date_of_birth=dob,
        blood_group=payload.get("blood_group"),
        father_name=payload.get("father_name"),
        father_mobile=payload.get("father_mobile"),
        mother_name=payload.get("mother_name"),
        mother_mobile=payload.get("mother_mobile"),
        guardian_mobile=payload.get("guardian_mobile") or mobile,
        address=payload.get("address"),
    )
    db.add(new_student)
    db.flush()

    # Auto-enrollment for the resolved section
    academic_year_id = payload.get("academic_year_id")
    if section_id:
        if not academic_year_id:
            curr_ay = db.query(AcademicYear).filter(AcademicYear.school_id == school_id, AcademicYear.is_active == True).first()
            if curr_ay:
                academic_year_id = curr_ay.id
            else:
                first_ay = db.query(AcademicYear).filter(AcademicYear.school_id == school_id).first()
                if first_ay:
                    academic_year_id = first_ay.id

        if academic_year_id:
            enrollment = StudentEnrollment(
                student_id=new_student.id,
                section_id=section_id,
                academic_year_id=academic_year_id,
                roll_number=payload.get("roll_number"),
            )
            db.add(enrollment)

    db.commit()
    db.refresh(new_student)
    return serialize_student(new_student)


@router.get("", response_model=List[dict])
def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    grade_id: Optional[int] = Query(None),
    section_id: Optional[int] = Query(None),
    academic_year_id: Optional[int] = Query(None),
    school_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user_role = str(current_user.role).upper()

    if user_role == "TEACHER":
        teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
        if not teacher:
            return []

        assigned_sec = db.query(Section).filter(
            Section.class_teacher_id == teacher.id,
            Section.school_id == teacher.school_id
        ).first()
        if not assigned_sec:
            return []

        query = (
            db.query(Student)
            .filter(Student.school_id == teacher.school_id)
            .join(Student.enrollments)
            .filter(StudentEnrollment.section_id == assigned_sec.id)
        )
        students = query.offset(skip).limit(limit).all()
        return [serialize_student(s) for s in students]

    target_school_id = current_user.school_id
    if user_role == "SUPER_ADMIN" and school_id:
        target_school_id = school_id

    if not target_school_id and user_role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")

    query = db.query(Student)
    if target_school_id:
        query = query.filter(Student.school_id == target_school_id)

    if section_id or grade_id or academic_year_id:
        query = query.join(Student.enrollments)
        if section_id:
            query = query.filter(StudentEnrollment.section_id == section_id)
        if academic_year_id:
            query = query.filter(StudentEnrollment.academic_year_id == academic_year_id)
        if grade_id:
            query = query.join(StudentEnrollment.section).filter(Section.grade_id == grade_id)

    students = query.offset(skip).limit(limit).all()
    return [serialize_student(s) for s in students]


@router.get("/me", response_model=dict)
def get_my_student_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if str(current_user.role).upper() != "STUDENT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    student = student_crud.get_student_by_user_id(db, current_user.id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    return serialize_student(student)


@router.patch("/me", response_model=dict)
def update_my_student_profile(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if str(current_user.role).upper() != "STUDENT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    student = student_crud.get_student_by_user_id(db, current_user.id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    # Strict restriction: Students can only update permitted personal/contact fields
    allowed_student_fields = {
        "date_of_birth", "gender", "blood_group",
        "father_name", "father_mobile", "mother_name", "mother_mobile",
        "guardian_mobile", "address", "display_name", "full_name", "email", "profile_photo"
    }
    sanitized_payload = {k: v for k, v in payload.items() if k in allowed_student_fields}

    updated = student_crud.update_student(db, student, sanitized_payload)
    return serialize_student(updated)


@router.get("/{student_id}", response_model=dict)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    student = student_crud.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    role = str(current_user.role).upper()
    if role != "SUPER_ADMIN" and student.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if role == "TEACHER":
        teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
        if not teacher:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        assigned_sec = db.query(Section).filter(
            Section.class_teacher_id == teacher.id,
            Section.school_id == teacher.school_id
        ).first()
        if not assigned_sec:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Not assigned as Class Teacher")
        is_enrolled = any(e.section_id == assigned_sec.id for e in (student.enrollments or []))
        if not is_enrolled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Student does not belong to your class")

    return serialize_student(student)


@router.patch("/{student_id}", response_model=dict)
def update_student(
    student_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    student = student_crud.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    role = str(current_user.role).upper()
    is_self = (current_user.id == student.user_id)
    is_admin = (role in ["SUPER_ADMIN", "PRINCIPAL"])
    is_teacher = (role == "TEACHER")

    if not is_self and not is_admin and not is_teacher:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if role != "SUPER_ADMIN" and student.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if is_teacher:
        teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
        if not teacher:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        assigned_sec = db.query(Section).filter(
            Section.class_teacher_id == teacher.id,
            Section.school_id == teacher.school_id
        ).first()
        if not assigned_sec:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Not assigned as Class Teacher")
        is_enrolled = any(e.section_id == assigned_sec.id for e in (student.enrollments or []))
        if not is_enrolled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Student does not belong to your class")
        allowed_fields = {
            "roll_number", "admission_date", "date_of_birth",
            "gender", "blood_group", "father_name", "father_mobile",
            "mother_name", "mother_mobile", "guardian_mobile", "address",
            "student_status", "display_name", "full_name", "email", "mobile", "profile_photo"
        }
    elif is_self and not is_admin:
        # Strict restriction for self update by student
        allowed_fields = {
            "date_of_birth", "gender", "blood_group",
            "father_name", "father_mobile", "mother_name", "mother_mobile",
            "guardian_mobile", "address", "display_name", "full_name", "email", "profile_photo"
        }
    else:
        # Admin / Principal update
        allowed_fields = {
            "admission_number", "roll_number", "admission_date", "date_of_birth",
            "gender", "blood_group", "father_name", "father_mobile",
            "mother_name", "mother_mobile", "guardian_mobile", "address",
            "student_status", "display_name", "full_name", "email", "mobile", "profile_photo"
        }

    sanitized_payload = {k: v for k, v in payload.items() if k in allowed_fields}
    updated = student_crud.update_student(db, student, sanitized_payload)
    return serialize_student(updated)
