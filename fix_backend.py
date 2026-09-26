"""Apply all backend fixes for the Scholaris application."""
import re

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def replace_once(content, old, new, label):
    if old in content:
        print(f"  OK: {label}")
        return content.replace(old, new, 1)
    else:
        print(f"  MISS: {label}")
        return content

# ============================================================
# FIX 01 — teachers.py: Principal school isolation on CREATE
# ============================================================
path = 'backend-python/app/routers/v1/teachers.py'
c = read_file(path)

old = (
    '    school_id = payload.get("school_id") or current_user.school_id\r\n'
    '    if not school_id and str(current_user.role).upper() != "SUPER_ADMIN":\r\n'
    '        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")\r\n'
)
new = (
    '    _role = str(current_user.role).upper()\r\n'
    '    if _role == "PRINCIPAL":\r\n'
    '        school_id = current_user.school_id\r\n'
    '        if not school_id:\r\n'
    '            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")\r\n'
    '        # Strip client-supplied school_id to prevent cross-school creation\r\n'
    '        payload = {k: v for k, v in payload.items() if k != "school_id"}\r\n'
    '    elif _role == "SUPER_ADMIN":\r\n'
    '        school_id = payload.get("school_id") or current_user.school_id\r\n'
    '        if not school_id:\r\n'
    '            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="school_id is required")\r\n'
    '    else:\r\n'
    '        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")\r\n'
)
c = replace_once(c, old, new, 'FIX01 teacher create school isolation')

# FIX 06 — teachers.py: add audit log + status lifecycle to update_teacher
old2 = (
    '    sanitized_payload = {k: v for k, v in payload.items() if k in allowed_fields}\r\n'
    '    if "status" in sanitized_payload and teacher.user:\r\n'
    '        teacher.user.is_active = sanitized_payload["status"]\r\n'
    '    updated = teacher_crud.update_teacher(db, teacher, sanitized_payload)\r\n'
    '    return serialize_teacher(updated, db=db)\r\n'
)
new2 = (
    '    sanitized_payload = {k: v for k, v in payload.items() if k in allowed_fields}\r\n'
    '    if "status" in sanitized_payload and teacher.user:\r\n'
    '        teacher.user.is_active = sanitized_payload["status"]\r\n'
    '        db.flush()\r\n'
    '    elif "is_active" in sanitized_payload and teacher.user:\r\n'
    '        teacher.user.is_active = sanitized_payload["is_active"]\r\n'
    '        db.flush()\r\n'
    '    updated = teacher_crud.update_teacher(db, teacher, sanitized_payload)\r\n'
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=teacher.school_id,\r\n'
    '        action="UPDATE", resource_type="Teacher", resource_id=teacher.id,\r\n'
    '        details={k: str(v) for k, v in sanitized_payload.items()},\r\n'
    '    )\r\n'
    '    return serialize_teacher(updated, db=db)\r\n'
)
c = replace_once(c, old2, new2, 'FIX06 teacher update audit + is_active')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 02 — students.py: Principal school isolation on CREATE
# ============================================================
path = 'backend-python/app/routers/v1/students.py'
c = read_file(path)

old = (
    '    else:\n'
    '        school_id = payload.get("school_id") or current_user.school_id\n'
    '        if not school_id and user_role != "SUPER_ADMIN":\r\n'
    '            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")\r\n'
    '        section_id = payload.get("section_id")\n'
)
new = (
    '    elif user_role == "PRINCIPAL":\r\n'
    '        school_id = current_user.school_id\r\n'
    '        if not school_id:\r\n'
    '            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")\r\n'
    '        # Strip client-supplied school_id to prevent cross-school creation\r\n'
    '        payload = {k: v for k, v in payload.items() if k != "school_id"}\r\n'
    '        section_id = payload.get("section_id")\r\n'
    '    else:  # SUPER_ADMIN\r\n'
    '        school_id = payload.get("school_id") or current_user.school_id\r\n'
    '        if not school_id:\r\n'
    '            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="school_id is required")\r\n'
    '        section_id = payload.get("section_id")\r\n'
)
c = replace_once(c, old, new, 'FIX02 student create school isolation')

# Also fix student update: add audit log
old3 = (
    '    sanitized_payload = {k: v for k, v in payload.items() if k in allowed_fields}\r\n'
    '    updated = student_crud.update_student(db, student, sanitized_payload)\r\n'
    '    return serialize_student(updated)\r\n'
)
new3 = (
    '    sanitized_payload = {k: v for k, v in payload.items() if k in allowed_fields}\r\n'
    '    if "student_status" in sanitized_payload and student.user:\r\n'
    '        student.user.is_active = sanitized_payload["student_status"]\r\n'
    '        db.flush()\r\n'
    '    updated = student_crud.update_student(db, student, sanitized_payload)\r\n'
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=student.school_id,\r\n'
    '        action="UPDATE", resource_type="Student", resource_id=student.id,\r\n'
    '        details={k: str(v) for k, v in sanitized_payload.items()},\r\n'
    '    )\r\n'
    '    return serialize_student(updated)\r\n'
)
c = replace_once(c, old3, new3, 'FIX07 student update audit + status sync')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 03 — users.py: Super Admin deactivate own account guard
# ============================================================
path = 'backend-python/app/routers/v1/users.py'
c = read_file(path)

