# Scholaris ERP — V1 CRUD Completion: Verified Implementation Plan

> I opened `geminiV3.zip` and checked every file/line reference from the ChatGPT
> review against your actual code. Line numbers below are the **real** ones in
> your zip (some differ slightly from the ChatGPT message). Everything marked
> `CONFIRMED` was read directly from your source. Follow the priority order —
> don't jump around.

Legend: 🔴 P0 (security / data integrity) · 🟠 P1 (functional gap) · 🟡 P2 (polish)

---

## HOW TO USE THIS FILE

For each fix you get:
1. **Files** — exact paths in your repo.
2. **Current code** — copied verbatim from your zip, with real line numbers.
3. **Change** — either a ready-to-paste patch (backend) or a precise spec
   (frontend forms), naming the exact existing service functions to call so
   you don't reinvent API plumbing.

Backend patches are written as minimal diffs you can paste in place of the
matching block. Frontend items that need a new modal/form give you the field
list + wiring; a reusable modal pattern is at the bottom (§ Appendix A) so you
don't rebuild it 10 times.

---

# 🔴 PRIORITY 1 — Attendance architecture + security

### Fix 1A — GET `/attendance` has no school/section scoping
**File:** `backend-python/app/routers/v1/attendance.py` (lines 18–57) — CONFIRMED

Current code lets `section_id` / `section_id+date` queries run with **no
ownership check at all** (only `student_id` and `STUDENT` role are checked).

**Patch** — add a helper and call it in the `elif` branches:

```python
# add near the top of attendance.py, after _assert_teacher_owns_section is defined later,
# or inline right in get_attendance:

def _assert_section_access(db: Session, current_user: User, section_id: int):
    role = str(current_user.role).upper()
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    if role == "SUPER_ADMIN":
        return
    if role == "PRINCIPAL":
        if section.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return
    if role == "TEACHER":
        _assert_teacher_owns_section(db, current_user, section_id)  # already defined below in file
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
```

Then in `get_attendance`, replace:
```python
    elif section_id and attendance_date:
        items = att_crud.get_attendance_by_date(db, section_id, attendance_date)
    elif section_id:
        items = att_crud.get_attendance_by_section(db, section_id, skip, limit)
```
with:
```python
    elif section_id and attendance_date:
        _assert_section_access(db, current_user, section_id)
        items = att_crud.get_attendance_by_date(db, section_id, attendance_date)
    elif section_id:
        _assert_section_access(db, current_user, section_id)
        items = att_crud.get_attendance_by_section(db, section_id, skip, limit)
```
⚠️ Because `_assert_teacher_owns_section` is defined **later** in the file
(currently at line 104), move its definition **above** `get_attendance`
(before line 18), or move `_assert_section_access` below it — Python needs it
defined before first use at runtime (module-level `def` order only matters if
called at import time, which it isn't here, so this is safe either way — just
keep both functions in the same file).

---

### Fix 1B — POST `/attendance` skips validation for non-Teacher roles
**File:** `backend-python/app/routers/v1/attendance.py`, `_assert_teacher_owns_section` (lines 104–135) and `mark_attendance` (lines 138–156) — CONFIRMED

Current: `_assert_teacher_owns_section` does `if role != "TEACHER": return` — so
a PRINCIPAL or SUPER_ADMIN posting attendance for **any student/section** is
never checked against their own school.

**Patch** — replace the early-return guard with role-aware checks:

```python
def _assert_attendance_write_allowed(db: Session, current_user: User, section_id: Optional[int], student_id: Optional[int] = None):
    role = str(current_user.role).upper()
    if not section_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section ID is required")
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    if role == "SUPER_ADMIN":
        pass  # cross-school allowed, but still validate relationship below
    elif role == "PRINCIPAL":
        if section.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Section does not belong to your school")
    elif role == "TEACHER":
        _assert_teacher_owns_section(db, current_user, section_id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if student_id:
        student = student_crud.get_student(db, student_id)
        if not student or student.school_id != section.school_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student does not belong to this section's school")
        # also confirm active enrollment in this section
        from app.models.student_enrollment import StudentEnrollment
        enrolled = db.query(StudentEnrollment).filter(
            StudentEnrollment.student_id == student_id,
            StudentEnrollment.section_id == section_id,
        ).first()
        if not enrolled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student is not enrolled in this section")
```

Then in `mark_attendance` (line 145) replace:
```python
    _assert_teacher_owns_section(db, current_user, payload.section_id)
```
with:
```python
    _assert_attendance_write_allowed(db, current_user, payload.section_id, payload.student_id)
```

