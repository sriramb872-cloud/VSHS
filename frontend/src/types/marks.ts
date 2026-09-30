// src/types/marks.ts
/**
 * Mirrors the backend `MarkResponse` schema (app/schemas/marks.py).
 * The `exam_*`/`subject_*`/`grade_id`/`section_id` context block is emitted by
 * `GET /marks/` for the principal Marks Monitor screen.
 */
export interface Mark {
  id: number;
  exam_subject_id: number;
  student_id: number;
  student_name?: string | null;
  roll_number?: string | null;
  marks_obtained: number;
  max_marks: number;
  remarks?: string | null;
  /**
   * Formative (4-component) exams persist their rows in `exam_results`.
   * `GET /marks/?exam_subject_id=..` returns them through the same shape so
   * the teacher's edit grid can be repopulated with the stored values.
   */
  written_test?: number | null;
  project?: number | null;
  read_reflection?: number | null;
  notebook?: number | null;
  created_at: string;
  updated_at?: string | null;
  exam_id?: number | null;
  exam_name?: string | null;
  subject_id?: number | null;
  subject_name?: string | null;
  grade_id?: number | null;
  section_id?: number | null;
  academic_year_id?: number | null;
  teacher_id?: number | null;
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