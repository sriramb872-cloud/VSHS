// src/types/homework.ts
/**
 * Mirrors the backend `HomeworkResponse` schema (app/schemas/homework.py).
 * The `*_name` fields are resolved server-side by `_enrich_with_names`.
 */
export interface Homework {
  id: number;
  title: string;
  description: string;
  academic_year_id: number | null;
  grade_id: number;
  section_id: number;
  subject_id: number;
  due_date: string;
  teacher_id: number;
  created_at: string;
  updated_at?: string | null;
  subject_name?: string | null;
  grade_name?: string | null;
  section_name?: string | null;
  teacher_name?: string | null;
}

export interface HomeworkListResponse {
  total: number;
  items: Homework[];
}

export interface HomeworkQueryParams {
  skip?: number;
  limit?: number;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  teacher_id?: number;
  due_date?: string;
}

export interface HomeworkCreatePayload {
  title: string;
  description: string;
  /** Optional on the backend (`Optional[int] = Field(None, ...)`). */
  academic_year_id?: number | null;
  grade_id: number;
  section_id: number;
  subject_id: number;
  due_date: string;
}

export interface HomeworkUpdatePayload {
  title?: string;
  description?: string;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  due_date?: string;
}