And in `mark_bulk_attendance` (lines 169–170) replace:
```python
    for sid in distinct_section_ids:
        _assert_teacher_owns_section(db, current_user, sid)
```
with:
```python
    for entry in payload:
        sid = entry.get("section_id") if isinstance(entry, dict) else getattr(entry, "section_id", None)
        stid = entry.get("student_id") if isinstance(entry, dict) else getattr(entry, "student_id", None)
        _assert_attendance_write_allowed(db, current_user, sid, stid)
```
(you can then delete the now-unused `distinct_section_ids` line 165–168, or leave it, it's harmless).

---

### Fix 1C — Frontend expects DELETE, backend only has PATCH
**Files:**
- `frontend/src/services/attendance.ts` line 278–280 — CONFIRMED: `voidAttendance()` calls `api.delete('/attendance/${id}')`
- `backend-python/app/routers/v1/attendance.py` — only has `PATCH /{attendance_id}` (line 186), no DELETE route.

**Decision (recommended): void = PATCH with status `VOID`, never a hard delete.**

1. Backend — add `"VOID"` to the enum in `backend-python/app/models/attendance.py` line 15:
```python
    status = Column(Enum("PRESENT", "ABSENT", "LATE", "LEAVE", "VOID", name="attendance_status"), nullable=False)
```
(you'll need a migration — see your migrations folder / Alembic setup — to alter the existing DB enum type.)

2. Backend — in `attendance.py` router, add a dedicated void endpoint right after `correct_attendance` (after line 224):
```python
@router.post("/{attendance_id}/void", response_model=dict)
def void_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"]))
):
    item = att_crud.get_attendance(db, attendance_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
    role = str(current_user.role).upper()
    if role == "TEACHER":
        _assert_teacher_owns_section(db, current_user, item.section_id)
    elif role == "PRINCIPAL":
        section = db.query(Section).filter(Section.id == item.section_id).first()
        if not section or section.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    old_status = item.status
    item.status = "VOID"
    db.commit()
    db.refresh(item)
    write_audit_log(
        db, user_id=current_user.id, school_id=current_user.school_id,
        action="VOID", resource_type="Attendance", resource_id=attendance_id,
        details={"old_status": str(old_status)},
    )
    return {"id": item.id, "student_id": item.student_id, "section_id": item.section_id,
            "date": str(item.date), "status": str(item.status)}
```

3. Frontend — `frontend/src/services/attendance.ts` line 278–280, replace:
```ts
  async voidAttendance(id: number): Promise<void> {
    await api.delete(`/attendance/${id}`);
  },
```
with:
```ts
  async voidAttendance(id: number): Promise<AttendanceRecord> {
    const response = await api.post<AttendanceRecord>(`/attendance/${id}/void`);
    return response.data;
  },
```
Then find every caller of `attendanceService.voidAttendance` in
`frontend/src/pages/principal/Attendance.tsx` and `frontend/src/pages/teacher/Attendance.tsx`
and update them to handle the returned record instead of assuming a 204/void response.

---

### Fix 1D — Two incompatible attendance data layers
**Files (all CONFIRMED to exist and mismatch):**
```
backend-python/app/models/attendance.py            (canonical: Attendance, table attendance_records, fields: id, student_id, section_id, date, status, recorded_by)
backend-python/app/models/attendance_record.py     (AttendanceRecord = Attendance — just an alias)
backend-python/app/schemas/attendance.py
backend-python/app/schemas/attendance_record.py
backend-python/app/repositories/attendance.py
backend-python/app/repositories/attendance_record.py
backend-python/app/services/attendance.py
backend-python/app/services/attendance_record.py
backend-python/app/crud/attendance.py              <- this is the one actually wired into the router (att_crud)
backend-python/app/crud/attendance_record.py       <- unused by the router, references school_id/remarks/recorded_by_id which don't exist on Attendance
```

The router (`attendance.py`) only ever imports `app.crud.attendance as att_crud`.
The parallel `*_record.py` files (repositories/services/crud) are **dead code**
that assumes columns (`school_id`, `remarks`, `recorded_by_id`) the real
`Attendance` model doesn't have — if anything ever imports them, it will
throw at runtime.

**Action:**
1. Grep the whole backend for imports of the `*_record` modules:
   ```bash
   grep -rn "attendance_record\|AttendanceRecordService\|attendance_record_repo" backend-python/app --include=*.py
   ```
2. If nothing outside the `*_record.py` files themselves imports them → **delete**:
   - `backend-python/app/models/attendance_record.py`
   - `backend-python/app/schemas/attendance_record.py`
   - `backend-python/app/repositories/attendance_record.py`
   - `backend-python/app/services/attendance_record.py`
   - `backend-python/app/crud/attendance_record.py`
3. If `remarks` support is actually wanted (Fix 1's `correct_attendance` already
   writes `remarks` via `allowed = {"status", "remarks"}` at line 206), add a
   real `remarks` column to the canonical model instead of resurrecting the
   second architecture:
   ```python
   # backend-python/app/models/attendance.py — add under recorded_by (line 16)
   remarks = Column(String(255), nullable=True)
   ```
   (+ Alembic migration to add the column.)
4. Keep exactly **one** model/schema/service/crud path for attendance going
   forward — the one already wired into the router.

---

### Fix 1E — Attendance correction/void UI
**Files:**
```
frontend/src/pages/principal/Attendance.tsx   (77 lines — CONFIRMED currently only daily marking, no history view)
frontend/src/pages/teacher/Attendance.tsx     (245 lines — CONFIRMED daily marking only)
frontend/src/services/attendance.ts           (already has updateAttendance() and the new voidAttendance() from Fix 1C)
```

**Add to both pages:**
- A "History" tab/section: call `attendanceService.getAttendance({ section_id, attendance_date })` for a chosen date, or `getStudentAttendance(studentId)` for one student.
- Per-record row: **Edit status** (dropdown PRESENT/ABSENT/LATE/LEAVE) + **remarks** text input → `attendanceService.updateAttendance(id, { status, remarks })`.
- **Void** button → `attendanceService.voidAttendance(id)`, confirm via a dialog (not `window.confirm`, see Fix 27/Appendix A), then remove/gray out the row.
- Gate visibility: Teacher only sees sections `_assert_teacher_owns_section` would allow (i.e., sections they are class/subject teacher for — you already fetch this list elsewhere, e.g. `TeachingAssignments`); Principal sees all sections in `current_user.school_id`; Student page (if any) stays read-only — don't add edit controls there at all.

---

# 🔴 PRIORITY 2 — Announcement backend security + payload contract

### Fix 2A — Frontend payload contract mismatch
**File:** `frontend/src/pages/principal/Announcements.tsx` (27 lines total, CONFIRMED) — this is currently a placeholder page.

Backend schema (`backend-python/app/schemas/announcement.py`, CONFIRMED) requires:
```python
title: str
description: str                       # NOT "content"
audience: AnnouncementAudience          # "School-Wide" | "Teachers" | "Students" | "Parents" | "Grade" | "Section"
academic_year_id: Optional[int]
grade_id: Optional[int]
section_id: Optional[int]
priority: AnnouncementPriority = "Normal"   # "Low" | "Normal" | "High" | "Urgent"
publish_date: datetime                  # REQUIRED, not optional
expiry_date: Optional[datetime]
status: AnnouncementStatus = "Draft"    # "Draft" | "Published" | "Archived"
```
Current frontend line 14 sends `{ title, content, audience: 'ALL' }` — `content`
and `'ALL'` do not exist on the backend at all, so every create request will
fail Pydantic validation (422) once you're hitting the real API instead of a
mock.

**Rewrite `Announcements.tsx` create form to collect:**
```
Title            (text)
Description      (textarea)
Audience          (select: School-Wide / Teachers / Students / Grade / Section)  — omit "Parents", per Fix 2A note below
Grade             (select, shown only when Audience = Grade or Section)
Section           (select, shown only when Audience = Section)
Priority          (select: Low / Normal / High / Urgent, default Normal)
Publish date      (datetime-local input, required)
Expiry date       (datetime-local input, optional)
```
On submit:
```ts
await announcementService.createAnnouncement({
  title: title.trim(),
  description: description.trim(),
  audience,                     // one of the real enum values above
  grade_id: audience === 'Grade' || audience === 'Section' ? gradeId : undefined,
  section_id: audience === 'Section' ? sectionId : undefined,
  academic_year_id: currentAcademicYearId,   // pull from your academic-year context/store
  priority,
  publish_date: publishDate,     // ISO string
  expiry_date: expiryDate || undefined,
  status: 'Draft',               // or 'Published' if you add a "publish now" toggle
});
```
Do **not** expose `Parents` as an audience option in the picker — Parent is
not a live V1 role (per your "already done" list).

Also fix the Edit flow at line 21–22 (currently `window.prompt('Announcement title', ...)`
only edits `title`) — replace with a real modal exposing the same field set as
create, pre-filled from the existing announcement, calling
`announcementService.updateAnnouncement(item.id, { ...changedFields })`.
Check `frontend/src/services/announcement.ts` for the exact method names
already available (`listAnnouncements`, `createAnnouncement`,
`updateAnnouncement`, `deleteAnnouncement`, `publishAnnouncement`,
`archiveAnnouncement`) — all already exist, you're just wiring a real form to them.

---

### Fix 2B — PUT/DELETE authorization hole (students not explicitly blocked)
**Files:**
- `backend-python/app/routers/v1/announcement.py` lines 62–81 — CONFIRMED: `update_announcement` and `delete_announcement` both use `deps.get_current_active_user` (any authenticated user, any role).
- `backend-python/app/services/announcement.py` lines 86–116 — CONFIRMED: only checks `if user_role == "TEACHER" and created_by != current_user.id`. There is **no check at all** blocking `STUDENT`.

**Patch — service layer** (`announcement.py`), inside `update_announcement` (after line 89) and `delete_announcement` (after line 108), add before the existing TEACHER check:
```python
        if user_role == "STUDENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot modify announcements"
            )
```
So `update_announcement` becomes:
```python
    @staticmethod
    def update_announcement(
        db: Session, announcement_id: int, obj_in: AnnouncementUpdate, current_user: User
    ) -> Announcement:
        announcement = AnnouncementService.get_announcement(db, announcement_id, current_user=current_user)
        user_role = str(current_user.role).upper()
        if user_role == "STUDENT":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot modify announcements")
        if user_role == "TEACHER" and getattr(announcement, "created_by", None) != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teachers can only edit their own announcements")
        ...
```
(same pattern for `delete_announcement`).

**Also tighten the router dependency** — this is defense-in-depth, don't rely
on the service alone. In `announcement.py` router, change the dependency on
`update_announcement` and `delete_announcement` (lines 67 and 77) from:
```python
    current_user: UserModel = Depends(deps.get_current_active_user),
```
to a role-restricted dependency, e.g. using the pattern already used elsewhere in your codebase (`require_roles`, see `attendance.py` import at line 7):
```python
from app.api.deps import require_roles
...
    current_user: UserModel = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL", "TEACHER"])),
```

---

### Fix 2C — Students can read any status/audience via query params
**Files:** `backend-python/app/routers/v1/announcement.py` `list_announcements` (lines 21–42) + `backend-python/app/services/announcement.py` `list_announcements` (lines 29–52) — CONFIRMED: `status_filter` from the query string is passed straight through with no server-side enforcement for STUDENT role, and there is no audience filtering by the student's own grade/section.

**Patch — service** (`announcement.py`), replace `list_announcements`:
```python
    @staticmethod
    def list_announcements(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        audience: Optional[AnnouncementAudience] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        status: Optional[AnnouncementStatus] = None,
        author_id: Optional[int] = None,
        current_user: Optional[User] = None,
    ) -> Tuple[List[Announcement], int]:
        school_id = current_user.school_id if (current_user and str(current_user.role).upper() != "SUPER_ADMIN") else None
        user_role = str(current_user.role).upper() if current_user else None

        if user_role == "STUDENT":
            status = AnnouncementStatus.PUBLISHED  # force, ignore whatever the client asked for
            # Resolve the student's current grade/section and constrain the read
            from app.models.student import Student
            from app.models.student_enrollment import StudentEnrollment
            student = db.query(Student).filter(Student.user_id == current_user.id).first()
            enrollment = None
            if student:
                enrollment = (
                    db.query(StudentEnrollment)
                    .filter(StudentEnrollment.student_id == student.id)
                    .order_by(StudentEnrollment.id.desc())
                    .first()
                )
            student_grade_id = enrollment.section.grade_id if (enrollment and enrollment.section) else None
            student_section_id = enrollment.section_id if enrollment else None
            return crud_announcement.get_multi_for_student(
                db, skip=skip, limit=limit, school_id=school_id,
                grade_id=student_grade_id, section_id=student_section_id,
            )

        return crud_announcement.get_multi(
            db, skip=skip, limit=limit, school_id=school_id,
            audience=audience, grade_id=grade_id, section_id=section_id,
            status=status, author_id=author_id,
        )
```
This calls a new CRUD method `get_multi_for_student` — add it in
`backend-python/app/crud/announcement.py` alongside the existing `get_multi`,
filtering `Announcement.status == "Published"` AND
`Announcement.audience.in_(["School-Wide", "Students"]) OR (audience == "Grade" AND grade_id == student_grade_id) OR (audience == "Section" AND section_id == student_section_id)`.
Look at how `get_multi` currently builds its query in that file and mirror the
same query-building style so it stays consistent with your existing repo pattern.

---

### Fix 2D — Relationship validation on create/update
**Files:** `backend-python/app/services/announcement.py` `create_announcement` (54–83) / `update_announcement` (86–102), or the CRUD layer they call into (`backend-python/app/crud/announcement.py`).

Add, before calling `crud_announcement.create` / `.update`:
```python
        if obj_in.grade_id:
            grade = db.query(Grade).filter(Grade.id == obj_in.grade_id, Grade.school_id == school_id).first()
            if not grade:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade does not belong to this school")
        if obj_in.section_id:
            section = db.query(Section).filter(Section.id == obj_in.section_id, Section.school_id == school_id).first()
            if not section:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section does not belong to this school")
            if obj_in.grade_id and section.grade_id != obj_in.grade_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section does not belong to the selected grade")
        if obj_in.academic_year_id:
            ay = db.query(AcademicYear).filter(AcademicYear.id == obj_in.academic_year_id, AcademicYear.school_id == school_id).first()
            if not ay:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Academic year does not belong to this school")
```
(add the matching imports for `Grade`, `Section`, `AcademicYear` at the top of `announcement.py` — same pattern already used in `timetable.py`, see Fix 14 below).

---

# 🔴 PRIORITY 3 — Enrollment Edit/Transfer UI

**Files:**
- `frontend/src/pages/principal/Enrollments.tsx` (608 lines) — CONFIRMED: no edit/transfer/withdraw action in the student list.
- `frontend/src/services/enrollments.ts` (32 lines) — CONFIRMED: `updateEnrollment(id, { section_id?, academic_year_id?, roll_number? })` already exists (line 311) and calls `PATCH /student-enrollments/{id}`.
- `backend-python/app/routers/v1/student_enrollments.py` — CONFIRMED: `PATCH` at line 174 and `DELETE` at line 197 both work and already validate section/academic-year belong to the student's school; **neither writes an audit log**.

**Frontend — add per-row actions:**
```
Edit Enrollment → opens modal:
   student (read-only, from item.student.full_name)
   academic year   (select)
   grade           (select → filters section options)
   section         (select, filtered to chosen grade)
   roll number     (text)
   → enrollmentsService.updateEnrollment(item.id, { section_id, academic_year_id, roll_number })

Withdraw / Remove → confirm dialog → enrollmentsService.deleteEnrollment(item.id)
```
"Transfer Section" and "Change Academic Year" are just the same Edit modal
with only the section (or only the academic year) field changed — you don't
need separate UI flows, one modal with all four editable fields covers all of
Fix 1's requested actions (Edit / Transfer / Change Year / Change Roll / Withdraw).

**Backend — add audit logging.** `student_enrollments.py` already imports
`write_audit_log` (line 12) and uses it nowhere in this file. Add at the end
of `update_enrollment` (after line 194, before `return`):
```python
    write_audit_log(
        db, user_id=current_user.id, school_id=school_id,
        action="UPDATE", resource_type="StudentEnrollment", resource_id=enrollment_id,
        details={"updates": payload},
    )
```
and at the end of `remove_enrollment` (after line 211, before `return None`):
```python
    write_audit_log(
        db, user_id=current_user.id, school_id=item.student.school_id if item.student else None,
        action="DELETE", resource_type="StudentEnrollment", resource_id=enrollment_id,
        details={},
    )
```
(Move the `write_audit_log` calls to *before* `se_crud.delete_student_enrollment(db, item)` actually deletes the row, since you read `item.student` for the school_id — reorder so the audit call happens first, then delete.)

For `TRANSFER`/`WITHDRAW` as distinct audit *action* values (as ChatGPT's
review suggested) instead of a generic `UPDATE`/`DELETE`: in the frontend
modal, when only `section_id` changed, call update as normal but pass an
extra hint, e.g. `action=TRANSFER` via a query param, or simplest — just
detect server-side: if `payload` contains `section_id` different from the
existing enrollment's section, log `action="TRANSFER"` instead of `"UPDATE"`.

---

# 🔴 PRIORITY 4 — Exam Edit + published/delete protection

### Fix 4A — No Edit action in UI
**File:** `frontend/src/pages/principal/Exams.tsx` (502 lines) — CONFIRMED only Delete/Publish exist around the row actions.
**Service:** `frontend/src/services/exam.ts` line 30 — `updateExam(id, payload)` → `PATCH /exams/{id}` already exists and works.

Add an "Edit" button, shown **only when `exam.status !== 'PUBLISHED'`**, opening
a modal with fields matching `ExamUpdatePayload` (mirrors backend `ExamUpdate`
schema, confirmed in `backend-python/app/schemas/exam.py` lines 57–66):
```
name
exam_type
assessment_mode      (Formative / Summative)
academic_year_id
grade_id
section_id
start_date
end_date
```
On save → `examService.updateExam(exam.id, payload)`.

### Fix 4B — Backend allows editing published exams
**File:** `backend-python/app/services/exam.py`, `update_exam` (lines 217–229) — CONFIRMED: no status check at all.

**Patch:**
```python
    @staticmethod
    def update_exam(
        db: Session,
        exam_id: int,
        obj_in: ExamUpdate,
        school_id: Optional[int] = None,
    ) -> Optional[ExamResponse]:
        db_obj = crud_exam.get(db, exam_id=exam_id)
        if not db_obj:
            return None
        if school_id is not None and db_obj.school_id != school_id:
            return None
        if db_obj.status == "PUBLISHED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Published exams cannot be edited. Use the reopen workflow first."
            )
        # Cross-entity validation when grade/section/academic_year are being changed
        data = obj_in.model_dump(exclude_unset=True)
        effective_ay = data.get("academic_year_id", db_obj.academic_year_id)
        effective_grade = data.get("grade_id", db_obj.grade_id)
        effective_section = data.get("section_id", db_obj.section_id)
        target_school = school_id or db_obj.school_id
        from app.models.academic_year import AcademicYear
        from app.models.grade import Grade
        from app.models.section import Section
        ay = db.query(AcademicYear).filter(AcademicYear.id == effective_ay, AcademicYear.school_id == target_school).first()
        grade = db.query(Grade).filter(Grade.id == effective_grade, Grade.school_id == target_school).first()
        section = db.query(Section).filter(Section.id == effective_section).first()
        if not ay:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Academic year does not belong to this school")
        if not grade:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grade does not belong to this school")
        if not section or section.school_id != target_school or section.grade_id != effective_grade:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section does not belong to the selected grade/school")

        updated = crud_exam.update(db, db_obj=db_obj, obj_in=obj_in)
        return ExamService._format_exam_response(crud_exam.get(db, exam_id=updated.id))
```
Note: `status` is also an editable field on `ExamUpdate` (line 66) — decide
whether ordinary PATCH should ever be allowed to set `status` directly; if
not, strip it in the router before calling `update_exam`, and only allow
status transitions through `publish_exam` and the new reopen/republish
endpoints from Fix 7.

### Fix 4C — Exam delete can destroy historical marks
**Files:**
- `backend-python/app/services/exam.py`, `delete_exam` (lines 232–239) — CONFIRMED: unconditional `crud_exam.remove`.
- `backend-python/app/models/exam.py` line 39: `exam_subjects = relationship(..., cascade="all, delete-orphan")` and `exam_results` likewise — deleting an `Exam` cascades and destroys `ExamSubject` rows, which cascade-delete `Marks` too (`app/models/exam_subject.py` line 26: `marks = relationship("Marks", ..., cascade="all, delete-orphan")`). **CONFIRMED this is a real destructive cascade.**
- `frontend/src/pages/principal/Exams.tsx` — has a delete-confirmation string warning about deleting recorded marks (matches the destructive cascade above).

**Patch — block delete when marks exist:**
```python
    @staticmethod
    def delete_exam(db: Session, exam_id: int, school_id: Optional[int] = None) -> bool:
        db_obj = crud_exam.get(db, exam_id=exam_id)
        if not db_obj:
            return False
        if school_id is not None and db_obj.school_id != school_id:
            return False

        from app.models.exam_subject import ExamSubject
        from app.models.marks import Marks
        has_marks = (
            db.query(Marks)
            .join(ExamSubject, Marks.exam_subject_id == ExamSubject.id)
            .filter(ExamSubject.exam_id == exam_id)
            .first()
            is not None
        )
        if has_marks or db_obj.status == "PUBLISHED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This exam has recorded marks and cannot be deleted. Archive or cancel it instead."
            )
        crud_exam.remove(db, id=exam_id)
        return True
```
This needs an **archive/cancel path** for exams that do have marks. Simplest:
add an `"ARCHIVED"` (or `"CANCELLED"`) value to the `exam_status` enum in
`backend-python/app/models/exam.py` line 26, plus a migration, and a new
endpoint:
```python
# exam.py router, after delete_exam
@router.post("/{exam_id}/archive", response_model=ExamResponse)
def archive_exam(
    exam_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_principal),
):
    school_id = current_user.school_id if str(current_user.role).upper() != "SUPER_ADMIN" else None
    exam = ExamService.archive_exam(db, exam_id=exam_id, school_id=school_id)
    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id,
                     action="ARCHIVE", resource_type="Exam", resource_id=exam_id, details={})
    return exam
```
with a matching `ExamService.archive_exam` that just sets `db_obj.status = "ARCHIVED"` and commits (no deletion, no cascade).

Frontend: in `Exams.tsx`, when `getMarksStatus`/exam has any submitted marks,
swap the Delete button for an **Archive** button calling this new endpoint,
and update the confirmation copy so it no longer claims marks will be deleted.

---

# 🔴 PRIORITY 5 — Marks Reopen / Correct / Republish

**Files:**
```
backend-python/app/services/marks.py   (429 lines)
backend-python/app/routers/v1/marks.py (73 lines)
frontend/src/pages/teacher/MarksEntry.tsx
frontend/src/pages/principal/Marks.tsx
frontend/src/pages/teacher/ExamDetails.tsx
```

**Current state (CONFIRMED via `marks.py`):**
- Real exam status values are `SCHEDULED → MARKS_IN_PROGRESS → PUBLISHED` (there is **no** `LOCKED` value on the `Exam` model — `_marks_lifecycle_state` (lines 29–34) checks for `"LOCKED"`/`"CLOSED"` defensively but nothing in your codebase ever sets those, so that branch is currently dead).
- `_assert_marks_editable` (lines 40–46) already blocks edits once `PUBLISHED` for everyone except SUPER_ADMIN/PRINCIPAL (`allow_correction`), and blocks `LOCKED` for everyone but SUPER_ADMIN — so the guard rails exist, but there is **no endpoint that flips status back**, so PRINCIPAL correction on published marks currently has no controlled path — a Principal could theoretically hit `submit_marks` directly with `allow_correction`-style logic baked in, but there's no explicit "reopen" audit trail.

**Add two endpoints, reusing the existing `Exam.status` field (no new model needed):**

`backend-python/app/routers/v1/marks.py` — add:
```python
@router.post("/exams/{exam_id}/reopen-marks", response_model=dict)
def reopen_marks(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if str(current_user.role).upper() != "SUPER_ADMIN" and exam.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if exam.status != "PUBLISHED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only published exams can be reopened")
    exam.status = "MARKS_IN_PROGRESS"
    db.commit()
    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id,
                     action="REOPEN", resource_type="Exam", resource_id=exam_id, details={})
    return {"exam_id": exam_id, "status": exam.status}


@router.post("/exams/{exam_id}/republish", response_model=dict)
def republish_marks(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["SUPER_ADMIN", "PRINCIPAL"])),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if str(current_user.role).upper() != "SUPER_ADMIN" and exam.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if exam.status != "MARKS_IN_PROGRESS":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam must be reopened before it can be republished")
    exam.status = "PUBLISHED"
    db.commit()
    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id,
                     action="REPUBLISH", resource_type="Exam", resource_id=exam_id, details={})
    return {"exam_id": exam_id, "status": exam.status}
```
(add `from app.models.exam import Exam` and `from app.api.deps import require_roles` / `write_audit_log` imports at the top if not already present — `marks.py` router is only 73 lines, check its current imports first.)

Between reopen and republish, marks edits go through your **existing**
`submit_marks` (`marks.py` service, lines 135+) — since `exam.status` is now
`MARKS_IN_PROGRESS`, `_assert_marks_editable` already permits teacher edits
normally. No change needed there — reopen/republish is purely a status gate
around your existing submit flow. This satisfies "log the correction" because
`submit_marks` should already be writing an audit entry — check
`backend-python/app/services/marks.py` for an existing `write_audit_log` call
in `submit_marks`; if it's missing, add one there too (`action="CORRECTION"`
when `exam.status == "MARKS_IN_PROGRESS"` and marks already existed for that
student, vs `action="SUBMIT"` for first entry).

**Frontend:**
- `ExamDetails.tsx` (teacher) and `Marks.tsx` (principal): when
  `exam.status === 'PUBLISHED'`, show a **"Reopen for correction"** button
  (Principal/SuperAdmin only) → calls the new `reopen-marks` endpoint, then
  refetches.
- Once reopened (`MARKS_IN_PROGRESS`), `MarksEntry.tsx` already supports
  editing (per your "already done" list, lock logic exists) — just make sure
  the UI's "locked" banner keys off `status === 'PUBLISHED'`, not a
  non-existent `LOCKED` value.
- Add a **"Republish"** button next to Reopen, enabled once corrections are
  done, calling the new `republish` endpoint.
- Add these two service methods to `frontend/src/services/exam.ts`:
```ts
  async reopenMarks(examId: number): Promise<{exam_id: number; status: string}> {
    const response = await api.post(`/exams/${examId}/reopen-marks`);
    return response.data;
  },
  async republishMarks(examId: number): Promise<{exam_id: number; status: string}> {
    const response = await api.post(`/exams/${examId}/republish`);
    return response.data;
  },
```
(Adjust the route prefix if your marks router is mounted at `/marks` rather
than reusing `/exams` — check how `marks.py`'s `router = APIRouter(prefix=...)`
is declared before finalizing the path; if it's `/marks`, mount these two
routes there instead and call them from `frontend/src/services/marks.ts`.)

---

# 🔴 PRIORITY 6 — Formative marks correction lifecycle

Same files as Priority 5: `marks.py` service has `submit_formative_marks`
(lines 228+, CONFIRMED) with the same `SCHEDULED → MARKS_IN_PROGRESS` bump
(line 284–285) but no reopen/republish concept once `PUBLISHED`.

**Reuse the exact two endpoints from Priority 5** — `reopen-marks` and
`republish` operate on the `Exam` record, and both formative and summative
marks live under the same `Exam`/`ExamSubject` structure (per your "recommended
backend" note to not invent a new model). No new code needed here beyond
Priority 5 — just make sure `MarksEntry.tsx`'s formative-entry mode also reads
`exam.status` the same way as summative mode does, so the Reopen/Republish
buttons gate both entry types identically.

---

# 🔴 PRIORITY 7 — Timetable UPDATE/COPY conflict validation

### Fix 7A — Update doesn't check teacher double-booking
**File:** `backend-python/app/services/timetable.py`, `update_timetable` (lines 188–242) — CONFIRMED: validates grade/section/subject/teacher/academic-year *ownership* but never re-runs the overlap check that `create_timetable` does at lines 150–166.

**Patch** — insert before `updated = crud_timetable.update(...)` (line 241):
```python
        effective_teacher_id = data.get("teacher_id", timetable.teacher_id)
        effective_day = data.get("day_of_week", timetable.day_of_week)
        conflict = db.query(Timetable).filter(
            Timetable.id != timetable_id,
            Timetable.teacher_id == effective_teacher_id,
            Timetable.day_of_week == effective_day,
            Timetable.start_time < end_t,
            Timetable.end_time > start_t,
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"This teacher is already scheduled on {effective_day} from "
                    f"{conflict.start_time} to {conflict.end_time} (section {conflict.section_id})."
                ),
            )

        updated = crud_timetable.update(db, db_obj=timetable, obj_in=data)
```
(`start_t`/`end_t` are already computed just above, at lines 233–234 — this
patch just adds the missing `Timetable.id != timetable_id` exclusion + overlap
query, mirroring the create-path logic at lines 150–166 exactly.)

### Fix 7B — Copy bypasses validation entirely
**File:** `backend-python/app/services/timetable.py`, `copy_timetable` (lines 261–290) — CONFIRMED: builds a `data` dict and calls `crud_timetable.create()` **directly**, skipping `create_timetable()`'s validation (grade/section/subject/teacher/school ownership + conflict check) entirely.

**Simplest correct fix — route copy through the same validated path:**
```python
    @staticmethod
    def copy_timetable(db: Session, timetable_id: int, copy_in: TimetableCopy, school_id: Optional[int] = None) -> Dict[str, Any]:
        source = crud_timetable.get(db, timetable_id)
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source timetable not found")
        if school_id is not None and source.school_id != school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: source timetable does not belong to your school")

        target_grade_id = copy_in.target_grade_id if copy_in.target_grade_id is not None else source.grade_id
        target_section_id = copy_in.target_section_id if copy_in.target_section_id is not None else source.section_id

        data = {
            "academic_year_id": source.academic_year_id,
            "grade_id": target_grade_id,
            "section_id": target_section_id,
            "subject_id": source.subject_id,
            "teacher_id": source.teacher_id,
            "day_of_week": source.day_of_week,
            "start_time": source.start_time,
            "end_time": source.end_time,
            "room_number": source.room_number,
        }
        # Route through the fully-validated create path instead of crud_timetable.create() directly
        return TimetableService.create_timetable(db, obj_in=TimetableCreate(**data), school_id=source.school_id)
```
Check `create_timetable`'s exact signature/decorator a few lines above line
130 to confirm the parameter name is `obj_in` and it accepts a `TimetableCreate`
(imported already, line 13) — construct it from the `data` dict as shown.
This gives Copy the same grade/section/subject/teacher/academic-year school
checks and the same conflict detection as a normal Create, for free.

---

# 🔴 PRIORITY 8 — Teacher-assignment GET security hole

**File:** `backend-python/app/routers/v1/teacher_assignments.py` (69 lines, full file CONFIRMED) — `list_assignments` (lines 14–29) takes `teacher_id` as a plain query param and returns that teacher's timetable rows to **any authenticated user**, with `get_current_active_user` as the only dependency — no role or ownership check.

**Patch:**
```python
@router.get("", response_model=List[dict])
def list_assignments(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    role = str(current_user.role).upper()
    if role == "STUDENT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if role == "TEACHER":
        from app.crud import teacher as teacher_crud
        teacher = teacher_crud.get_teacher_by_user_id(db, current_user.id)
        if not teacher or teacher.id != teacher_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only view your own assignments")
    elif role == "PRINCIPAL":
        from app.models.teacher import Teacher
        teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
        if not teacher or teacher.school_id != current_user.school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher does not belong to your school")
    elif role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    timetables = db.query(Timetable).filter(Timetable.teacher_id == teacher_id).all()
    return [
        {
            "id": t.id,
            "teacher_id": t.teacher_id,
            "section_id": getattr(t, "section_id", None),
            "subject_id": getattr(t, "subject_id", None)
        }
        for t in timetables
    ]
```
(`status` is already imported at line 3 of this file — CONFIRMED — so no new import needed for `HTTPException`/`status`.)

Alternative (simpler, if this legacy route isn't actually used by the
frontend anymore — grep `frontend/src` for `/teacher-assignments` GET calls
first): just delete the `list_assignments` function and its route decorator
entirely, keeping only POST/DELETE which are already role-guarded via
`require_roles(["SUPER_ADMIN", "PRINCIPAL"])` at lines 36 and 60.

---

# 🟠 PRIORITY 9 — School deactivation → login/session blocking

**Files:** `backend-python/app/services/auth_service.py` (51 lines) and `backend-python/app/api/deps.py` `get_current_active_user` (lines 98–119) — CONFIRMED: only `User.is_active` (a string `account_status` column, values like `"ACTIVE"`) is checked. `School.is_active` (a real `Boolean` column, `backend-python/app/models/school.py` line 15) is never consulted anywhere in the auth path.

**Patch — `deps.py`, `get_current_active_user` (replace lines 98–119):**
```python
def get_current_active_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Verifies the authenticated user's account AND (for non-Super-Admins)
    their school are both active. Runs on every authenticated request, so a
    school deactivation immediately blocks already-issued sessions too.
    """
    account_status = getattr(current_user, "is_active", None)
    if account_status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")

    role = str(getattr(current_user, "role", "")).upper()
    if role != "SUPER_ADMIN" and current_user.school_id:
        from app.models.school import School
        school = db.query(School).filter(School.id == current_user.school_id).first()
        if school is not None and school.is_active is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your school account has been deactivated")

    return current_user
```
`get_current_active_user` didn't previously take a `db` dependency — check
every place it's used as a `Depends(...)` chain (it's used everywhere, e.g.
`attendance.py`, `announcement.py`, `exam.py`, `users.py`); adding a `Session
= Depends(get_db)` parameter to it is transparent to callers since FastAPI
resolves the dependency tree automatically — no call sites need to change.

**Also patch the login flow** in `auth_service.py` — find the function that
authenticates username/password (open the file and locate the `login`/
`authenticate_user` function) and add the same `school.is_active` check right
after the existing `user.is_active` check, before issuing a token, so a
deactivated school also can't log in fresh (not just get blocked on
subsequent requests).