old = (
    '    allowed_fields = {"display_name", "full_name", "email", "mobile"}\r\n'
    '    if is_admin:\r\n'
    '        allowed_fields.add("is_active")\r\n'
    '\r\n'
    '    for key, value in payload.items():\r\n'
    '        if key in allowed_fields and value is not None:\r\n'
    '            if key == "full_name":\r\n'
    '                user.display_name = str(value).strip()\r\n'
    '            else:\r\n'
    '                setattr(user, key, value)\r\n'
    '\r\n'
    '    db.commit()\r\n'
    '    db.refresh(user)\r\n'
    '\r\n'
    '    return serialize_user(user)\r\n'
)
new = (
    '    allowed_fields = {"display_name", "full_name", "email", "mobile"}\r\n'
    '    if is_admin:\r\n'
    '        allowed_fields.add("is_active")\r\n'
    '\r\n'
    '    # Prevent Super Admin from accidentally deactivating their own account\r\n'
    '    if role == "SUPER_ADMIN" and is_self and "is_active" in payload:\r\n'
    '        new_status = payload["is_active"]\r\n'
    '        if isinstance(new_status, str) and new_status.upper() not in ("ACTIVE",):\r\n'
    '            raise HTTPException(\r\n'
    '                status_code=status.HTTP_400_BAD_REQUEST,\r\n'
    '                detail="Super Admin cannot deactivate their own account.",\r\n'
    '            )\r\n'
    '\r\n'
    '    for key, value in payload.items():\r\n'
    '        if key in allowed_fields and value is not None:\r\n'
    '            if key == "full_name":\r\n'
    '                user.display_name = str(value).strip()\r\n'
    '            else:\r\n'
    '                setattr(user, key, value)\r\n'
    '\r\n'
    '    from app.core.audit import write_audit_log\r\n'
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=user.school_id,\r\n'
    '        action="UPDATE", resource_type="User", resource_id=user.id,\r\n'
    '        details={k: str(v) for k, v in payload.items() if k in allowed_fields},\r\n'
    '    )\r\n'
    '    db.commit()\r\n'
    '    db.refresh(user)\r\n'
    '\r\n'
    '    return serialize_user(user)\r\n'
)
c = replace_once(c, old, new, 'FIX03 user update guard + audit')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 04 — principals.py: audit log on update
# ============================================================
path = 'backend-python/app/routers/v1/principals.py'
c = read_file(path)

old = (
    '    db.commit()\r\n'
    '    db.refresh(p)\r\n'
    '    return serialize_principal(p, db=db)\r\n'
)
new = (
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=p.school_id,\r\n'
    '        action="UPDATE", resource_type="Principal", resource_id=p.id,\r\n'
    '        details={k: str(v) for k, v in payload.items() if k in ("display_name","full_name","email","mobile","is_active","status","school_id","employee_id","joining_date")},\r\n'
    '    )\r\n'
    '    db.commit()\r\n'
    '    db.refresh(p)\r\n'
    '    return serialize_principal(p, db=db)\r\n'
)
c = replace_once(c, old, new, 'FIX04 principal update audit')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 05 — schools.py: activate/deactivate endpoint
# ============================================================
path = 'backend-python/app/routers/v1/schools.py'
c = read_file(path)

# Add activate/deactivate endpoints after update_school
extra_endpoints = (
    '\r\n'
    '\r\n'
    '@router.patch("/{school_id}/status", response_model=dict)\r\n'
    'def update_school_status(\r\n'
    '    school_id: int,\r\n'
    '    payload: dict,\r\n'
    '    db: Session = Depends(get_db),\r\n'
    '    current_user: User = Depends(require_roles(["SUPER_ADMIN"]))\r\n'
    '):\r\n'
    '    """Activate or deactivate a school (SUPER_ADMIN only)."""\r\n'
    '    school = school_crud.get_school(db, school_id)\r\n'
    '    if not school:\r\n'
    '        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")\r\n'
    '\r\n'
    '    new_status = payload.get("is_active")\r\n'
    '    if new_status is None:\r\n'
    '        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="is_active is required")\r\n'
    '\r\n'
    '    old_status = getattr(school, "is_active", None)\r\n'
    '    school.is_active = bool(new_status)\r\n'
    '    db.commit()\r\n'
    '    db.refresh(school)\r\n'
    '\r\n'
    '    action = "ACTIVATE" if new_status else "DEACTIVATE"\r\n'
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=school.id,\r\n'
    '        action=action, resource_type="School", resource_id=school.id,\r\n'
    '        details={"is_active": new_status, "previous": old_status},\r\n'
    '    )\r\n'
    '    return {\r\n'
    '        "id": school.id,\r\n'
    '        "name": getattr(school, "name", ""),\r\n'
    '        "code": getattr(school, "code", ""),\r\n'
    '        "is_active": getattr(school, "is_active", True)\r\n'
    '    }\r\n'
)
if '@router.patch("/{school_id}/status"' not in c:
    c = c + extra_endpoints
    print('  OK: FIX05 school status endpoint added')
