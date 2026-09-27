// src/types/reports.ts
/** Mirrors the backend schemas in app/schemas/reports.py. */

export interface RoleUserCounts {
  total: number;
  active: number;
  inactive: number;
}

export interface PlatformReportSummary {
  generated_at: string;
  window_start: string;
  window_end: string;
  school_count: number;
  active_school_count: number;
  user_count: number;
  active_user_count: number;
  inactive_user_count: number;
  /** Users attached to a school in scope. */
  school_user_count: number;
  /** Platform-level accounts (school_id is null), e.g. the Super Admin. */
  platform_user_count: number;
  users_by_role: Record<string, RoleUserCounts>;
  student_count: number;
  teacher_count: number;
  grade_count: number;
  section_count: number;
  subject_count: number;
  exam_count: number;
  published_exam_count: number;
  marks_record_count: number;
  report_card_count: number;
  attendance_record_count: number;
  audit_event_count: number;
}

export interface SchoolRollup {
  school_id: number;
  school_name: string;
  school_code?: string | null;
  is_active: boolean;
  student_count: number;
  teacher_count: number;
  staff_count: number;
  section_count: number;
  exam_count: number;
  report_card_count: number;
  attendance_record_count: number;
  last_audit_at?: string | null;
}

export interface PlatformReport {
  summary: PlatformReportSummary;
  schools: SchoolRollup[];
}
