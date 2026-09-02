# app/services/exam.py
from datetime import datetime, date
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.crud.exam import exam as crud_exam
from app.crud.notification import notification as crud_notification
from app.schemas.exam import (
    ExamCreate,
    ExamUpdate,
    ExamResponse,
    ExamSubjectResponse,
    MarksStatusResponse,
    MarksStatusItem,
    ExamPublishResponse,
)
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.exam_result import ExamResult
from app.models.marks import Marks
from app.models.grade_subject import GradeSubject
from app.models.teacher_subject import TeacherSubject
from app.models.section import Section
from app.models.teacher import Teacher
from app.models.student_enrollment import StudentEnrollment
from app.models.user import User


class ExamService:
    @staticmethod
    def _format_exam_response(db_obj: Exam) -> ExamResponse:
        grade_name = db_obj.grade.name if (db_obj.grade and hasattr(db_obj.grade, "name")) else (db_obj.grade.grade_name if hasattr(db_obj.grade, "grade_name") else f"Grade {db_obj.grade_id}")
        section_name = db_obj.section.name if (db_obj.section and hasattr(db_obj.section, "name")) else (db_obj.section.section_name if hasattr(db_obj.section, "section_name") else f"Section {db_obj.section_id}")

        subject_responses: List[ExamSubjectResponse] = []
        if db_obj.exam_subjects:
            for es in db_obj.exam_subjects:
                sub_name = es.subject.name if (es.subject and hasattr(es.subject, "name")) else (es.subject.subject_name if hasattr(es.subject, "subject_name") else f"Subject #{es.subject_id}")
                sub_code = getattr(es.subject, "code", None) or getattr(es.subject, "subject_code", None)
                teacher_name = None
                if es.teacher and es.teacher.user:
                    teacher_name = getattr(es.teacher.user, "display_name", None) or getattr(es.teacher.user, "full_name", None)

                subject_responses.append(
                    ExamSubjectResponse(
                        id=es.id,
                        exam_id=es.exam_id,
                        subject_id=es.subject_id,
                        subject_name=sub_name,
                        subject_code=sub_code,
                        teacher_id=es.teacher_id,
                        teacher_name=teacher_name,
                        maximum_marks=es.maximum_marks,
                        passing_marks=es.passing_marks,
                        is_marks_submitted=es.is_marks_submitted,
                        submitted_at=es.submitted_at,
                        created_at=es.created_at,
                        updated_at=es.updated_at,
                    )
                )

        return ExamResponse(
            id=db_obj.id,
            school_id=db_obj.school_id,
            academic_year_id=db_obj.academic_year_id,
            grade_id=db_obj.grade_id,
            section_id=db_obj.section_id,
            name=db_obj.name,
            exam_type=db_obj.exam_type,
            assessment_mode=db_obj.assessment_mode or "FORMATIVE",
            start_date=db_obj.start_date,
            end_date=db_obj.end_date,
            status=db_obj.status or "SCHEDULED",
            created_by_id=db_obj.created_by_id,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at,
            grade_name=grade_name,
            section_name=section_name,
            exam_subjects=subject_responses,
        )

    @staticmethod
    def get_exam(db: Session, exam_id: int, school_id: Optional[int] = None) -> Optional[ExamResponse]:
        db_obj = crud_exam.get(db, exam_id=exam_id)
        if not db_obj:
            return None
        if school_id is not None and db_obj.school_id != school_id:
            return None
        return ExamService._format_exam_response(db_obj)

    @staticmethod
    def list_exams(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        school_id: Optional[int] = None,
        academic_year_id: Optional[int] = None,
        exam_type: Optional[str] = None,
        assessment_mode: Optional[str] = None,
        status: Optional[str] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[List[ExamResponse], int]:
        items, total = crud_exam.get_multi(
            db,
            skip=skip,
            limit=limit,
            school_id=school_id,
            academic_year_id=academic_year_id,
            exam_type=exam_type,
            assessment_mode=assessment_mode,
            status=status,
            grade_id=grade_id,
            section_id=section_id,
            teacher_id=teacher_id,
            start_date=start_date,
            end_date=end_date,
        )
        return [ExamService._format_exam_response(item) for item in items], total

    @staticmethod
    def create_exam(
        db: Session,
        obj_in: ExamCreate,
        school_id: int,
        created_by_id: Optional[int] = None,
    ) -> ExamResponse:
        # Create exam master record
        db_exam = crud_exam.create(
            db,
            obj_in=obj_in,
            school_id=school_id,
            created_by_id=created_by_id,
        )

        # Auto-create exam_subjects rows from grade_subjects for this grade
        grade_subjects = db.query(GradeSubject).filter(GradeSubject.grade_id == obj_in.grade_id).all()

        is_formative = (obj_in.assessment_mode or "FORMATIVE").upper() == "FORMATIVE"
        default_max = obj_in.maximum_marks if obj_in.maximum_marks is not None else (20.0 if is_formative else 100.0)
        default_pass = obj_in.passing_marks if obj_in.passing_marks is not None else (7.0 if is_formative else 35.0)

        for gs in grade_subjects:
            # Check teacher_subjects for section assignment
            ts = db.query(TeacherSubject).filter(
                TeacherSubject.school_id == school_id,
                TeacherSubject.section_id == obj_in.section_id,
                TeacherSubject.subject_id == gs.subject_id,
            ).first()

            assigned_teacher_id = ts.teacher_id if ts else gs.teacher_id

            exam_subject = ExamSubject(
                exam_id=db_exam.id,
                subject_id=gs.subject_id,
                teacher_id=assigned_teacher_id,
                maximum_marks=default_max,
                passing_marks=default_pass,
                is_marks_submitted=False,
            )
            db.add(exam_subject)

        db.commit()
        db.refresh(db_exam)
        return ExamService._format_exam_response(crud_exam.get(db, exam_id=db_exam.id))

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
        updated = crud_exam.update(db, db_obj=db_obj, obj_in=obj_in)
        return ExamService._format_exam_response(crud_exam.get(db, exam_id=updated.id))

    @staticmethod
    def delete_exam(db: Session, exam_id: int, school_id: Optional[int] = None) -> bool:
        db_obj = crud_exam.get(db, exam_id=exam_id)
        if not db_obj:
            return False
        if school_id is not None and db_obj.school_id != school_id:
            return False
        crud_exam.remove(db, id=exam_id)
        return True

    @staticmethod
    def get_exam_subjects(
        db: Session,
        exam_id: int,
        teacher_id: Optional[int] = None,
        school_id: Optional[int] = None,
    ) -> List[ExamSubjectResponse]:
        exam_obj = crud_exam.get(db, exam_id=exam_id)
        if not exam_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        if school_id is not None and exam_obj.school_id != school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

        query = db.query(ExamSubject).filter(ExamSubject.exam_id == exam_id)
        if teacher_id is not None:
            query = query.filter(ExamSubject.teacher_id == teacher_id)

        items = query.all()
        results: List[ExamSubjectResponse] = []
        for es in items:
            sub_name = es.subject.name if (es.subject and hasattr(es.subject, "name")) else (es.subject.subject_name if hasattr(es.subject, "subject_name") else f"Subject #{es.subject_id}")
            sub_code = getattr(es.subject, "code", None) or getattr(es.subject, "subject_code", None)
            teacher_name = None
            if es.teacher and es.teacher.user:
                teacher_name = getattr(es.teacher.user, "display_name", None) or getattr(es.teacher.user, "full_name", None)

            results.append(
                ExamSubjectResponse(
                    id=es.id,
                    exam_id=es.exam_id,
                    subject_id=es.subject_id,
                    subject_name=sub_name,
                    subject_code=sub_code,
                    teacher_id=es.teacher_id,
                    teacher_name=teacher_name,
                    maximum_marks=es.maximum_marks,
                    passing_marks=es.passing_marks,
                    is_marks_submitted=es.is_marks_submitted,
                    submitted_at=es.submitted_at,
                    created_at=es.created_at,
                    updated_at=es.updated_at,
                )
            )
        return results

    @staticmethod
    def get_marks_status(db: Session, exam_id: int, current_user: User) -> MarksStatusResponse:
        exam_obj = crud_exam.get(db, exam_id=exam_id)
        if not exam_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        user_role = str(current_user.role).upper()
        if user_role not in ("SUPER_ADMIN", "PRINCIPAL"):
            # Check if teacher is class teacher for this section
            teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
            if not teacher:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher profile not found")
            section = db.query(Section).filter(Section.id == exam_obj.section_id).first()
            if not section or section.class_teacher_id != teacher.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the Class Teacher, Principal, or Super Admin can view marks readiness status",
                )

        exam_subjects = db.query(ExamSubject).filter(ExamSubject.exam_id == exam_id).all()
        items: List[MarksStatusItem] = []
        submitted_count = 0

        for es in exam_subjects:
            sub_name = es.subject.name if (es.subject and hasattr(es.subject, "name")) else (es.subject.subject_name if hasattr(es.subject, "subject_name") else f"Subject #{es.subject_id}")
            teacher_name = None
            if es.teacher and es.teacher.user:
                teacher_name = getattr(es.teacher.user, "display_name", None) or getattr(es.teacher.user, "full_name", None)

            if es.is_marks_submitted:
                submitted_count += 1

            items.append(
                MarksStatusItem(
                    exam_subject_id=es.id,
                    subject_id=es.subject_id,
                    subject_name=sub_name,
                    teacher_id=es.teacher_id,
                    teacher_name=teacher_name,
                    maximum_marks=es.maximum_marks,
                    passing_marks=es.passing_marks,
                    is_marks_submitted=es.is_marks_submitted,
                    submitted_at=es.submitted_at,
                )
            )

        total_subjects = len(exam_subjects)
        return MarksStatusResponse(
            exam_id=exam_obj.id,
            exam_name=exam_obj.name,
            status=exam_obj.status or "SCHEDULED",
            assessment_mode=exam_obj.assessment_mode or "FORMATIVE",
            total_subjects=total_subjects,
            submitted_subjects=submitted_count,
            is_all_submitted=(submitted_count == total_subjects and total_subjects > 0),
            items=items,
        )

    @staticmethod
    def publish_exam(db: Session, exam_id: int, current_user: User) -> ExamPublishResponse:
        exam_obj = crud_exam.get(db, exam_id=exam_id)
        if not exam_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        user_role = str(current_user.role).upper()
        if user_role not in ("SUPER_ADMIN", "PRINCIPAL"):
            teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
            if not teacher:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher profile not found")
            section = db.query(Section).filter(Section.id == exam_obj.section_id).first()
            if not section or section.class_teacher_id != teacher.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the Section's Class Teacher or Principal can publish exam marks",
                )

        if (exam_obj.status or "").upper() == "PUBLISHED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam is already published")

        # Fetch all enrolled students for this section
        enrollments = db.query(StudentEnrollment).filter(
            StudentEnrollment.section_id == exam_obj.section_id,
            StudentEnrollment.academic_year_id == exam_obj.academic_year_id,
        ).all()
        student_ids = [en.student_id for en in enrollments]

        exam_subjects = db.query(ExamSubject).filter(ExamSubject.exam_id == exam_id).all()
        is_formative = (exam_obj.assessment_mode or "FORMATIVE").upper() == "FORMATIVE"
        missing_zeroed = 0

        now = datetime.utcnow()

        for es in exam_subjects:
            if is_formative:
                # Fill missing ExamResult
                for st_id in student_ids:
                    existing = db.query(ExamResult).filter(
                        ExamResult.exam_id == exam_id,
                        ExamResult.student_id == st_id,
                        ExamResult.subject_id == es.subject_id,
                    ).first()
                    if not existing:
                        db.add(
                            ExamResult(
                                exam_id=exam_id,
                                student_id=st_id,
                                subject_id=es.subject_id,
                                written_test=0.0,
                                project=0.0,
                                read_reflection=0.0,
                                notebook=0.0,
                            )
                        )
                        missing_zeroed += 1
            else:
                # Fill missing Marks
                for st_id in student_ids:
                    existing = db.query(Marks).filter(
                        Marks.exam_subject_id == es.id,
                        Marks.student_id == st_id,
                    ).first()
                    if not existing:
                        db.add(
                            Marks(
                                exam_subject_id=es.id,
                                student_id=st_id,
                                school_id=exam_obj.school_id,
                                marks_obtained=0.0,
                                max_marks=es.maximum_marks,
                                entered_by_id=current_user.id,
                            )
                        )
                        missing_zeroed += 1

            es.is_marks_submitted = True
            if not es.submitted_at:
                es.submitted_at = now

        exam_obj.status = "PUBLISHED"
        exam_obj.updated_at = now
        db.commit()

        # Fire notification to all students in section
        crud_notification.create(
            db,
            title="Exam Results Published",
            message=f"Your {exam_obj.name} results are out.",
            notification_type="ONLY_FOR_CLASS",
            sender_id=current_user.id,
            sender_role=user_role,
            school_id=exam_obj.school_id,
            category="CLASS",
            target_class_id=exam_obj.section_id,
        )

        return ExamPublishResponse(
            message=f"Exam '{exam_obj.name}' successfully published.",
            exam_id=exam_obj.id,
            status="PUBLISHED",
            students_notified=len(student_ids),
            missing_marks_zeroed=missing_zeroed,
        )