else:
    print('  SKIP: FIX05 already exists')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 08 — grades.py: add delete endpoint with audit
# ============================================================
path = 'backend-python/app/routers/v1/grades.py'
c = read_file(path)

if 'from app.core.audit import write_audit_log' not in c:
    c = c.replace(
        'from app.models.user import User\r\n',
        'from app.models.user import User\r\nfrom app.core.audit import write_audit_log\r\n'
    )

# Add audit to update + archive endpoint
old_update = (
    '    updated = grade_crud.update_grade(db, grade, payload)\r\n'
    '    return {\r\n'
    '        "id": updated.id,\r\n'
    '        "school_id": updated.school_id,\r\n'
    '        "name": getattr(updated, "name", "")\r\n'
    '    }\r\n'
)
new_update = (
    '    updated = grade_crud.update_grade(db, grade, payload)\r\n'
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=grade.school_id,\r\n'
    '        action="UPDATE", resource_type="Grade", resource_id=grade.id,\r\n'
    '        details={k: str(v) for k, v in payload.items()},\r\n'
    '    )\r\n'
    '    return {\r\n'
    '        "id": updated.id,\r\n'
    '        "school_id": updated.school_id,\r\n'
    '        "name": getattr(updated, "name", ""),\r\n'
    '        "display_order": getattr(updated, "display_order", 0),\r\n'
    '        "is_active": getattr(updated, "is_active", True),\r\n'
    '    }\r\n'
)
c = replace_once(c, old_update, new_update, 'FIX08 grade update audit')

# Add delete endpoint
if '@router.delete("/{grade_id}"' not in c:
    c += (
        '\r\n\r\n'
        '@router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)\r\n'
        'def delete_grade(\r\n'
        '    grade_id: int,\r\n'
        '    db: Session = Depends(get_db),\r\n'
        '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))\r\n'
        '):\r\n'
        '    grade = grade_crud.get_grade(db, grade_id)\r\n'
        '    if not grade:\r\n'
        '        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")\r\n'
        '\r\n'
        '    if str(current_user.role).upper() != "SUPER_ADMIN" and grade.school_id != current_user.school_id:\r\n'
        '        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")\r\n'
        '\r\n'
        '    try:\r\n'
        '        grade_crud.delete_grade(db, grade)\r\n'
        '    except Exception as e:\r\n'
        '        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot delete grade: {e}")\r\n'
        '\r\n'
        '    write_audit_log(\r\n'
        '        db, user_id=current_user.id, school_id=grade.school_id,\r\n'
        '        action="DELETE", resource_type="Grade", resource_id=grade_id,\r\n'
        '        details={"name": getattr(grade, "name", "")},\r\n'
        '    )\r\n'
        '    return None\r\n'
    )
    print('  OK: FIX08 grade delete endpoint added')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 09 — sections.py: add delete endpoint + class_teacher_id
# ============================================================
path = 'backend-python/app/routers/v1/sections.py'
c = read_file(path)

if 'from app.core.audit import write_audit_log' not in c:
    c = c.replace(
        'from app.models.user import User\r\n',
        'from app.models.user import User\r\nfrom app.core.audit import write_audit_log\r\n'
    )

# Improve update to return class_teacher_id and add audit
old_update = (
    '    updated = section_crud.update_section(db, section, payload)\r\n'
    '    return {\r\n'
    '        "id": updated.id,\r\n'
    '        "school_id": updated.school_id,\r\n'
    '        "grade_id": updated.grade_id,\r\n'
    '        "name": getattr(updated, "name", "")\r\n'
    '    }\r\n'
)
new_update = (
    '    # Validate grade belongs to same school if being changed\r\n'
    '    new_grade_id = payload.get("grade_id")\r\n'
    '    if new_grade_id and str(current_user.role).upper() != "SUPER_ADMIN":\r\n'
    '        grade = grade_crud.get_grade(db, new_grade_id)\r\n'
    '        if not grade or grade.school_id != current_user.school_id:\r\n'
    '            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade does not belong to your school")\r\n'
    '    updated = section_crud.update_section(db, section, payload)\r\n'
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=section.school_id,\r\n'
    '        action="UPDATE", resource_type="Section", resource_id=section.id,\r\n'
    '        details={k: str(v) for k, v in payload.items()},\r\n'
    '    )\r\n'
    '    return {\r\n'
    '        "id": updated.id,\r\n'
    '        "school_id": updated.school_id,\r\n'
    '        "grade_id": updated.grade_id,\r\n'
    '        "name": getattr(updated, "name", ""),\r\n'
    '        "class_teacher_id": getattr(updated, "class_teacher_id", None),\r\n'
    '    }\r\n'
)
c = replace_once(c, old_update, new_update, 'FIX09 section update + grade validation + audit')