---

# 🟠 PRIORITY 10 — Real Super Admin User Edit

**File:** `frontend/src/pages/superadmin/Users.tsx` line 112 (CONFIRMED):
```tsx
onClick={() => window.alert('Edit user details through the profile workflow.')}
```
**Service:** `frontend/src/services/users.ts` line 206 — `updateUser(id, payload)` → `PATCH /users/{id}` already exists. Backend `users.py` `update_user` at line 137 already accepts a payload dict (open that function to see the exact whitelist of accepted keys before finalizing your form fields — likely `full_name`, `email`, `mobile` per the ChatGPT note).

**Replace the alert with a real modal** (see Appendix A pattern), fields:
```
Full Name    (text)
Email        (email)
Mobile       (tel)
```
Submit → `usersService.updateUser(u.id, { full_name, email, mobile })`, then
merge the returned user into local state. Keep the existing
Activate/Deactivate/Reset-Password/Offboard buttons (lines 112) as separate,
already-working actions — don't fold lifecycle changes into this Edit modal.

---

# 🟠 PRIORITY 11 — Full Student/Teacher/Principal Edit forms

All three follow the exact same pattern; only field lists differ. Reuse
Appendix A's modal.

### Student
**File:** `frontend/src/pages/principal/Students.tsx` (~183–187, CONFIRMED shallow: only `full_name`).
**Service:** `studentsService.updateStudent(id, payload)` → `PATCH /students/{id}` (`frontend/src/services/students.ts` line 42) — check `StudentUpdatePayload` type in `frontend/src/types` for the exact backend-accepted field names before wiring, then build the modal with:
```
Full Name, Mobile, Email, Date of Birth, Gender, Blood Group,
Father Name / Mother Name / Guardian Name + Contact,
Address, Admission Date, Roll Number
```

