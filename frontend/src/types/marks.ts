// src/types/marks.ts
export interface Mark {
  id: number;
  exam_subject_id: number;
  student_id: number;
  student_name?: string;
  roll_number?: string;
  marks_obtained: number;
  max_marks: number;
  remarks?: string;
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
  remarks?: string;
}

export interface MarksSubmitPayload {
  exam_subject_id: number;
  marks: StudentMarkInput[];
}

export type MarksEntryCreatePayload = MarksSubmitPayload;

export interface StudentFormativeMarkInput {
  student_id: number;
  written_test: number;
  project: number;
  read_reflection: number;
  notebook: number;
}

export interface FormativeMarksSubmitPayload {
  exam_subject_id: number;
  marks: StudentFormativeMarkInput[];
}

export interface MarksQueryParams {
  skip?: number;
  limit?: number;
  exam_id?: number;
  exam_subject_id?: number;
  student_id?: number;
}

export interface StudentMarksViewItem {
  exam_id: number;
  exam_name: string;
  exam_type: string;
  assessment_mode: string;
  exam_subject_id: number;
  subject_id: number;
  subject_name: string;
  marks_obtained: number;
  max_marks: number;
  passing_marks: number;
  is_passed: boolean;
  components?: {
    written_test?: number;
    project?: number;
    read_reflection?: number;
    notebook?: number;
  };
}

export interface StudentMarksViewResponse {
  total: number;
  items: StudentMarksViewItem[];
}