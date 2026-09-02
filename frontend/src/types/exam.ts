// src/types/exam.ts
export interface ExamSubject {
  id: number;
  exam_id: number;
  subject_id: number;
  subject_name?: string;
  subject_code?: string;
  teacher_id?: number | null;
  teacher_name?: string | null;
  maximum_marks: number;
  passing_marks: number;
  is_marks_submitted: boolean;
  submitted_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface Exam {
  id: number;
  school_id?: number;
  name: string;
  exam_type: string;
  assessment_mode: 'FORMATIVE' | 'SUMMATIVE' | string;
  academic_year_id: number;
  grade_id: number;
  section_id: number;
  start_date: string;
  end_date: string;
  status: 'SCHEDULED' | 'MARKS_IN_PROGRESS' | 'PUBLISHED' | string;
  created_by_id?: number | null;
  created_at?: string;
  updated_at?: string;
  grade_name?: string;
  section_name?: string;
  exam_subjects?: ExamSubject[];
}

export interface ExamListResponse {
  total: number;
  items: Exam[];
}

export interface ExamQueryParams {
  skip?: number;
  limit?: number;
  academic_year_id?: number;
  exam_type?: string;
  assessment_mode?: string;
  status?: string;
  grade_id?: number;
  section_id?: number;
  teacher_id?: number;
  start_date?: string;
  end_date?: string;
}

export interface ExamCreatePayload {
  name: string;
  exam_type: string;
  assessment_mode: 'FORMATIVE' | 'SUMMATIVE';
  academic_year_id: number;
  grade_id: number;
  section_id: number;
  start_date: string;
  end_date: string;
  maximum_marks?: number;
  passing_marks?: number;
}

export interface ExamUpdatePayload {
  name?: string;
  exam_type?: string;
  assessment_mode?: string;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
}

export interface MarksStatusItem {
  exam_subject_id: number;
  subject_id: number;
  subject_name: string;
  teacher_id?: number | null;
  teacher_name?: string | null;
  maximum_marks: number;
  passing_marks: number;
  is_marks_submitted: boolean;
  submitted_at?: string | null;
}

export interface MarksStatusResponse {
  exam_id: number;
  exam_name: string;
  status: string;
  assessment_mode: string;
  total_subjects: number;
  submitted_subjects: number;
  is_all_submitted: boolean;
  items: MarksStatusItem[];
}

export interface ExamPublishResponse {
  message: string;
  exam_id: number;
  status: string;
  students_notified: number;
  missing_marks_zeroed: number;
}

export interface ExamTimetableEntry {
  id: string | number;
  exam_id: number;
  subject_id: number;
  subject_name: string;
  exam_date: string;
  start_time: string;
  end_time: string;
  maximum_marks: number;
  passing_marks: number;
}