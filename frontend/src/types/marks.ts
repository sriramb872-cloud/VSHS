// src/types/marks.ts
export interface Mark {
  id: number;
  exam_id: number;
  student_id: number;
  marks_obtained: number;
  created_at: string;
  updated_at?: string;
}

export interface MarksListResponse {
  total: number;
  items: Mark[];
}

export interface StudentMarkInput {
  student_id: number;
  marks_obtained: number;
}

export interface MarksEntryPayload {
  exam_id: number;
  marks: StudentMarkInput[];
}

export interface MarksQueryParams {
  skip?: number;
  limit?: number;
  exam_id?: number;
  student_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  academic_year_id?: number;
  teacher_id?: number;
}