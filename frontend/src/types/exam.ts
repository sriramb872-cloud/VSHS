// src/types/exam.ts
export interface Exam {
  id: number;
  name: string;
  exam_type: string;
  academic_year_id: number;
  grade_id: number;
  section_id: number;
  subject_id: number;
  exam_date: string;
  start_time: string;
  end_time: string;
  maximum_marks: number;
  passing_marks: number;
  instructions?: string;
  teacher_id: number;
  created_at: string;
  updated_at?: string;
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
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  teacher_id?: number;
  start_date?: string;
  end_date?: string;
}

export interface ExamCreatePayload {
  name: string;
  exam_type: string;
  academic_year_id: number;
  grade_id: number;
  section_id: number;
  subject_id: number;
  exam_date: string;
  start_time: string;
  end_time: string;
  maximum_marks: number;
  passing_marks: number;
  instructions?: string;
}

export interface ExamUpdatePayload {
  name?: string;
  exam_type?: string;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  exam_date?: string;
  start_time?: string;
  end_time?: string;
  maximum_marks?: number;
  passing_marks?: number;
  instructions?: string;
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