# Add delete endpoint
if '@router.delete("/{section_id}"' not in c:
    c += (
        '\r\n\r\n'
        '@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)\r\n'
        'def delete_section(\r\n'
        '    section_id: int,\r\n'
        '    db: Session = Depends(get_db),\r\n'
        '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))\r\n'
        '):\r\n'
        '    section = section_crud.get_section(db, section_id)\r\n'
        '    if not section:\r\n'
        '        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")\r\n'
        '\r\n'
        '    if str(current_user.role).upper() != "SUPER_ADMIN" and section.school_id != current_user.school_id:\r\n'
        '        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")\r\n'
        '\r\n'
        '    try:\r\n'
        '        section_crud.delete_section(db, section)\r\n'
        '    except Exception as e:\r\n'
        '        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot delete section: {e}")\r\n'
        '\r\n'
        '    write_audit_log(\r\n'
        '        db, user_id=current_user.id, school_id=section.school_id,\r\n'
        '        action="DELETE", resource_type="Section", resource_id=section_id,\r\n'
        '        details={"name": getattr(section, "name", "")},\r\n'
        '    )\r\n'
        '    return None\r\n'
    )
    print('  OK: FIX09 section delete endpoint added')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 10 — subjects.py: add delete endpoint + audit on update
# ============================================================
path = 'backend-python/app/routers/v1/subjects.py'
c = read_file(path)

if 'from app.core.audit import write_audit_log' not in c:
    c = c.replace(
        'from app.models.user import User\r\n',
        'from app.models.user import User\r\nfrom app.core.audit import write_audit_log\r\n'
    )

old_update = (
    '    updated = subject_crud.update_subject(db, subject, payload)\r\n'
    '    return {\r\n'
    '        "id": updated.id,\r\n'
    '        "school_id": updated.school_id,\r\n'
    '        "name": getattr(updated, "name", ""),\r\n'
    '        "code": getattr(updated, "code", "")\r\n'
    '    }\r\n'
)
new_update = (
    '    updated = subject_crud.update_subject(db, subject, payload)\r\n'
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=subject.school_id,\r\n'
    '        action="UPDATE", resource_type="Subject", resource_id=subject.id,\r\n'
    '        details={k: str(v) for k, v in payload.items()},\r\n'
    '    )\r\n'
    '    return {\r\n'
    '        "id": updated.id,\r\n'
    '        "school_id": updated.school_id,\r\n'
    '        "name": getattr(updated, "name", ""),\r\n'
    '        "code": getattr(updated, "code", "")\r\n'
    '    }\r\n'
)
c = replace_once(c, old_update, new_update, 'FIX10 subject update audit')

if '@router.delete("/{subject_id}"' not in c:
    c += (
        '\r\n\r\n'
        '@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)\r\n'
        'def delete_subject(\r\n'
        '    subject_id: int,\r\n'
        '    db: Session = Depends(get_db),\r\n'
        '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))\r\n'
        '):\r\n'
        '    subject = subject_crud.get_subject(db, subject_id)\r\n'
        '    if not subject:\r\n'
        '        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")\r\n'
        '\r\n'
        '    if str(current_user.role).upper() != "SUPER_ADMIN" and subject.school_id != current_user.school_id:\r\n'
        '        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")\r\n'
        '\r\n'
        '    try:\r\n'
        '        subject_crud.delete_subject(db, subject)\r\n'
        '    except Exception as e:\r\n'
        '        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot delete subject: {e}")\r\n'
        '\r\n'
        '    write_audit_log(\r\n'
        '        db, user_id=current_user.id, school_id=subject.school_id,\r\n'
        '        action="DELETE", resource_type="Subject", resource_id=subject_id,\r\n'
        '        details={"name": getattr(subject, "name", "")},\r\n'
        '    )\r\n'
        '    return None\r\n'
    )
    print('  OK: FIX10 subject delete endpoint added')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 11 — academic_years.py: add activate + audit
# ============================================================
path = 'backend-python/app/routers/v1/academic_years.py'
c = read_file(path)

if 'from app.core.audit import write_audit_log' not in c:
    c = c.replace(
        'from app.schemas.academic_year import AcademicYearCreate\r\n',
        'from app.schemas.academic_year import AcademicYearCreate\r\nfrom app.core.audit import write_audit_log\r\n'
    )