### Teacher
**File:** `frontend/src/pages/principal/Teachers.tsx` (~149–153, CONFIRMED shallow).
**Service:** `teachersService.updateTeacher(id, payload)` (line 78) → `PATCH /teachers/{id}`.
```
Full Name, Mobile, Email, Qualification, Department,
Specialization, Joining Date, Address, Employee ID
```

### Principal
**File:** `frontend/src/pages/superadmin/Principals.tsx` (~87–91, CONFIRMED shallow).
**Service:** `principalsService.updatePrincipal(id, payload)` (line 121) → `PATCH /principals/{id}`.
```
Full Name, Mobile, Email, Employee ID, Joining Date, School assignment (if reassignment is supported backend-side — check the PATCH schema; if school_id isn't in the accepted update fields, omit this field and handle re-assignment as a separate dedicated action instead of silently failing)
```

For all three: **check the actual Pydantic `*UpdatePayload`/`*Update` schema
in `backend-python/app/schemas/` before finalizing which fields the modal
exposes** — only show fields the backend will actually persist, so you don't
build UI for a field silently ignored server-side. Do not add role/permission
fields to any of these ordinary edit modals.

---

# 🟠 PRIORITY 12 — Section Class Teacher editing

**File:** `frontend/src/pages/principal/Sections.tsx`, `editSection` (line 43, CONFIRMED) currently only changes `name`.
**Service:** `sectionsService.updateSection(id, payload)` (line 148, `frontend/src/services/sections.ts`) → `PATCH /sections/{id}`. Backend already supports `class_teacher_id` per your note — confirm the field name in `backend-python/app/schemas/section.py`.

