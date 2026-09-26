"""Apply remaining Scholaris V1 fixes (frontend + backend gaps)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(p):
    return (ROOT / p).read_text(encoding='utf-8')

def write(p, c):
    (ROOT / p).write_text(c, encoding='utf-8')
    print('Wrote', p)

def patch_once(path, old, new, label):
    c = read(path)
    if old not in c:
        print('SKIP', label)
        return
    write(path, c.replace(old, new, 1))
    print('OK', label)

# --- Backend: teacher_assignments TimetableService ---
patch_once(
    'backend-python/app/routers/v1/teacher_assignments.py',
    '''    data = dict(payload)
    if "start_time" in data and data["start_time"] is not None:
        data["start_time"] = parse_time(data["start_time"])
    if "end_time" in data and data["end_time"] is not None:
        data["end_time"] = parse_time(data["end_time"])
    item = Timetable(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "teacher_id": item.teacher_id,
        "section_id": getattr(item, "section_id", None),
        "subject_id": getattr(item, "subject_id", None)
    }''',
    '''    from app.services.timetable import TimetableService
    from app.schemas.timetable import TimetableCreate
    try:
        obj_in = TimetableCreate(**payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else payload.get("school_id")
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context missing")
    item = TimetableService.create_timetable(db, obj_in=obj_in, school_id=int(school_id))
    return {
        "id": item["id"],
        "teacher_id": item.get("teacher_id"),
        "section_id": item.get("section_id"),
        "subject_id": item.get("subject_id"),
    }''',
    'teacher_assignments create via TimetableService',
)

patch_once(
    'backend-python/app/routers/v1/teacher_assignments.py',
    '''    item = db.query(Timetable).filter(Timetable.id == assignment_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    db.delete(item)
    db.commit()
    return None''',
    '''    from app.services.timetable import TimetableService
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    try:
        TimetableService.delete_timetable(db, timetable_id=assignment_id, school_id=school_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found or access denied")
    return None''',
    'teacher_assignments delete via TimetableService',
)

# --- Backend: announcement audit + student mutate block ---
for old, new, lbl in [
    (
        '    return AnnouncementService.create_announcement(db, obj_in=obj_in, current_user=current_user)\r\n',
        '    result = AnnouncementService.create_announcement(db, obj_in=obj_in, current_user=current_user)\r\n'
        '    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id, action="CREATE", resource_type="Announcement", resource_id=getattr(result, "id", None), details={"title": getattr(result, "title", "")})\r\n'
        '    return result\r\n',
        'announcement create audit',
    ),
    (
        '    return AnnouncementService.update_announcement(db, announcement_id=announcement_id, obj_in=obj_in, current_user=current_user)\r\n',
        '    result = AnnouncementService.update_announcement(db, announcement_id=announcement_id, obj_in=obj_in, current_user=current_user)\r\n'
        '    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id, action="UPDATE", resource_type="Announcement", resource_id=announcement_id)\r\n'
        '    return result\r\n',
        'announcement update audit',
    ),
    (
        '    return AnnouncementService.delete_announcement(db, announcement_id=announcement_id, current_user=current_user)\r\n',
        '    result = AnnouncementService.delete_announcement(db, announcement_id=announcement_id, current_user=current_user)\r\n'
        '    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id, action="DELETE", resource_type="Announcement", resource_id=announcement_id)\r\n'
        '    return result\r\n',
        'announcement delete audit',
    ),
]:
    patch_once('backend-python/app/routers/v1/announcement.py', old, new, lbl)

c = read('backend-python/app/services/announcement.py')
if 'if user_role == "STUDENT":' not in c.split('def update_announcement')[1].split('def delete_announcement')[0]:
    c = c.replace(
        '        announcement = AnnouncementService.get_announcement(db, announcement_id, current_user=current_user)\r\n'
        '        user_role = str(current_user.role).upper()\r\n'
        '        if user_role == "TEACHER" and getattr(announcement, "created_by", None) != current_user.id:',
        '        announcement = AnnouncementService.get_announcement(db, announcement_id, current_user=current_user)\r\n'
        '        user_role = str(current_user.role).upper()\r\n'
        '        if user_role == "STUDENT":\r\n'
        '            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot edit announcements")\r\n'
        '        if user_role == "TEACHER" and getattr(announcement, "created_by", None) != current_user.id:',
        1,
    )
if 'Students cannot delete' not in c:
    c = c.replace(
        '        user_role = str(current_user.role).upper()\r\n'
        '        if user_role == "TEACHER" and getattr(announcement, "created_by", None) != current_user.id:\r\n'
        '            raise HTTPException(\r\n'
        '                status_code=status.HTTP_403_FORBIDDEN,\r\n'
        '                detail="Teachers can only delete their own announcements"\r\n'
        '            )',
        '        user_role = str(current_user.role).upper()\r\n'
        '        if user_role == "STUDENT":\r\n'
        '            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot delete announcements")\r\n'
        '        if user_role == "TEACHER" and getattr(announcement, "created_by", None) != current_user.id:\r\n'
        '            raise HTTPException(\r\n'
        '                status_code=status.HTTP_403_FORBIDDEN,\r\n'
        '                detail="Teachers can only delete their own announcements"\r\n'
        '            )',
        1,
    )
write('backend-python/app/services/announcement.py', c)

# --- marks lifecycle helpers in marks service ---
c = read('backend-python/app/services/marks.py')
if '_marks_lifecycle_state' not in c:
    insert = '''
    @staticmethod
    def _marks_lifecycle_state(exam: Exam) -> str:
        st = (getattr(exam, "status", None) or "DRAFT").upper()
        if st == "PUBLISHED":
            return "PUBLISHED"
        if st in ("LOCKED", "CLOSED"):
            return "LOCKED"
        if st in ("SUBMITTED", "MARKS_IN_PROGRESS"):
            return "SUBMITTED"
        return "DRAFT"

    @staticmethod
    def _assert_marks_editable(exam: Exam, current_user: User, allow_correction: bool = False) -> None:
        state = MarksService._marks_lifecycle_state(exam)
        role = str(current_user.role).upper()
        if state == "LOCKED" and role != "SUPER_ADMIN":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Marks are locked")
        if state == "PUBLISHED" and role not in ("SUPER_ADMIN", "PRINCIPAL") and not allow_correction:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Published marks cannot be edited")
'''
    c = c.replace('class MarksService:\n    @staticmethod\n    def _check_submission_permission(', insert + '    @staticmethod\n    def _check_submission_permission(', 1)
    write('backend-python/app/services/marks.py', c)

# --- Services ---
write('frontend/src/services/academicYears.ts', read('frontend/src/services/academicYears.ts').rstrip() + '''

  async deleteAcademicYear(id: number): Promise<void> {
    await api.delete(`/academic-years/${id}`);
  },
};
'''.replace('};};', '};').replace('};', '};', 1) if 'deleteAcademicYear' not in read('frontend/src/services/academicYears.ts') else read('frontend/src/services/academicYears.ts'))

# fix academicYears - the above might break; do properly
ay = read('frontend/src/services/academicYears.ts')
if 'deleteAcademicYear' not in ay:
    ay = ay.replace(
        '  async updateAcademicYear(id: number, payload: AcademicYearUpdatePayload): Promise<AcademicYear> {\n'
        '    const response = await api.patch<AcademicYear>(`/academic-years/${id}`, payload);\n'
        '    return response.data;\n'
        '  },\n};',
        '  async updateAcademicYear(id: number, payload: AcademicYearUpdatePayload): Promise<AcademicYear> {\n'
        '    const response = await api.patch<AcademicYear>(`/academic-years/${id}`, payload);\n'
        '    return response.data;\n'
        '  },\n\n'
        '  async deleteAcademicYear(id: number): Promise<void> {\n'
        '    await api.delete(`/academic-years/${id}`);\n'
        '  },\n};',
    )
    write('frontend/src/services/academicYears.ts', ay)

en = read('frontend/src/services/enrollments.ts')
if 'updateEnrollment' not in en:
    en = en.replace(
        '  async deleteEnrollment(id: number): Promise<void> {\n'
        '    await api.delete(`/student-enrollments/${id}`);\n'
        '  },\n};',
        '  async deleteEnrollment(id: number): Promise<void> {\n'
        '    await api.delete(`/student-enrollments/${id}`);\n'
        '  },\n\n'
        '  async updateEnrollment(id: number, payload: { section_id?: number; academic_year_id?: number; roll_number?: string }): Promise<StudentEnrollment> {\n'
        '    const response = await api.patch<StudentEnrollment>(`/student-enrollments/${id}`, payload);\n'
        '    return response.data;\n'
        '  },\n};',
    )
    write('frontend/src/services/enrollments.ts', en)

att = read('frontend/src/services/attendance.ts')
if 'updateAttendance' not in att:
    att = att.replace(
        'export default attendanceService;\n',
        '  async updateAttendance(id: number, payload: { status?: string; remarks?: string }): Promise<AttendanceRecord> {\n'
        '    const response = await api.patch<AttendanceRecord>(`/attendance/${id}`, payload);\n'
        '    return response.data;\n'
        '  },\n};\n\nexport default attendanceService;\n',
    )
    att = att.replace('};\n\nexport default', '  async updateAttendance(id: number, payload: { status?: string; remarks?: string }): Promise<AttendanceRecord> {\n    const response = await api.patch<AttendanceRecord>(`/attendance/${id}`, payload);\n    return response.data;\n  },\n};\n\nexport default') if 'updateAttendance' not in att else att
    if 'updateAttendance' not in att:
        att = att.replace(
            '  },\n};\n\nexport default attendanceService;',
            '  },\n\n  async updateAttendance(id: number, payload: { status?: string; remarks?: string }): Promise<AttendanceRecord> {\n    const response = await api.patch<AttendanceRecord>(`/attendance/${id}`, payload);\n    return response.data;\n  },\n};\n\nexport default attendanceService;',
        )
    write('frontend/src/services/attendance.ts', att)

sch = read('frontend/src/services/schools.ts')
if 'updateSchoolLifecycle' not in sch:
    sch = sch.replace(
        '  async updateSchool(id: number, payload: SchoolUpdatePayload): Promise<School> {\n'
        '    const response = await api.patch<School>(`/schools/${id}`, payload);\n'
        '    return response.data;\n'
        '  },\n};',
        '  async updateSchool(id: number, payload: SchoolUpdatePayload): Promise<School> {\n'
        '    const response = await api.patch<School>(`/schools/${id}`, payload);\n'
        '    return response.data;\n'
        '  },\n\n'
        '  async updateSchoolLifecycle(id: number, action: \'DEACTIVATE\' | \'REACTIVATE\'): Promise<School> {\n'
        '    const response = await api.post<School>(`/schools/${id}/lifecycle`, { action });\n'
        '    return response.data;\n'
        '  },\n};',
    )
    write('frontend/src/services/schools.ts', sch)

usr = read('frontend/src/services/users.ts')
if 'resetUserPassword' not in usr:
    usr = usr.replace(
        '  async updateUser(id: number, payload: UserUpdatePayload): Promise<AppUser> {\n'
        '    const response = await api.patch<AppUser>(`/users/${id}`, payload);\n'
        '    return response.data;\n'
        '  },\n};',
        '  async updateUser(id: number, payload: UserUpdatePayload): Promise<AppUser> {\n'
        '    const response = await api.patch<AppUser>(`/users/${id}`, payload);\n'
        '    return response.data;\n'
        '  },\n\n'
        '  async resetUserPassword(id: number, password: string): Promise<void> {\n'
        '    await api.post(`/users/${id}/reset-password`, { password });\n'
        '  },\n\n'
        '  async setUserActive(id: number, active: boolean): Promise<AppUser> {\n'
        '    return this.updateUser(id, { is_active: active ? \'ACTIVE\' : \'INACTIVE\' } as UserUpdatePayload);\n'
        '  },\n};',
    )
    write('frontend/src/services/users.ts', usr)

for svc, method in [
    ('frontend/src/services/grades.ts', 'deleteGrade'),
    ('frontend/src/services/sections.ts', 'deleteSection'),
    ('frontend/src/services/subjects.ts', 'deleteSubject'),
]:
    s = read(svc)
    if method in s:
        continue
    s = s.replace('};\n', '  async ' + method + '(id: number): Promise<void> {\n    await api.delete(`/' + svc.split('/')[-1].replace('.ts','').replace('grades','grades').replace('sections','sections').replace('subjects','subjects') + '/${id}`);\n  },\n};\n')
    # fix paths
    if 'grades' in svc:
        s = s.replace('deleteGrade', 'deleteGrade').replace('/grades/${id}', '/grades/${id}')
        s = read(svc)
        s = s.replace(
            '  async updateGrade(id: number, payload: GradeUpdatePayload): Promise<Grade> {\n    const response = await api.patch<Grade>(`/grades/${id}`, payload);\n    return response.data;\n  },\n};',
            '  async updateGrade(id: number, payload: GradeUpdatePayload): Promise<Grade> {\n    const response = await api.patch<Grade>(`/grades/${id}`, payload);\n    return response.data;\n  },\n\n  async deleteGrade(id: number): Promise<void> {\n    await api.delete(`/grades/${id}`);\n  },\n};',
        )
    if 'sections' in svc:
        s = read(svc)
        s = s.replace(
            '  async updateSection(id: number, payload: SectionUpdatePayload): Promise<Section> {\n    const response = await api.patch<Section>(`/sections/${id}`, payload);\n    return response.data;\n  },\n};',
            '  async updateSection(id: number, payload: SectionUpdatePayload): Promise<Section> {\n    const response = await api.patch<Section>(`/sections/${id}`, payload);\n    return response.data;\n  },\n\n  async deleteSection(id: number): Promise<void> {\n    await api.delete(`/sections/${id}`);\n  },\n};',
        )
    if 'subjects' in svc:
        s = read(svc)
        s = s.replace(
            '  async updateSubject(id: number, payload: SubjectUpdatePayload): Promise<Subject> {\n    const response = await api.patch<Subject>(`/subjects/${id}`, payload);\n    return response.data;\n  },\n};',
            '  async updateSubject(id: number, payload: SubjectUpdatePayload): Promise<Subject> {\n    const response = await api.patch<Subject>(`/subjects/${id}`, payload);\n    return response.data;\n  },\n\n  async deleteSubject(id: number): Promise<void> {\n    await api.delete(`/subjects/${id}`);\n  },\n};',
        )
    write(svc, s)

print('apply_remaining_v1: services/backend partial done')