old_update = (
    '    updated = ay_crud.update_academic_year(db, item, payload)\r\n'
    '    return {\r\n'
    '        "id": updated.id,\r\n'
    '        "school_id": updated.school_id,\r\n'
    '        "name": getattr(updated, "name", ""),\r\n'
    '        "is_active": getattr(updated, "is_active", False)\r\n'
    '    }\r\n'
)
new_update = (
    '    # Enforce: only one active academic year per school\r\n'
    '    if payload.get("is_active") is True:\r\n'
    '        from app.models.academic_year import AcademicYear\r\n'
    '        db.query(AcademicYear).filter(\r\n'
    '            AcademicYear.school_id == item.school_id,\r\n'
    '            AcademicYear.id != item.id,\r\n'
    '        ).update({"is_active": False})\r\n'
    '        db.flush()\r\n'
    '    updated = ay_crud.update_academic_year(db, item, payload)\r\n'
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=item.school_id,\r\n'
    '        action="UPDATE", resource_type="AcademicYear", resource_id=item.id,\r\n'
    '        details={k: str(v) for k, v in payload.items()},\r\n'
    '    )\r\n'
    '    return {\r\n'
    '        "id": updated.id,\r\n'
    '        "school_id": updated.school_id,\r\n'
    '        "name": getattr(updated, "name", ""),\r\n'
    '        "is_active": getattr(updated, "is_active", False),\r\n'
    '        "start_date": getattr(updated, "start_date", None),\r\n'
    '        "end_date": getattr(updated, "end_date", None),\r\n'
    '    }\r\n'
)
c = replace_once(c, old_update, new_update, 'FIX11 academic_year update + single-active enforce + audit')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 12 — student_enrollments.py: add PATCH update endpoint
# ============================================================
path = 'backend-python/app/routers/v1/student_enrollments.py'
c = read_file(path)

if 'from app.core.audit import write_audit_log' not in c:
    c = c.replace(
        'from app.models.user import User\n',
        'from app.models.user import User\nfrom app.core.audit import write_audit_log\n'
    )

# Add audit to delete
old_del = (
    '    se_crud.delete_student_enrollment(db, item)\r\n'
    '    return None\n'
)
new_del = (
    '    se_crud.delete_student_enrollment(db, item)\r\n'
    '    write_audit_log(\r\n'
    '        db, user_id=current_user.id, school_id=(item.student.school_id if item.student else None),\r\n'
    '        action="DELETE", resource_type="StudentEnrollment", resource_id=enrollment_id,\r\n'
    '        details={"student_id": item.student_id, "section_id": item.section_id},\r\n'
    '    )\r\n'
    '    return None\n'
)
c = replace_once(c, old_del, new_del, 'FIX12 enrollment delete audit')

# Add PATCH update endpoint
if '@router.patch("/{enrollment_id}"' not in c:
    c += (
        '\r\n\r\n'
        '@router.patch("/{enrollment_id}", response_model=dict)\r\n'
        'def update_enrollment(\r\n'
        '    enrollment_id: int,\r\n'
        '    payload: dict,\r\n'
        '    db: Session = Depends(get_db),\r\n'
        '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))\r\n'
        '):\r\n'
        '    """Update/transfer a student enrollment (grade/section/academic year)."""\r\n'
        '    item = se_crud.get_student_enrollment(db, enrollment_id)\r\n'
        '    if not item:\r\n'
        '        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")\r\n'
        '\r\n'
        '    user_role = str(current_user.role).upper()\r\n'
        '    if user_role != "SUPER_ADMIN":\r\n'
        '        if item.student and item.student.school_id != current_user.school_id:\r\n'
        '            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")\r\n'
        '\r\n'
        '    # Validate new section if provided\r\n'
        '    new_section_id = payload.get("section_id")\r\n'
        '    if new_section_id:\r\n'
        '        section = db.query(Section).filter(Section.id == int(new_section_id)).first()\r\n'
        '        if not section:\r\n'
        '            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")\r\n'
        '        if user_role != "SUPER_ADMIN" and section.school_id != current_user.school_id:\r\n'
        '            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Section does not belong to your school")\r\n'
        '\r\n'
        '    # Validate new academic_year if provided\r\n'
        '    new_ay_id = payload.get("academic_year_id")\r\n'
        '    if new_ay_id:\r\n'
        '        ay = db.query(AcademicYear).filter(AcademicYear.id == int(new_ay_id)).first()\r\n'
        '        if not ay:\r\n'
        '            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")\r\n'
        '        if user_role != "SUPER_ADMIN" and ay.school_id != current_user.school_id:\r\n'
        '            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Academic year does not belong to your school")\r\n'
        '\r\n'
        '    allowed = {"section_id", "academic_year_id", "roll_number"}\r\n'
        '    for k, v in payload.items():\r\n'
        '        if k in allowed and v is not None:\r\n'
        '            setattr(item, k, v)\r\n'
        '    db.commit()\r\n'
        '    db.refresh(item)\r\n'
        '\r\n'
        '    write_audit_log(\r\n'
        '        db, user_id=current_user.id, school_id=(item.student.school_id if item.student else None),\r\n'
        '        action="UPDATE", resource_type="StudentEnrollment", resource_id=enrollment_id,\r\n'
        '        details={k: str(v) for k, v in payload.items() if k in allowed},\r\n'
        '    )\r\n'
        '    return serialize_enrollment(item)\r\n'
    )
    print('  OK: FIX12 enrollment PATCH endpoint added')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 13 — teacher_subjects.py: enforce school ownership in PATCH
# ============================================================
path = 'backend-python/app/routers/v1/teacher_subjects.py'
c = read_file(path)

