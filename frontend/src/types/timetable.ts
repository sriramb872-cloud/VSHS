// src/types/timetable.ts
export interface TimetableEntry {
  id: number;
  day_of_week: string;
  period_number: number;
  start_time: string;
  end_time: string;
  subject_id: number;
  teacher_id: number;
  classroom?: string;
}

export interface Timetable {
  id: number;
  academic_year_id: number;
  grade_id: number;
  section_id: number;
  entries: TimetableEntry[];
}

export interface TimetableListResponse {
  total: number;
  items: Timetable[];
}

export interface TimetableEntryInput {
  day_of_week: string;
  period_number: number;
  start_time: string;
  end_time: string;
  subject_id: number;
  teacher_id: number;
  classroom?: string;
}

export interface TimetableCreatePayload {
  academic_year_id: number;
  grade_id: number;
  section_id: number;
  entries: TimetableEntryInput[];
}

export interface TimetableCopyPayload {
  target_section_id: number;
  target_grade_id?: number;
}

export interface TimetableQueryParams {
  skip?: number;
  limit?: number;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  teacher_id?: number;
}