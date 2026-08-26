# app/services/report_card.py
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.report_card import report_card as crud_report_card
from app.models.report_card import ReportCard

class ReportCardCalculationService:
    @staticmethod
    def calculate_converted_marks(obtained: float, raw_max: float, report_max: float) -> float:
        if raw_max <= 0:
            return 0.0
        return round((obtained / raw_max) * report_max, 2)

    @staticmethod
    def determine_grade(percentage: float) -> str:
        if percentage >= 90:
            return "A+"
        elif percentage >= 80:
            return "A"
        elif percentage >= 70:
            return "B+"
        elif percentage >= 60:
            return "B"
        elif percentage >= 50:
            return "C"
        elif percentage >= 40:
            return "D"
        else:
            return "F"

from app.schemas.report_card import (
    ReportCardResponse,
    SubjectReportCardDetail,
    SubjectAssessmentResult,
    AssessmentComponentScore,
)

class ReportCardService:
    @staticmethod
    def build_response(db: Session, report: ReportCard) -> ReportCardResponse:
        from app.models.student import Student
        from app.models.student_enrollment import StudentEnrollment
        from app.models.exam_result import ExamResult
        from app.models.exam import Exam
        from app.models.subject import Subject

        student = db.query(Student).filter(Student.id == report.student_id).first()
        student_name = student.user.name if (student and student.user and student.user.name) else f"Student {report.student_id}"

        enrollment = db.query(StudentEnrollment).filter(
            StudentEnrollment.student_id == report.student_id,
            StudentEnrollment.academic_year_id == report.academic_year_id
        ).first()
        grade_id = enrollment.grade_id if enrollment else 1
        section_id = enrollment.section_id if enrollment else 1

        results = db.query(ExamResult).join(Exam, ExamResult.exam_id == Exam.id).filter(
            ExamResult.student_id == report.student_id,
            Exam.academic_year_id == report.academic_year_id
        ).all()

        subject_map: Dict[int, Dict[str, Any]] = {}
        for res in results:
            sub_id = res.subject_id
            sub_name = res.subject.name if (res.subject and res.subject.name) else f"Subject {sub_id}"
            if sub_id not in subject_map:
                subject_map[sub_id] = {
                    "subject_id": sub_id,
                    "subject_name": sub_name,
                    "assessments": [],
                    "subject_total_obtained": 0.0,
                    "subject_total_maximum": 0.0,
                }

            exam_name = res.exam.name if (res.exam and res.exam.name) else "Exam"
            components = [
                AssessmentComponentScore(
                    component_name="Written Test",
                    raw_marks_obtained=res.written_test,
                    raw_maximum_marks=20.0,
                    report_maximum_marks=20.0,
                    converted_marks=res.written_test,
                ),
                AssessmentComponentScore(
                    component_name="Project",
                    raw_marks_obtained=res.project,
                    raw_maximum_marks=5.0,
                    report_maximum_marks=5.0,
                    converted_marks=res.project,
                ),
                AssessmentComponentScore(
                    component_name="Read Reflection",
                    raw_marks_obtained=res.read_reflection,
                    raw_maximum_marks=5.0,
                    report_maximum_marks=5.0,
                    converted_marks=res.read_reflection,
                ),
                AssessmentComponentScore(
                    component_name="Notebook",
                    raw_marks_obtained=res.notebook,
                    raw_maximum_marks=5.0,
                    report_maximum_marks=5.0,
                    converted_marks=res.notebook,
                ),
            ]
            total_obtained = round(res.written_test + res.project + res.read_reflection + res.notebook, 2)
            total_max = 40.0
            subject_map[sub_id]["assessments"].append(
                SubjectAssessmentResult(
                    assessment_name=exam_name,
                    components=components,
                    total_obtained=total_obtained,
                    total_maximum=total_max,
                )
            )
            subject_map[sub_id]["subject_total_obtained"] += total_obtained
            subject_map[sub_id]["subject_total_maximum"] += total_max

        subjects: List[SubjectReportCardDetail] = []
        grand_total_obtained = 0.0
        grand_total_maximum = 0.0
        for s_data in subject_map.values():
            s_tot_obt = s_data["subject_total_obtained"]
            s_tot_max = s_data["subject_total_maximum"]
            pct = round((s_tot_obt / s_tot_max * 100), 2) if s_tot_max > 0 else 0.0
            grd = ReportCardCalculationService.determine_grade(pct)
            subjects.append(
                SubjectReportCardDetail(
                    subject_id=s_data["subject_id"],
                    subject_name=s_data["subject_name"],
                    assessments=s_data["assessments"],
                    subject_total_obtained=s_tot_obt,
                    subject_total_maximum=s_tot_max,
                    percentage=pct,
                    grade=grd,
                )
            )
            grand_total_obtained += s_tot_obt
            grand_total_maximum += s_tot_max

        if not subjects:
            grand_total_obtained = report.total_marks
            grand_total_maximum = 100.0
            overall_pct = report.percentage
        else:
            overall_pct = round((grand_total_obtained / grand_total_maximum * 100), 2) if grand_total_maximum > 0 else report.percentage

        overall_grade = report.grade_letter or ReportCardCalculationService.determine_grade(overall_pct)
        overall_result = "Pass" if overall_pct >= 40.0 else "Fail"

        return ReportCardResponse(
            student_id=report.student_id,
            student_name=student_name,
            grade_id=grade_id,
            section_id=section_id,
            academic_year_id=report.academic_year_id,
            subjects=subjects,
            grand_total_obtained=grand_total_obtained,
            grand_total_maximum=grand_total_maximum,
            overall_percentage=overall_pct,
            overall_grade=overall_grade,
            overall_result=overall_result,
            teacher_remarks=report.remarks,
        )

    @staticmethod
    def get_report_card(
        db: Session, student_id: int, academic_year_id: int, school_id: Optional[int] = None
    ) -> ReportCardResponse:
        from app.models.student import Student
        report = crud_report_card.get_by_student_and_year(
            db, student_id=student_id, academic_year_id=academic_year_id
        )
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report card not found for the given student and academic year"
            )
        if school_id is not None:
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student or student.school_id != school_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: student does not belong to your school"
                )
        return ReportCardService.build_response(db, report)

    @staticmethod
    def list_report_cards(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        academic_year_id: Optional[int] = None,
        grade_id: Optional[int] = None,
        section_id: Optional[int] = None,
        student_id: Optional[int] = None,
        school_id: Optional[int] = None,
    ) -> Tuple[List[ReportCardResponse], int]:
        from app.models.student import Student
        if school_id is not None:
            query = db.query(ReportCard).join(Student, ReportCard.student_id == Student.id).filter(
                Student.school_id == school_id
            )
            if academic_year_id is not None:
                query = query.filter(ReportCard.academic_year_id == academic_year_id)
            if student_id is not None:
                query = query.filter(ReportCard.student_id == student_id)
            total = query.count()
            items = query.offset(skip).limit(limit).all()
            return [ReportCardService.build_response(db, r) for r in items], total

        items, total = crud_report_card.get_multi(
            db,
            skip=skip,
            limit=limit,
            academic_year_id=academic_year_id,
            grade_id=grade_id,
            section_id=section_id,
            student_id=student_id,
        )
        return [ReportCardService.build_response(db, r) for r in items], total

    @staticmethod
    def update_remarks(
        db: Session, student_id: int, academic_year_id: int, teacher_remarks: str
    ) -> ReportCardResponse:
        report = crud_report_card.get_by_student_and_year(
            db, student_id=student_id, academic_year_id=academic_year_id
        )
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report card not found"
            )
        updated = crud_report_card.update_remarks(db, db_obj=report, teacher_remarks=teacher_remarks)
        return ReportCardService.build_response(db, updated)

    """
SCHOLARIS ERP

Module:
Description:

TODO:
"""