old_patch = (
    '@router.patch("/{assignment_id}", response_model=TeacherSubjectResponse)\r\n'
    'def update_teacher_subject_assignment(\r\n'
    '    assignment_id: int,\r\n'
    '    payload: TeacherSubjectUpdate,\r\n'
    '    db: Session = Depends(get_db),\r\n'
    '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),\r\n'
    '):\r\n'
    '    service = TeacherSubjectService(db)\r\n'
    '    return service.update_assignment(assignment_id, payload)\r\n'
)
new_patch = (
    '@router.patch("/{assignment_id}", response_model=TeacherSubjectResponse)\r\n'
    'def update_teacher_subject_assignment(\r\n'
    '    assignment_id: int,\r\n'
    '    payload: TeacherSubjectUpdate,\r\n'
    '    db: Session = Depends(get_db),\r\n'
    '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),\r\n'
    '):\r\n'
    '    service = TeacherSubjectService(db)\r\n'
    '    # Principal: lock school_id to own school\r\n'
    '    if str(current_user.role).upper() == "PRINCIPAL":\r\n'
    '        payload = TeacherSubjectUpdate(\r\n'
    '            **{**payload.model_dump(exclude_none=True), "school_id": current_user.school_id}\r\n'
    '        )\r\n'
    '    return service.update_assignment(assignment_id, payload)\r\n'
)
c = replace_once(c, old_patch, new_patch, 'FIX13 teacher_subject PATCH school lock')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 14 — teacher_assignments.py: disable legacy raw mutations
# ============================================================
path = 'backend-python/app/routers/v1/teacher_assignments.py'
c = read_file(path)

old_post = (
    '@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)\r\n'
    'def create_assignment(\r\n'
    '    payload: dict,\r\n'
    '    db: Session = Depends(get_db),\r\n'
    '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))\r\n'
    '):\r\n'
    '    data = dict(payload)\r\n'
    '    if "start_time" in data and data["start_time"] is not None:\r\n'
    '        data["start_time"] = parse_time(data["start_time"])\r\n'
    '    if "end_time" in data and data["end_time"] is not None:\r\n'
    '        data["end_time"] = parse_time(data["end_time"])\r\n'
    '    item = Timetable(**data)\r\n'
    '    db.add(item)\r\n'
    '    db.commit()\r\n'
    '    db.refresh(item)\r\n'
    '    return {\r\n'
    '        "id": item.id,\r\n'
    '        "teacher_id": item.teacher_id,\r\n'
    '        "section_id": getattr(item, "section_id", None),\r\n'
    '        "subject_id": getattr(item, "subject_id", None)\r\n'
    '    }\r\n'
)
new_post = (
    '@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)\r\n'
    'def create_assignment(\r\n'
    '    payload: dict,\r\n'
    '    db: Session = Depends(get_db),\r\n'
    '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))\r\n'
    '):\r\n'
    '    # Legacy endpoint: use TimetableService to keep validation consistent\r\n'
    '    from app.services.timetable import TimetableService\r\n'
    '    from app.schemas.timetable import TimetableCreate\r\n'
    '    try:\r\n'
    '        obj_in = TimetableCreate(**payload)\r\n'
    '    except Exception as e:\r\n'
    '        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))\r\n'
    '    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else payload.get("school_id")\r\n'
    '    item = TimetableService.create(db, obj_in=obj_in, school_id=school_id, created_by_id=current_user.id)\r\n'
    '    return {\r\n'
    '        "id": item.id,\r\n'
    '        "teacher_id": item.teacher_id,\r\n'
    '        "section_id": getattr(item, "section_id", None),\r\n'
    '        "subject_id": getattr(item, "subject_id", None)\r\n'
    '    }\r\n'
)
c = replace_once(c, old_post, new_post, 'FIX14 teacher_assignments use TimetableService')

old_del = (
    '@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)\r\n'
    'def remove_assignment(\r\n'
    '    assignment_id: int,\r\n'
    '    db: Session = Depends(get_db),\r\n'
    '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))\r\n'
    '):\r\n'
    '    item = db.query(Timetable).filter(Timetable.id == assignment_id).first()\r\n'
    '    if not item:\r\n'
    '        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")\r\n'
    '    db.delete(item)\r\n'
    '    db.commit()\r\n'
    '    return None\r\n'
)
new_del = (
    '@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)\r\n'
    'def remove_assignment(\r\n'
    '    assignment_id: int,\r\n'
    '    db: Session = Depends(get_db),\r\n'
    '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"]))\r\n'
    '):\r\n'
    '    from app.services.timetable import TimetableService\r\n'
    '    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None\r\n'
    '    success = TimetableService.delete(db, timetable_id=assignment_id, school_id=school_id)\r\n'
    '    if not success:\r\n'
    '        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found or access denied")\r\n'
    '    return None\r\n'
)
c = replace_once(c, old_del, new_del, 'FIX14 teacher_assignments delete via TimetableService')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 16 — attendance.py: add PATCH correction endpoint
# ============================================================
path = 'backend-python/app/routers/v1/attendance.py'
c = read_file(path)

if 'from app.core.audit import write_audit_log' not in c:
    c = c.replace(
        'from app.schemas.attendance import AttendanceCreate\n',
        'from app.schemas.attendance import AttendanceCreate\nfrom app.core.audit import write_audit_log\n'
    )