Replace `editSection`'s current `window.prompt`-based flow with a modal:
```
Section Name        (text)
Class Teacher        (select, populated from teachersService.listTeachers())
```
Submit → `sectionsService.updateSection(section.id, { name, class_teacher_id })`.

---

# 🟠 PRIORITY 13 — Teacher-Subject proper Edit modal

**File:** `frontend/src/pages/principal/TeachingAssignments.tsx` line 610 (CONFIRMED):
```tsx
const teacherId = window.prompt('Teacher ID', String(assignment.teacher_id));
```
**Service:** `teacherSubjectsService.update(id, payload)` (`frontend/src/services/teacherSubjects.ts` line 173) → `PATCH /teacher-subjects/{id}`, already wired to a backend endpoint that validates the teacher/subject relationship (`backend-python/app/routers/v1/teacher_subjects.py` lines 71–92, CONFIRMED — see `_validate_assignment_relationships`).

Replace the `window.prompt` block with a modal:
```
Teacher   (select, from teachersService.listTeachers())
Subject   (select, from your existing subjects service)
Save
```
Submit → `teacherSubjectsService.update(assignment.id, { teacher_id, subject_id })`.

**Add audit logging** — `backend-python/app/routers/v1/teacher_subjects.py`
`update_teacher_subject_assignment` (lines 71–92) and
`remove_teacher_subject_assignment` (lines 95–104) currently call
`service.update_assignment` / `service.delete_assignment` with no
`write_audit_log` call at all (CONFIRMED — no audit import in this file).
Add:
```python
from app.core.audit import write_audit_log
```
at the top, then after `return service.update_assignment(...)` becomes:
```python
    result = service.update_assignment(assignment_id, payload)
    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id,
                     action="UPDATE", resource_type="TeacherSubject", resource_id=assignment_id, details={})
    return result
```
and before `return None` in the delete route:
```python
    write_audit_log(db, user_id=current_user.id, school_id=current_user.school_id,
                     action="DELETE", resource_type="TeacherSubject", resource_id=assignment_id, details={})
```

