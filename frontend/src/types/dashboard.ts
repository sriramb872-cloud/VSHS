// src/types/dashboard.ts

/** Real measurement returned by `app/services/health.py`. */
export interface StorageDetail {
  media_path: string;
  media_available: boolean;
  used_bytes: number;
  file_count: number;
  used_human: string;
  disk?: {
    total_bytes: number;
    used_bytes: number;
    free_bytes: number;
    /** A genuine percentage: `shutil.disk_usage` reports the real capacity. */
    percent_used: number | null;
  } | null;
  label: string;
}

export interface SuperAdminDashboard {
  total_schools: number;
  total_principals: number;
  total_teachers: number;
  total_students: number;
  active_schools: number;
  recent_activity: any[];
  /** Measured per request: "Healthy" | "Degraded" | "Unavailable" | "Unknown". */
  system_health: string;
  system_health_detail?: string | null;
  database_latency_ms?: number | null;
  /** Measured media-directory usage, e.g. "12.4 MB in 3 files". */
  storage_usage: string;
  storage_detail?: StorageDetail | null;
}

export interface PrincipalDashboard {
  total_teachers: number;
  total_students: number;
  todays_attendance: Record<string, any>;
  upcoming_exams: any[];
  recent_homework: any[];
  announcements: any[];
  calendar_events: any[];
}

export interface TeacherDashboard {
  todays_timetable: any[];
  attendance_pending: boolean;
  homework_summary: any[];
  upcoming_exams: any[];
  announcements: any[];
  calendar_events: any[];
}

export interface StudentDashboard {
  todays_timetable: any[];
  attendance_percentage: number;
  pending_homework: any[];
  upcoming_exams: any[];
  latest_marks: any[];
  report_card_summary?: any;
  announcements: any[];
  calendar_events: any[];
  /** Slip tests for this student's own section, still scheduled. */
  upcoming_slip_tests?: number;
}

export interface ParentDashboard {
  child_attendance: Record<string, any>;
  homework: any[];
  upcoming_exams: any[];
  latest_report_card?: any;
  announcements: any[];
  calendar_events: any[];
  fee_summary: Record<string, any>;
  teacher_messages: any[];
}