// src/types/homework.ts
export interface Homework {
  id: number;
  title: string;
  description: string;
  academic_year_id: number;
  grade_id: number;
  section_id: number;
  subject_id: number;
  due_date: string;
  teacher_id: number;
  created_at: string;
  updated_at?: string;
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
  academic_year_id: number;
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