---

# 🟠 PRIORITY 14 — Historical-delete dependency guards

**Files & current state (CONFIRMED to exist, need extending):**

- `backend-python/app/routers/v1/academic_years.py` — currently checks enrollments only. Add checks (query `Exam`, `Timetable`, `Marks` via `ExamSubject`, and any report-card table) filtered by `academic_year_id`; if any exist, reject hard delete and require an "archive" action instead (flip an `is_active`/`status` flag rather than deleting the row).
- `backend-python/app/routers/v1/sections.py` — currently checks enrollments only. Add checks for `Attendance` (`section_id`), `Timetable` (`section_id`), `Exam` (`section_id`).
- `backend-python/app/routers/v1/subjects.py` — currently checks exam results only. Add checks for `TeacherSubject` (`subject_id`), `Timetable` (`subject_id`), `ExamSubject` (`subject_id`), `Marks` (via `ExamSubject`).

**Pattern to copy into each of the three files** (adapt table/column names to
what each router already imports — open each file's existing delete route
first to see its current single-dependency check and extend it in place
rather than rewriting the route):
```python
    blocking = []
    if db.query(SomeRelatedModel).filter(SomeRelatedModel.section_id == section_id).first():
        blocking.append("attendance records")
    if db.query(Timetable).filter(Timetable.section_id == section_id).first():
        blocking.append("timetable entries")
    if db.query(Exam).filter(Exam.section_id == section_id).first():
        blocking.append("exams")
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: this section has {', '.join(blocking)}. Archive it instead."
        )
```
Since your "already done" list confirms Grade/Section/Subject/Academic-Year
already have **edit/archive/delete** endpoints, check whether an
`is_active`/`status` toggle already exists on each model before adding a new
one — you likely just need to extend the *delete* guard's dependency list and
point the frontend's error handling at the existing archive action when the
delete call returns 409.

