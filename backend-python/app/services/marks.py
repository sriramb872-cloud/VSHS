# app/services/marks.py
from datetime import datetime
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.exam_result import ExamResult
from app.models.marks import Marks
from app.models.section import Section
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.timetable import Timetable
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.user import User
from app.crud.notification import notification as crud_notification
from app.schemas.marks import (
    MarksSubmitPayload,
    FormativeMarksSubmitPayload,
    MarkResponse,
    StudentMarksViewItem,
    StudentMarksViewResponse,
)


class MarksService:
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
    @staticmethod
    def _validate_submission_students(
        db: Session,
        exam: Exam,
        marks: List,
    ) -> None:
        """Reject empty submissions and students outside the exam's section.

        Two integrity rules that both submission paths need:

        1. An empty submission is never a legitimate "marks completed" signal.
           Previously an empty grid still flipped ``is_marks_submitted`` to
           True and notified the class teacher that the subject was done,
           which made the ``is_all_submitted`` readiness flag meaningless.

        2. Every student being marked must actually be enrolled in the section
           this exam belongs to. Without this check a teacher assigned to one
           section could POST marks for any student id in the school (including
           students of a different section), because the permission check above
           only inspects the *exam subject*, never the students in the payload.
        """
        if not marks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No marks were supplied. Enter at least one student's marks before submitting.",
            )

        section = db.query(Section).filter(Section.id == exam.section_id).first()
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam section not found",
            )

        enrolled_student_ids = {
            row[0]
            for row in db.query(StudentEnrollment.student_id)
            .filter(
                StudentEnrollment.section_id == exam.section_id,
                StudentEnrollment.academic_year_id == exam.academic_year_id,
            )
            .all()
        }
        if not enrolled_student_ids:
            return

        foreign = sorted({item.student_id for item in marks} - enrolled_student_ids)
        if foreign:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Student(s) "
                    + ", ".join(f"#{sid}" for sid in foreign)
                    + " are not enrolled in this exam's section"
                ),
            )

    @staticmethod
    def _check_submission_permission(
        db: Session,
        exam_subject: ExamSubject,
        exam: Exam,
        current_user: User,
    ) -> None:
        user_role = str(current_user.role).upper()

        if user_role not in ("SUPER_ADMIN", "PRINCIPAL", "TEACHER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to submit marks",
            )

        # Check locked status — SUPER_ADMIN and PRINCIPAL may correct published marks
        if (exam.status or "").upper() == "PUBLISHED" and user_role not in ("SUPER_ADMIN", "PRINCIPAL"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Exam marks are locked because the exam has already been published",
            )

        # Tenant boundary: everyone except SUPER_ADMIN is scoped to their own
        # school. This used to be inside the TEACHER branch only, so a principal
        # of one school could write marks into any other school's exam.
        if user_role != "SUPER_ADMIN" and current_user.school_id != exam.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to submit marks for this school's examination",
            )

        # If teacher, verify teacher is assigned
        if user_role == "TEACHER":
            teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
            if not teacher:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher profile not found")

            if teacher.school_id != exam.school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to submit marks for this school's examination",
                )

            # Check if teacher matches the assigned exam subject, an explicit
            # teacher_subjects assignment, or the school-scoped timetable
            # assignment used by the Teacher portal.
            is_assigned = (exam_subject.teacher_id == teacher.id)
            if not is_assigned:
                ts = db.query(TeacherSubject).filter(
                    TeacherSubject.teacher_id == teacher.id,
                    TeacherSubject.school_id == exam.school_id,
                    TeacherSubject.section_id == exam.section_id,
                    TeacherSubject.subject_id == exam_subject.subject_id,
                ).first()
                if ts:
                    is_assigned = True
            if not is_assigned:
                timetable_assignment = db.query(Timetable).filter(
                    Timetable.teacher_id == teacher.id,
                    Timetable.school_id == exam.school_id,
                    Timetable.academic_year_id == exam.academic_year_id,
                    Timetable.grade_id == exam.grade_id,
                    Timetable.section_id == exam.section_id,
                    Timetable.subject_id == exam_subject.subject_id,
                ).first()
                is_assigned = timetable_assignment is not None

            if not is_assigned:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to submit marks for this subject",
                )

    @staticmethod
    def _send_class_teacher_notification(
        db: Session,
        exam: Exam,
        exam_subject: ExamSubject,
        current_user: User,
    ) -> None:
        teacher_name = getattr(current_user, "display_name", None) or getattr(current_user, "full_name", "Teacher")
        sub_name = exam_subject.subject.name if (exam_subject.subject and hasattr(exam_subject.subject, "name")) else (exam_subject.subject.subject_name if hasattr(exam_subject.subject, "subject_name") else f"Subject #{exam_subject.subject_id}")
        sec_name = exam.section.name if (exam.section and hasattr(exam.section, "name")) else (exam.section.section_name if hasattr(exam.section, "section_name") else f"Section #{exam.section_id}")

        # TODO: this ONLY_FOR_CLASS "Marks Submitted" notice is meant for the
        # class teacher, but that type is visible to the class's STUDENTS (and
        # not to teachers). Push is disabled so students don't get a push
        # about marks that are not published yet. Revisit when the in-app
        # visibility for this notice is fixed.
        crud_notification.create(
            db,
            title="Marks Submitted",
            message=f"{teacher_name} submitted marks for {sub_name} — {exam.name}, {sec_name}.",
            notification_type="ONLY_FOR_CLASS",
            sender_id=current_user.id,
            sender_role=str(current_user.role).upper(),
            school_id=exam.school_id,
            category="CLASS_TEACHER",
            target_class_id=exam.section_id,
            push=False,
        )

    @staticmethod
    def submit_marks(db: Session, payload: MarksSubmitPayload, current_user: User) -> List[MarkResponse]:
        exam_subject = db.query(ExamSubject).filter(ExamSubject.id == payload.exam_subject_id).first()
        if not exam_subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam subject not found")

        exam = db.query(Exam).filter(Exam.id == exam_subject.exam_id).first()
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        # Authorization first: the mode hint below must never leak whether an
        # exam exists/belongs to another school (cross-tenant callers get 403
        # before any exam-specific detail is revealed).
        MarksService._check_submission_permission(db, exam_subject, exam, current_user)

        if (exam.assessment_mode or "FORMATIVE").upper() == "FORMATIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "This exam is FORMATIVE. Use POST /marks/submit-formative "
                    "(written_test/project/read_reflection/notebook) instead of "
                    "the generic /marks/submit — marks entered here would be "
                    "silently discarded when the exam is published."
                ),
            )

        MarksService._validate_submission_students(db, exam, payload.marks)

        # Validate marks values
        for item in payload.marks:
            if item.marks_obtained < 0 or item.marks_obtained > exam_subject.maximum_marks:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Marks obtained ({item.marks_obtained}) for student #{item.student_id} must be between 0 and {exam_subject.maximum_marks}",
                )

        now = datetime.utcnow()
        saved_items: List[Marks] = []

        for item in payload.marks:
            existing = db.query(Marks).filter(
                Marks.exam_subject_id == payload.exam_subject_id,
                Marks.student_id == item.student_id,
            ).first()

            if existing:
                existing.marks_obtained = item.marks_obtained
                existing.max_marks = exam_subject.maximum_marks
                existing.remarks = item.remarks
                existing.entered_by_id = current_user.id
                existing.updated_at = now
                saved_items.append(existing)
            else:
                new_mark = Marks(
                    exam_subject_id=payload.exam_subject_id,
                    student_id=item.student_id,
                    school_id=exam.school_id,
                    marks_obtained=item.marks_obtained,
                    max_marks=exam_subject.maximum_marks,
                    remarks=item.remarks,
                    entered_by_id=current_user.id,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_mark)
                saved_items.append(new_mark)

        exam_subject.is_marks_submitted = True
        exam_subject.submitted_at = now
        if exam.status == "SCHEDULED":
            exam.status = "MARKS_IN_PROGRESS"

        db.commit()

        for s in saved_items:
            db.refresh(s)

        MarksService._send_class_teacher_notification(db, exam, exam_subject, current_user)

        results: List[MarkResponse] = []
        for s in saved_items:
            student = db.query(Student).filter(Student.id == s.student_id).first()
            student_name = student.user.display_name if (student and student.user and hasattr(student.user, "display_name")) else f"Student #{s.student_id}"
            results.append(
                MarkResponse(
                    id=s.id,
                    exam_subject_id=s.exam_subject_id,
                    student_id=s.student_id,
                    student_name=student_name,
                    marks_obtained=s.marks_obtained,
                    max_marks=s.max_marks,
                    remarks=s.remarks,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )
        return results

    @staticmethod
    def submit_formative_marks(db: Session, payload: FormativeMarksSubmitPayload, current_user: User) -> List[dict]:
        exam_subject = db.query(ExamSubject).filter(ExamSubject.id == payload.exam_subject_id).first()
        if not exam_subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam subject not found")

        exam = db.query(Exam).filter(Exam.id == exam_subject.exam_id).first()
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        MarksService._check_submission_permission(db, exam_subject, exam, current_user)
        MarksService._validate_submission_students(db, exam, payload.marks)

        # Validate formative components
        for item in payload.marks:
            if not (0 <= item.written_test <= 20):
                raise HTTPException(status_code=400, detail=f"Written test marks for student #{item.student_id} must be 0-20")
            if not (0 <= item.project <= 5):
                raise HTTPException(status_code=400, detail=f"Project marks for student #{item.student_id} must be 0-5")
            if not (0 <= item.read_reflection <= 5):
                raise HTTPException(status_code=400, detail=f"Read reflection marks for student #{item.student_id} must be 0-5")
            if not (0 <= item.notebook <= 5):
                raise HTTPException(status_code=400, detail=f"Notebook marks for student #{item.student_id} must be 0-5")

        now = datetime.utcnow()
        saved_items: List[ExamResult] = []

        for item in payload.marks:
            existing = db.query(ExamResult).filter(
                ExamResult.exam_id == exam.id,
                ExamResult.student_id == item.student_id,
                ExamResult.subject_id == exam_subject.subject_id,
            ).first()

            if existing:
                existing.written_test = item.written_test
                existing.project = item.project
                existing.read_reflection = item.read_reflection
                existing.notebook = item.notebook
                existing.updated_at = now
                saved_items.append(existing)
            else:
                new_er = ExamResult(
                    exam_id=exam.id,
                    student_id=item.student_id,
                    subject_id=exam_subject.subject_id,
                    written_test=item.written_test,
                    project=item.project,
                    read_reflection=item.read_reflection,
                    notebook=item.notebook,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_er)
                saved_items.append(new_er)

        exam_subject.is_marks_submitted = True
        exam_subject.submitted_at = now
        if exam.status == "SCHEDULED":
            exam.status = "MARKS_IN_PROGRESS"

        db.commit()

        MarksService._send_class_teacher_notification(db, exam, exam_subject, current_user)

        return [
            {
                "id": er.id,
                "exam_id": er.exam_id,
                "student_id": er.student_id,
                "subject_id": er.subject_id,
                "written_test": er.written_test,
                "project": er.project,
                "read_reflection": er.read_reflection,
                "notebook": er.notebook,
                "total": er.written_test + er.project + er.read_reflection + er.notebook,
            }
            for er in saved_items
        ]

    @staticmethod
    def list_marks(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        exam_id: Optional[int] = None,
        exam_subject_id: Optional[int] = None,
        student_id: Optional[int] = None,
        school_id: Optional[int] = None,
        exam_subject_ids: Optional[List[int]] = None,
        academic_year_id: Optional[int] = None,
        published_only: bool = False,
    ) -> Tuple[List[MarkResponse], int]:
        # FORMATIVE exams store their rows in `exam_results`, not `marks`.
        # Reading an exam subject therefore has to switch to that table so the
        # teacher's grid can be repopulated when they hit Edit.
        if exam_subject_id is not None:
            exam_subject = (
                db.query(ExamSubject).filter(ExamSubject.id == exam_subject_id).first()
            )
            if exam_subject is not None:
                exam = exam_subject.exam
                if exam is not None and (exam.assessment_mode or "FORMATIVE").upper() == "FORMATIVE":
                    return MarksService._list_formative_results(
                        db,
                        exam=exam,
                        exam_subject=exam_subject,
                        student_id=student_id,
                        school_id=school_id,
                        skip=skip,
                        limit=limit,
                        published_only=published_only,
                    )

        query = db.query(Marks)

        if school_id is not None:
            query = query.filter(Marks.school_id == school_id)
        if exam_subject_ids is not None:
            query = query.filter(Marks.exam_subject_id.in_(exam_subject_ids))
        if exam_subject_id is not None:
            query = query.filter(Marks.exam_subject_id == exam_subject_id)
        # Join each table at most once: joining ExamSubject once for `exam_id`
        # and again for the academic-year filter produced
        # "Not unique table/alias: 'exam_subjects'" (HTTP 500).
        if exam_id is not None or academic_year_id is not None:
            query = query.join(ExamSubject, Marks.exam_subject_id == ExamSubject.id)
        if exam_id is not None:
            query = query.filter(ExamSubject.exam_id == exam_id)
        if academic_year_id is not None:
            # Marks inherit the year through Marks -> ExamSubject -> Exam.
            # No denormalised year column on `marks` itself.
            query = (
                query.join(Exam, ExamSubject.exam_id == Exam.id)
                .filter(Exam.academic_year_id == academic_year_id)
            )
        if student_id is not None:
            query = query.filter(Marks.student_id == student_id)
        if published_only:
            # Students (and their exam views) must never read marks for an
            # exam the Principal has not published yet.
            query = query.filter(
                Marks.exam_subject_id.in_(
                    select(ExamSubject.id)
                    .join(Exam, ExamSubject.exam_id == Exam.id)
                    .where(Exam.status == "PUBLISHED")
                )
            )

        total = query.count()
        items = query.order_by(Marks.id.desc()).offset(skip).limit(limit).all()

        responses: List[MarkResponse] = []
        for item in items:
            student = db.query(Student).filter(Student.id == item.student_id).first()
            st_name = student.user.display_name if (student and student.user and hasattr(student.user, "display_name")) else f"Student #{item.student_id}"
            exam_subject = item.exam_subject
            exam = exam_subject.exam if exam_subject else None
            subject = exam_subject.subject if exam_subject else None
            responses.append(
                MarkResponse(
                    id=item.id,
                    exam_subject_id=item.exam_subject_id,
                    student_id=item.student_id,
                    student_name=st_name,
                    roll_number=student.roll_number if student else None,
                    marks_obtained=item.marks_obtained,
                    max_marks=item.max_marks,
                    remarks=item.remarks,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    exam_id=exam.id if exam else None,
                    exam_name=exam.name if exam else None,
                    subject_id=exam_subject.subject_id if exam_subject else None,
                    subject_name=(getattr(subject, "name", None) or getattr(subject, "subject_name", None)) if subject else None,
                    grade_id=exam.grade_id if exam else None,
                    section_id=exam.section_id if exam else None,
                    academic_year_id=exam.academic_year_id if exam else None,
                    teacher_id=exam_subject.teacher_id if exam_subject else None,
                )
            )
        return responses, total

    @staticmethod
    def _list_formative_results(
        db: Session,
        exam: Exam,
        exam_subject: ExamSubject,
        student_id: Optional[int] = None,
        school_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        published_only: bool = False,
    ) -> Tuple[List[MarkResponse], int]:
        if school_id is not None and exam.school_id != school_id:
            return [], 0
        if published_only and (exam.status or "").upper() != "PUBLISHED":
            return [], 0

        query = db.query(ExamResult).filter(
            ExamResult.exam_id == exam.id,
            ExamResult.subject_id == exam_subject.subject_id,
        )
        if student_id is not None:
            query = query.filter(ExamResult.student_id == student_id)

        total = query.count()
        items = query.order_by(ExamResult.id.desc()).offset(skip).limit(limit).all()

        subject = exam_subject.subject
        subject_name = (
            getattr(subject, "name", None)
            or getattr(subject, "subject_name", None)
            or f"Subject #{exam_subject.subject_id}"
        )

        responses: List[MarkResponse] = []
        for item in items:
            student = db.query(Student).filter(Student.id == item.student_id).first()
            st_name = (
                student.user.display_name
                if (student and student.user and hasattr(student.user, "display_name"))
                else f"Student #{item.student_id}"
            )
            responses.append(
                MarkResponse(
                    id=item.id,
                    exam_subject_id=exam_subject.id,
                    student_id=item.student_id,
                    student_name=st_name,
                    roll_number=student.roll_number if student else None,
                    marks_obtained=(
                        item.written_test + item.project + item.read_reflection + item.notebook
                    ),
                    max_marks=float(exam_subject.maximum_marks or 35.0),
                    remarks=None,
                    written_test=item.written_test,
                    project=item.project,
                    read_reflection=item.read_reflection,
                    notebook=item.notebook,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    exam_id=exam.id,
                    exam_name=exam.name,
                    subject_id=exam_subject.subject_id,
                    subject_name=subject_name,
                    grade_id=exam.grade_id,
                    section_id=exam.section_id,
                    academic_year_id=exam.academic_year_id,
                    teacher_id=exam_subject.teacher_id,
                )
            )
        return responses, total

    @staticmethod
    def get_student_marks_view(
        db: Session,
        current_user: User,
        academic_year_id: Optional[int] = None,
    ) -> StudentMarksViewResponse:
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

        # Always scope to the student's own school - the previous query was
        # platform-wide and leaked every school's published exams.
        exam_query = db.query(Exam).filter(
            Exam.status == "PUBLISHED",
            Exam.school_id == student.school_id,
        )
        if academic_year_id is None:
            # Default to the year the student is placed in (latest placement)
            # so a student never sees last year's marks by accident.
            enrollment = (
                db.query(StudentEnrollment)
                .filter(StudentEnrollment.student_id == student.id)
                .order_by(StudentEnrollment.id.desc())
                .first()
            )
            academic_year_id = enrollment.academic_year_id if enrollment else None
        if academic_year_id is not None:
            exam_query = exam_query.filter(Exam.academic_year_id == academic_year_id)
        published_exams = exam_query.all()
        results: List[StudentMarksViewItem] = []

        for ex in published_exams:
            is_formative = (ex.assessment_mode or "FORMATIVE").upper() == "FORMATIVE"
            for es in ex.exam_subjects:
                sub_name = es.subject.name if (es.subject and hasattr(es.subject, "name")) else (es.subject.subject_name if hasattr(es.subject, "subject_name") else f"Subject #{es.subject_id}")

                if is_formative:
                    er = db.query(ExamResult).filter(
                        ExamResult.exam_id == ex.id,
                        ExamResult.student_id == student.id,
                        ExamResult.subject_id == es.subject_id,
                    ).first()
                    if er:
                        tot = er.written_test + er.project + er.read_reflection + er.notebook
                        results.append(
                            StudentMarksViewItem(
                                exam_id=ex.id,
                                exam_name=ex.name,
                                exam_type=ex.exam_type,
                                assessment_mode="FORMATIVE",
                                exam_subject_id=es.id,
                                subject_id=es.subject_id,
                                subject_name=sub_name,
                                marks_obtained=tot,
                                max_marks=es.maximum_marks or 40.0,
                                passing_marks=es.passing_marks or 14.0,
                                is_passed=tot >= (es.passing_marks or 14.0),
                                components={
                                    "written_test": er.written_test,
                                    "project": er.project,
                                    "read_reflection": er.read_reflection,
                                    "notebook": er.notebook,
                                },
                            )
                        )
                else:
                    mk = db.query(Marks).filter(
                        Marks.exam_subject_id == es.id,
                        Marks.student_id == student.id,
                    ).first()
                    if mk:
                        results.append(
                            StudentMarksViewItem(
                                exam_id=ex.id,
                                exam_name=ex.name,
                                exam_type=ex.exam_type,
                                assessment_mode="SUMMATIVE",
                                exam_subject_id=es.id,
                                subject_id=es.subject_id,
                                subject_name=sub_name,
                                marks_obtained=mk.marks_obtained,
                                max_marks=mk.max_marks,
                                passing_marks=es.passing_marks or 35.0,
                                is_passed=mk.marks_obtained >= (es.passing_marks or 35.0),
                            )
                        )

        return StudentMarksViewResponse(total=len(results), items=results)