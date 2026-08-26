// src/types/reportcard.ts
export interface AssessmentComponentScore {
  component_name: string;
  raw_marks_obtained: number;
  raw_maximum_marks: number;
  report_maximum_marks: number;
  converted_marks: number;
}

export interface SubjectAssessmentResult {
  assessment_name: string;
  components: AssessmentComponentScore[];
  total_obtained: number;
  total_maximum: number;
}

export interface SubjectReportCardDetail {
  subject_id: number;
  subject_name: string;
  assessments: SubjectAssessmentResult[];
  subject_total_obtained: number;
  subject_total_maximum: number;
  percentage: number;
  grade: string;
}

export interface ReportCardResponse {
  student_id: number;
  student_name: string;
  grade_id: number;
  section_id: number;
  academic_year_id: number;
  subjects: SubjectReportCardDetail[];
  grand_total_obtained: number;
  grand_total_maximum: number;
  overall_percentage: number;
  overall_grade: string;
  overall_result: 'Pass' | 'Fail';
  teacher_remarks?: string;
}

export interface ReportCardListResponse {
  total: number;
  items: ReportCardResponse[];
}

export interface ReportCardQueryParams {
  skip?: number;
  limit?: number;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  student_id?: number;
}