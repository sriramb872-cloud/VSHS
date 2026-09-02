# app/services/marks.py
from datetime import datetime
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.exam_result import ExamResult
from app.models.marks import Marks
from app.models.section import Section
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
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

        # Check locked status
        if (exam.status or "").upper() == "PUBLISHED" and user_role != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Exam marks are locked because the exam has already been published",
            )

        # If teacher, verify teacher is assigned
        if user_role == "TEACHER":
            teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
            if not teacher:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher profile not found")

            # Check if teacher matches exam_subject.teacher_id or is assigned via teacher_subjects
            is_assigned = (exam_subject.teacher_id == teacher.id)
            if not is_assigned:
                ts = db.query(TeacherSubject).filter(
                    TeacherSubject.teacher_id == teacher.id,
                    TeacherSubject.section_id == exam.section_id,
                    TeacherSubject.subject_id == exam_subject.subject_id,
                ).first()
                if ts:
                    is_assigned = True

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
        )

    @staticmethod
    def submit_marks(db: Session, payload: MarksSubmitPayload, current_user: User) -> List[MarkResponse]:
        exam_subject = db.query(ExamSubject).filter(ExamSubject.id == payload.exam_subject_id).first()
        if not exam_subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam subject not found")

        exam = db.query(Exam).filter(Exam.id == exam_subject.exam_id).first()
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        MarksService._check_submission_permission(db, exam_subject, exam, current_user)

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
    ) -> Tuple[List[MarkResponse], int]:
        query = db.query(Marks)

        if school_id is not None:
            query = query.filter(Marks.school_id == school_id)
        if exam_subject_id is not None:
            query = query.filter(Marks.exam_subject_id == exam_subject_id)
        if exam_id is not None:
            query = query.join(ExamSubject, Marks.exam_subject_id == ExamSubject.id).filter(
                ExamSubject.exam_id == exam_id
            )
        if student_id is not None:
            query = query.filter(Marks.student_id == student_id)

        total = query.count()
        items = query.order_by(Marks.id.desc()).offset(skip).limit(limit).all()

        responses: List[MarkResponse] = []
        for item in items:
            student = db.query(Student).filter(Student.id == item.student_id).first()
            st_name = student.user.display_name if (student and student.user and hasattr(student.user, "display_name")) else f"Student #{item.student_id}"
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
                )
            )
        return responses, total

    @staticmethod
    def get_student_marks_view(db: Session, current_user: User) -> StudentMarksViewResponse:
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

        # Query only published exams
        published_exams = db.query(Exam).filter(Exam.status == "PUBLISHED").all()
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