if '@router.patch("/{attendance_id}"' not in c:
    c += (
        '\n\n'
        '@router.patch("/{attendance_id}", response_model=dict)\n'
        'def correct_attendance(\n'
        '    attendance_id: int,\n'
        '    payload: dict,\n'
        '    db: Session = Depends(get_db),\n'
        '    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"]))\n'
        '):\n'
        '    """Correct/update an attendance record. Prefer correction over deletion."""\n'
        '    item = att_crud.get_attendance(db, attendance_id)\n'
        '    if not item:\n'
        '        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")\n'
        '\n'
        '    role = str(current_user.role).upper()\n'
        '    if role != "SUPER_ADMIN" and getattr(item, "school_id", None) and getattr(item, "school_id") != current_user.school_id:\n'
        '        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")\n'
        '\n'
        '    if role == "TEACHER":\n'
        '        _assert_teacher_owns_section(db, current_user, item.section_id)\n'
        '\n'
        '    old_status = getattr(item, "status", None)\n'
        '    allowed = {"status", "remarks"}\n'
        '    for k, v in payload.items():\n'
        '        if k in allowed and v is not None:\n'
        '            setattr(item, k, v)\n'
        '    db.commit()\n'
        '    db.refresh(item)\n'
        '\n'
        '    write_audit_log(\n'
        '        db, user_id=current_user.id, school_id=current_user.school_id,\n'
        '        action="CORRECTION", resource_type="Attendance", resource_id=attendance_id,\n'
        '        details={"old_status": str(old_status), "new_status": payload.get("status")},\n'
        '    )\n'
        '    return {\n'
        '        "id": item.id,\n'
        '        "student_id": item.student_id,\n'
        '        "section_id": item.section_id,\n'
        '        "date": str(getattr(item, "date", "")),\n'
        '        "status": str(getattr(item, "status", "")),\n'
        '    }\n'
    )
    print('  OK: FIX16 attendance correction PATCH endpoint added')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 17 — exam.py: add audit log on create/update/delete/publish
# ============================================================
path = 'backend-python/app/routers/v1/exam.py'
c = read_file(path)

# Add audit log to create_exam
old_create = (
    '    return ExamService.create_exam(\n'
    '        db,\n'
    '        obj_in=obj_in,\n'
    '        school_id=school_id,\n'
    '        created_by_id=current_user.id,\n'
    '    )\n'
)
new_create = (
    '    result = ExamService.create_exam(\n'
    '        db,\n'
    '        obj_in=obj_in,\n'
    '        school_id=school_id,\n'
    '        created_by_id=current_user.id,\n'
    '    )\n'
    '    write_audit_log(\n'
    '        db, user_id=current_user.id, school_id=school_id,\n'
    '        action="CREATE", resource_type="Exam", resource_id=getattr(result, "id", None),\n'
    '        details={"name": getattr(result, "name", "")},\n'
    '    )\n'
    '    return result\n'
)
c = replace_once(c, old_create, new_create, 'FIX17 exam create audit')

# Add audit log to update_exam  
old_update = (
    '    exam = ExamService.update_exam(db, exam_id=exam_id, obj_in=obj_in, school_id=school_id)\n'
    '    if not exam:\n'
    '        raise HTTPException(\n'
    '            status_code=status.HTTP_404_NOT_FOUND,\n'
    '            detail="Exam not found or unauthorized to edit",\n'
    '        )\n'
    '    return exam\n'
)
new_update = (
    '    exam = ExamService.update_exam(db, exam_id=exam_id, obj_in=obj_in, school_id=school_id)\n'
    '    if not exam:\n'
    '        raise HTTPException(\n'
    '            status_code=status.HTTP_404_NOT_FOUND,\n'
    '            detail="Exam not found or unauthorized to edit",\n'
    '        )\n'
    '    write_audit_log(\n'
    '        db, user_id=current_user.id, school_id=current_user.school_id,\n'
    '        action="UPDATE", resource_type="Exam", resource_id=exam_id,\n'
    '        details={"updates": str(obj_in.model_dump(exclude_none=True))[:500]},\n'
    '    )\n'
    '    return exam\n'
)
c = replace_once(c, old_update, new_update, 'FIX17 exam update audit')

# Add audit log to delete_exam
old_del = (
    '    success = ExamService.delete_exam(db, exam_id=exam_id, school_id=school_id)\n'
    '    if not success:\n'
    '        raise HTTPException(\n'
    '            status_code=status.HTTP_404_NOT_FOUND,\n'
    '            detail="Exam not found or unauthorized to delete",\n'
    '        )\n'
    '    return None\n'
)
new_del = (
    '    success = ExamService.delete_exam(db, exam_id=exam_id, school_id=school_id)\n'
    '    if not success:\n'
    '        raise HTTPException(\n'
    '            status_code=status.HTTP_404_NOT_FOUND,\n'
    '            detail="Exam not found or unauthorized to delete",\n'
    '        )\n'
    '    write_audit_log(\n'
    '        db, user_id=current_user.id, school_id=current_user.school_id,\n'
    '        action="DELETE", resource_type="Exam", resource_id=exam_id,\n'
    '        details={},\n'
    '    )\n'
    '    return None\n'
)
c = replace_once(c, old_del, new_del, 'FIX17 exam delete audit')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 18 — marks.py: principal/admin reopen capability
# ============================================================
path = 'backend-python/app/services/marks.py'
c = read_file(path)

