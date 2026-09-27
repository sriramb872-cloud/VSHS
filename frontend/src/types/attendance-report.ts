// src/types/attendance-report.ts
/**
 * Mirrors `GET /attendance/reports/summary`
 * (backend-python/app/routers/v1/attendance.py).
 *
 * `attendance_rate` is present / marked, where `marked` counts every recorded
 * status except VOID. The backend computes these values with SQL COUNTs; the
 * client only formats them.
 */

export type AttendanceReportStatus = 'PRESENT' | 'ABSENT' | 'LATE' | 'LEAVE' | 'VOID';

export interface AttendanceReportTotals {
  PRESENT: number;
  ABSENT: number;
  LATE: number;
  LEAVE: number;
  VOID: number;
  marked: number;
  students: number;
  attendance_rate: number;
}

export interface AttendanceReportDailyRow {
  date: string;
  marked: number;
  attendance_rate: number;
  PRESENT: number;
  ABSENT: number;
  LATE: number;
  LEAVE: number;
  VOID: number;
}

export interface AttendanceReportSectionRow {
  section_id: number;
  grade_id: number;
  grade_name?: string | null;
  section_name?: string | null;
  marked: number;
  attendance_rate: number;
  PRESENT: number;
  ABSENT: number;
  LATE: number;
  LEAVE: number;
  VOID: number;
  enrolled_students: number;
  students_with_records: number;
}

export interface AttendanceReportStudentRow {
  student_id: number;
  student_name?: string | null;
  admission_number?: string | null;
  roll_number?: string | null;
  section_id: number;
  grade_name?: string | null;
  section_name?: string | null;
  marked: number;
  attendance_rate: number;
  PRESENT: number;
  ABSENT: number;
  LATE: number;
  LEAVE: number;
  VOID: number;
}

export interface AttendanceReportFilters {
  start_date: string;
  end_date: string;
  grade_id: number | null;
  section_id: number | null;
}

export interface AttendanceReport {
  filters: AttendanceReportFilters;
  totals: AttendanceReportTotals;
  daily: AttendanceReportDailyRow[];
  sections: AttendanceReportSectionRow[];
  students: AttendanceReportStudentRow[];
}