---

# 🟡 PRIORITY 15 — Missing audit logs (roundup)

Already covered above per-fix (Priority 3 enrollment, Priority 13 teacher-subject).
Do a final sweep: grep for routers that mutate data but never import
`write_audit_log`:
```bash
grep -L "write_audit_log" backend-python/app/routers/v1/*.py
```
Cross-reference the output against your "already done" list — anything not
already covered there needs the same `write_audit_log(...)` pattern used
throughout `exam.py`/`announcement.py` added to its PATCH/DELETE routes.

---

# 🟡 PRIORITY 16 — Hard-coded academic-year values

All three CONFIRMED with exact strings:

**File 1:** `frontend/src/pages/principal/AcademicYears.tsx` lines 13–14:
```tsx
const [startDate, setStartDate] = useState('2026-09-09');
const [endDate, setEndDate] = useState('2027-09-08');
```
Replace with:
```tsx
const [startDate, setStartDate] = useState('');
const [endDate, setEndDate] = useState('');
```
(or compute a rolling default like `` `${new Date().getFullYear()}-06-01` `` if you want a sensible placeholder instead of blank — but don't hard-code a fixed year).

**File 2:** `frontend/src/pages/principal/Marks.tsx` lines 46 and 53:
```tsx
{id === 2 ? '2026-2027' : `Year ${id}`}
...
Academic year {selectedRows[0]?.academic_year_id === 2 ? '2026-2027' : selectedRows[0]?.academic_year_id}
```
Replace both with a lookup against the real academic year list you already
fetch elsewhere (e.g. a small `academicYearsById` map built from
`academicYearsService.listAcademicYears()` → `{ [ay.id]: ay.name }`), so it
reads:
```tsx
{academicYearsById[id]?.name ?? `Year ${id}`}
...
Academic year {academicYearsById[selectedRows[0]?.academic_year_id]?.name ?? selectedRows[0]?.academic_year_id}
```

**File 3:** `frontend/src/pages/principal/ReportCards.tsx` lines 29, 67, 75 —
same `academic_year_id === 2 ? '2026-2027' : ...` pattern in three places.
Apply the identical `academicYearsById[...]?.name` fix at all three lines.

---

# 🟡 PRIORITY 17 — Replace `window.prompt`/`confirm`/`alert`

**Files (CONFIRMED, grep for `window.prompt|window.confirm|window.alert` in each to get exact line numbers in your working copy — they'll shift slightly once you've applied the earlier fixes):**
```
frontend/src/pages/principal/Grades.tsx
frontend/src/pages/principal/Sections.tsx           (see Priority 12 — replaced there)
frontend/src/pages/principal/Subjects.tsx
frontend/src/pages/principal/AcademicYears.tsx
frontend/src/pages/principal/Students.tsx           (see Priority 11)
frontend/src/pages/principal/Teachers.tsx           (see Priority 11)
frontend/src/pages/principal/TeachingAssignments.tsx (see Priority 13)
frontend/src/pages/superadmin/Principals.tsx        (see Priority 11)
frontend/src/pages/superadmin/Users.tsx             (see Priority 10)
frontend/src/pages/principal/Announcements.tsx      (see Priority 2A)
```
Most are already being replaced as part of their dedicated fix above (11–13,
2A, 10, 12). What's left standalone: **Grades.tsx, Subjects.tsx,
AcademicYears.tsx create/edit-name flows** — these are simple single-field
edits (name / academic year name), so a lightweight shared `<PromptModal
label="..." initialValue="..." onSubmit={...}/>` (see Appendix A) is enough —
you don't need the full multi-field modal pattern for these three.
Also replace bare `window.confirm('Are you sure?')` delete confirmations
across the same files with a shared `<ConfirmDialog/>` component so styling
and copy are consistent (call it "Archive" instead of "Delete" wherever the
underlying action is actually an archive per Priority 14).

---

# 🟡 PRIORITY 18 — Announcement notification integration

**File:** `backend-python/app/services/announcement.py`, `_trigger_notifications` (lines 139–142, CONFIRMED):
```python
    @staticmethod
    def _trigger_notifications(announcement: Announcement) -> None:
        # Structure for notification integration without modifying existing module
        pass
```
This is called from `create_announcement` (line 81), `update_announcement`
(line 100), and `publish_announcement` (line 124) whenever status becomes
`PUBLISHED`.

- **If you have a notifications module already** (search `backend-python/app`
  for `notification` — check `app/services/` and `app/models/` for an
  existing `Notification` model/service): wire it in here, e.g.
  ```python
  @staticmethod
  def _trigger_notifications(announcement: Announcement) -> None:
      from app.services.notification import NotificationService
      NotificationService.notify_announcement(announcement)
  ```
- **If there is no notification system yet**, this is out of scope for V1
  CRUD completion — leave the `pass`, but delete the misleading calls to
  `_trigger_notifications(...)` at lines 81/100/124 (or leave them — they're
  harmless no-ops) and note in your own backlog that "true" publish delivery
  is a V2 feature, not a CRUD bug.

---

# Appendix A — Reusable modal pattern (frontend)

Every "replace prompt() with a real form" fix above (Priorities 2A, 10, 11,
12, 13, 17) is the same shape: a controlled modal with typed fields, calling
an existing `*Service.update*()` function. If you don't already have a shared
modal component, add one so you're not duplicating markup 10 times:

```tsx
// frontend/src/components/EditModal.tsx
import React, { useState } from 'react';

export interface Field {
  key: string;
  label: string;
  type?: 'text' | 'email' | 'tel' | 'date' | 'datetime-local' | 'select' | 'textarea';
  options?: { value: string | number; label: string }[]; // for type: 'select'
  required?: boolean;
}

interface EditModalProps {
  title: string;
  fields: Field[];
  initialValues: Record<string, any>;
  onSubmit: (values: Record<string, any>) => Promise<void>;
  onClose: () => void;
}

export const EditModal: React.FC<EditModalProps> = ({ title, fields, initialValues, onSubmit, onClose }) => {
  const [values, setValues] = useState<Record<string, any>>(initialValues);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit(values);
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <form
        onClick={e => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="bg-white rounded-2xl p-5 w-full max-w-md space-y-3 shadow-xl"
      >
        <h2 className="text-sm font-bold text-slate-900">{title}</h2>
        {fields.map(f => (
          <div key={f.key} className="space-y-1">
            <label className="text-xs font-semibold text-slate-600">{f.label}</label>
            {f.type === 'select' ? (
              <select
                className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                value={values[f.key] ?? ''}
                required={f.required}
                onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))}
              >
                <option value="" disabled>Select...</option>
                {f.options?.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            ) : f.type === 'textarea' ? (
              <textarea
                className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                value={values[f.key] ?? ''}
                required={f.required}
                onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))}
              />
            ) : (
              <input
                type={f.type || 'text'}
                className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                value={values[f.key] ?? ''}
                required={f.required}
                onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))}
              />
            )}
          </div>
        ))}
        {error && <p className="text-xs text-rose-600">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="text-xs px-3 py-2 rounded-lg border border-slate-200">Cancel</button>
          <button type="submit" disabled={saving} className="text-xs px-3 py-2 rounded-lg bg-indigo-600 text-white font-bold disabled:opacity-50">
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default EditModal;
```

Usage example (Super Admin User Edit, Priority 10):
```tsx
{editingUser && (
  <EditModal
    title="Edit User"
    fields={[
      { key: 'full_name', label: 'Full Name', required: true },
      { key: 'email', label: 'Email', type: 'email' },
      { key: 'mobile', label: 'Mobile', type: 'tel' },
    ]}
    initialValues={editingUser}
    onSubmit={async (values) => {
      const updated = await usersService.updateUser(editingUser.id, values);
      setUsers(current => current.map(u => u.id === updated.id ? updated : u));
    }}
    onClose={() => setEditingUser(null)}
  />
)}
```

A simple `ConfirmDialog` for replacing `window.confirm` follows the same
shape minus the fields array — a title, a message, Cancel/Confirm buttons,
and an `onConfirm: () => Promise<void>` prop.

---

# Execution order (unchanged from the review, verified achievable in this codebase)

```
1. Attendance architecture + security         (Priority 1, all sub-fixes)
2. Announcement backend security + contract   (Priority 2, all sub-fixes)
3. Enrollment Edit/Transfer UI                (Priority 3)
4. Exam Edit + published/delete protection    (Priority 4)
5. Marks Reopen/Correct/Republish             (Priority 5)
6. Formative marks correction lifecycle       (Priority 6)
7. Timetable update/copy conflict validation  (Priority 7)
8. Teacher-assignment GET security            (Priority 8)
9. School deactivation → login/session block  (Priority 9)
10. Real Super Admin User Edit                (Priority 10)
11. Full Student/Teacher/Principal Edit forms (Priority 11)
12. Section Class Teacher editing             (Priority 12)
13. Teacher-Subject proper Edit modal + audit (Priority 13)
14. Historical-delete dependency guards       (Priority 14)
15. Missing audit logs roundup                (Priority 15)
16. Hard-coded academic-year values           (Priority 16)
17. Replace prompt/confirm/alert CRUD UX      (Priority 17)
18. Announcement notification integration     (Priority 18)
```

The five you should not skip, unchanged and confirmed real in your code:
**Attendance security (1A/1B), Announcement security (2B/2C), Exam
delete/published protection (4B/4C), Marks reopen/correction (5), Timetable
update/copy validation (7A/7B).** Everything else is a real gap but won't
silently corrupt data or leak cross-school/cross-role access the way those
five will if left as-is.