# The existing lock logic: published exam blocks teacher submission
# Add reopen by adding PRINCIPAL check to allow correction
old_lock = (
    '        # Check locked status\n'
    '        if (exam.status or "").upper() == "PUBLISHED" and user_role != "SUPER_ADMIN":\n'
    '            raise HTTPException(\n'
    '                status_code=status.HTTP_409_CONFLICT,\n'
    '                detail="Exam marks are locked because the exam has already been published",\n'
    '            )\n'
)
new_lock = (
    '        # Check locked status — SUPER_ADMIN and PRINCIPAL may correct published marks\n'
    '        if (exam.status or "").upper() == "PUBLISHED" and user_role not in ("SUPER_ADMIN", "PRINCIPAL"):\n'
    '            raise HTTPException(\n'
    '                status_code=status.HTTP_409_CONFLICT,\n'
    '                detail="Exam marks are locked because the exam has already been published",\n'
    '            )\n'
)
c = replace_once(c, old_lock, new_lock, 'FIX18 marks: principal can correct published marks')

write_file(path, c)
print(f'Saved: {path}')

# ============================================================
# FIX 23 — announcement.py: audit on create/update/delete
# ============================================================
path = 'backend-python/app/routers/v1/announcement.py'
c = read_file(path)

# Add audit to create_announcement
old_create = (
    'def create_announcement(\r\n'
    '    obj_in: AnnouncementCreate,\r\n'
    '    db: Session = Depends(deps.get_db),\r\n'
    '    current_user: UserModel = Depends(deps.get_current_active_teacher),\r\n'
    '):\r\n'
    '    return AnnouncementService.create_announcement(db, obj_in=obj_in, current_user=current_user)\r\n'
)
new_create = (
    'def create_announcement(\r\n'
    '    obj_in: AnnouncementCreate,\r\n'
    '    db: Session = Depends(deps.get_db),\r\n'
    '    current_user: UserModel = Depends(deps.get_current_active_teacher),\r\n'
    '):\r\n'
    '    result = AnnouncementService.create_announcement(db, obj_in=obj_in, current_user=current_user)\r\n'
    '    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id, action="CREATE", resource_type="Announcement", resource_id=getattr(result, "id", None), details={"title": getattr(result, "title", "")})\r\n'
    '    return result\r\n'
)
c = replace_once(c, old_create, new_create, 'FIX23 announcement create audit')

# Add audit to update_announcement
old_upd = (
    'def update_announcement(\r\n'
    '    announcement_id: int,\r\n'
    '    obj_in: AnnouncementUpdate,\r\n'
    '    db: Session = Depends(deps.get_db),\r\n'
    '    current_user: UserModel = Depends(deps.get_current_active_user),\r\n'
    '):\r\n'
    '    return AnnouncementService.update_announcement(db, announcement_id=announcement_id, obj_in=obj_in, current_user=current_user)\r\n'
)
new_upd = (
    'def update_announcement(\r\n'
    '    announcement_id: int,\r\n'
    '    obj_in: AnnouncementUpdate,\r\n'
    '    db: Session = Depends(deps.get_db),\r\n'
    '    current_user: UserModel = Depends(deps.get_current_active_user),\r\n'
    '):\r\n'
    '    result = AnnouncementService.update_announcement(db, announcement_id=announcement_id, obj_in=obj_in, current_user=current_user)\r\n'
    '    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id, action="UPDATE", resource_type="Announcement", resource_id=announcement_id)\r\n'
    '    return result\r\n'
)
c = replace_once(c, old_upd, new_upd, 'FIX23 announcement update audit')

# Add audit to delete_announcement  
old_del = (
    'def delete_announcement(\r\n'
    '    announcement_id: int,\r\n'
    '    db: Session = Depends(deps.get_db),\r\n'
    '    current_user: UserModel = Depends(deps.get_current_active_user),\r\n'
    '):\r\n'
    '    return AnnouncementService.delete_announcement(db, announcement_id=announcement_id, current_user=current_user)\r\n'
)
new_del = (
    'def delete_announcement(\r\n'
    '    announcement_id: int,\r\n'
    '    db: Session = Depends(deps.get_db),\r\n'
    '    current_user: UserModel = Depends(deps.get_current_active_user),\r\n'
    '):\r\n'
    '    result = AnnouncementService.delete_announcement(db, announcement_id=announcement_id, current_user=current_user)\r\n'
    '    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id, action="DELETE", resource_type="Announcement", resource_id=announcement_id)\r\n'
    '    return result\r\n'
)
c = replace_once(c, old_del, new_del, 'FIX23 announcement delete audit')

write_file(path, c)
print(f'Saved: {path}')

print('\nAll backend fixes applied.')
