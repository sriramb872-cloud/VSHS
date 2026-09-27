// src/types/index.ts — Comprehensive V1 Domain Types

import type { Homework } from './homework';
import type { Mark } from './marks';
import type { Exam } from './exam';

// ─── Auth ────────────────────────────────────────────────────────────────────
export type UserRole = 'SUPER_ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'STUDENT';

export interface AuthUser {
  id: number;
  school_id: number | null;
  mobile: string;
  display_name: string;
  role: UserRole;
  is_active: string | boolean;
  email?: string;
}

// ─── School ───────────────────────────────────────────────────────────────────
export interface School {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SchoolCreatePayload {
  name: string;
  code: string;
  is_active?: boolean;
}

export interface SchoolUpdatePayload {
  name?: string;
  code?: string;
  is_active?: boolean;
}

// ─── User ────────────────────────────────────────────────────────────────────
export interface AppUser {
  id: number;
  school_id: number | null;
  /**
   * Resolved server-side by `serialize_user` in the users router. `null` for
   * platform-level accounts (a Super Admin is not attached to a school).
   */
  school_name?: string | null;
  school_code?: string | null;
  mobile: string;
  email?: string | null;
  display_name: string;
  role: UserRole;
  /**
   * Account status. The backend column is `users.account_status`, a string
   * ("ACTIVE" / "INACTIVE"), and `serialize_user` returns it verbatim - it is
   * not a boolean.
   */
  is_active: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UserUpdatePayload {
  display_name?: string;
  email?: string;
  /** Account status; the backend coerces this to "ACTIVE"/"INACTIVE". */
  is_active?: string;
  mobile?: string;
}

// ─── Principal ───────────────────────────────────────────────────────────────
export interface Principal {
  id: number;
  school_id: number | null;
  school_name?: string | null;
  school_code?: string | null;
  employee_id?: string | null;
  joining_date?: string | null;
  mobile: string;
  email?: string | null;
  profile_photo?: string | null;
  display_name: string;
  full_name?: string;
  role?: UserRole;
  status?: string;
  is_active: boolean;
}

export interface PrincipalOnboardResponse extends Principal {
  must_change_password: boolean;
}

export interface PrincipalCreatePayload {
  school_id: number;
  full_name: string;
  mobile: string;
  email?: string;
  password: string;
}

export interface PrincipalUpdatePayload {
  display_name?: string;
  full_name?: string;
  email?: string;
  mobile?: string;
  profile_photo?: string;
  employee_id?: string;
  joining_date?: string;
  is_active?: boolean;
  status?: 'ACTIVE' | 'INACTIVE' | 'OFFBOARDED';
  school_id?: number;
}

// ─── Student ──────────────────────────────────────────────────────────────────
export interface Student {
  id: number;
  school_id: number;
  school_name?: string | null;
  school_code?: string | null;
  user_id: number;
  display_name?: string;
  full_name?: string;
  mobile?: string;
  /** Nullable: the backend column is `email = NULL` for most students. */
  email?: string | null;
  profile_photo?: string | null;
  admission_number?: string;
  student_id_formatted?: string;
  admission_date?: string;
  roll_number?: string;
  date_of_birth?: string;
  age?: number;
  gender?: string;
  blood_group?: string;
  address?: string;
  father_name?: string;
  father_mobile?: string;
  mother_name?: string;
  mother_mobile?: string;
  guardian_mobile?: string;
  grade_id?: number;
  grade_name?: string;
  section_id?: number;
  section_name?: string;
  academic_year_id?: number;
  academic_year_name?: string;
  enrollment_date?: string;
  attendance_percentage?: number;
  status?: string;
  student_status?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface StudentCreatePayload {
  school_id?: number;
  display_name?: string;
  full_name: string;
  email?: string;
  mobile?: string;
  profile_photo?: string;
  admission_number?: string;
  admission_date?: string;
  roll_number?: string;
  date_of_birth?: string;
  gender?: string;
  blood_group?: string;
  father_name?: string;
  father_mobile?: string;
  mother_name?: string;
  mother_mobile?: string;
  guardian_mobile?: string;
  address?: string;
  grade_id?: number;
  section_id?: number;
  academic_year_id?: number;
  password?: string;
}

export interface StudentOnboardResponse extends Student {
  temporary_password?: string;
}

export interface StudentUpdatePayload {
  display_name?: string;
  full_name?: string;
  email?: string;
  mobile?: string;
  profile_photo?: string;
  admission_number?: string;
  admission_date?: string;
  roll_number?: string;
  date_of_birth?: string;
  gender?: string;
  blood_group?: string;
  father_name?: string;
  father_mobile?: string;
  mother_name?: string;
  mother_mobile?: string;
  guardian_mobile?: string;
  address?: string;
  student_status?: string;
}

// ─── Teacher ──────────────────────────────────────────────────────────────────
export interface TeachingAssignment {
  grade_id: number;
  grade_name: string;
  section_id: number;
  section_name: string;
  subject_id: number;
  subject_name: string;
}

export interface Teacher {
  id: number;
  school_id: number;
  school_name?: string | null;
  school_code?: string | null;
  user_id: number;
  display_name?: string;
  full_name?: string;
  mobile?: string;
  /** Nullable: the backend column is `email = NULL` for many teachers. */
  email?: string | null;
  profile_photo?: string | null;
  employee_id?: string | null;
  role_type?: 'Class Teacher' | 'Subject Teacher' | string;
  qualification?: string | null;
  department?: string | null;
  specialization?: string | null;
  joining_date?: string | null;
  address?: string | null;
  gender?: string | null;
  date_of_birth?: string | null;
  status?: string;
  is_active?: boolean;
  assigned_subjects?: string[];
  assigned_sections?: string[];
  class_teacher_section?: {
    id: number;
    section_id: number;
    grade_id: number;
    grade_name: string;
    name: string;
    section_name: string;
  } | null;
  teaching_assignments?: TeachingAssignment[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TeacherOnboardResponse extends Teacher {
  temporary_password?: string;
}

export interface TeacherCreatePayload {
  school_id?: number;
  display_name?: string;
  full_name: string;
  email?: string;
  mobile?: string;
  profile_photo?: string;
  employee_id?: string;
  qualification?: string;
  department?: string;
  specialization?: string;
  joining_date?: string;
  address?: string;
  password?: string;
}

export interface TeacherUpdatePayload {
  display_name?: string;
  full_name?: string;
  email?: string;
  mobile?: string;
  profile_photo?: string;
  employee_id?: string;
  qualification?: string;
  department?: string;
  specialization?: string;
  joining_date?: string;
  address?: string;
  is_active?: boolean;
  status?: string;
}

// ─── Grade ────────────────────────────────────────────────────────────────────
export interface Grade {
  id: number;
  school_id: number;
  name: string;
  display_order?: number;
}

export interface GradeCreatePayload {
  name: string;
  display_order?: number;
}

export interface GradeUpdatePayload {
  name?: string;
  display_order?: number;
}

// ─── Section ──────────────────────────────────────────────────────────────────
export interface Section {
  id: number;
  school_id: number;
  grade_id: number;
  name: string;
  grade_name?: string;
  class_teacher_id?: number | null;
  class_teacher_name?: string | null;
}

export interface SectionCreatePayload {
  grade_id: number;
  name: string;
}

export interface SectionUpdatePayload {
  name?: string;
  grade_id?: number;
}

// ─── Subject ──────────────────────────────────────────────────────────────────
export interface Subject {
  id: number;
  school_id: number;
  name: string;
  code?: string;
}

export interface SubjectCreatePayload {
  name: string;
  code?: string;
}

export interface SubjectUpdatePayload {
  name?: string;
  code?: string;
}

// ─── Academic Year ────────────────────────────────────────────────────────────
export interface AcademicYear {
  id: number;
  school_id: number;
  name: string;
  is_active: boolean;
  start_date?: string | null;
  end_date?: string | null;
}

export interface AcademicYearCreatePayload {
  name: string;
  is_active?: boolean;
  start_date?: string;
  end_date?: string;
}

export interface AcademicYearUpdatePayload {
  name?: string;
  is_active?: boolean;
  start_date?: string;
  end_date?: string;
}

// ─── Attendance ───────────────────────────────────────────────────────────────
/**
 * Mirrors the `attendance_records.status` MySQL ENUM declared in
 * `backend-python/app/models/attendance.py` and validated by
 * `AttendanceStatus` in `app/models/attendance_record.py`.
 *
 * This union used to be `PRESENT | ABSENT | LATE | EXCUSED`. `EXCUSED` is not a
 * member of the database ENUM (it was rejected by MySQL with a 500), while
 * `LEAVE` and `VOID` - which the attendance screens actually offer - were
 * missing from the type.
 */
export type AttendanceStatus = 'PRESENT' | 'ABSENT' | 'LATE' | 'LEAVE' | 'VOID';

export interface AttendanceRecord {
  id: number;
  student_id: number;
  section_id: number;
  date: string;
  status: AttendanceStatus | string;
  remarks?: string | null;
  recorded_by?: number | null;
}

export interface AttendanceMarkPayload {
  student_id: number;
  section_id: number;
  date: string;
  status: AttendanceStatus;
  /** Persisted on the `remarks` column; accepted by POST /attendance. */
  remarks?: string | null;
}

// ─── Exam ─────────────────────────────────────────────────────────────────────
/**
 * `Exam` and its payloads are canonically defined in ./exam (mirroring the
 * backend `ExamResponse` / `ExamCreate` / `ExamUpdate` schemas). The copies
 * that used to live here were a looser, drifting duplicate.
 */
export type {
  Exam,
  ExamCreatePayload,
  ExamUpdatePayload,
  ExamListResponse,
  ExamSubject,
  ExamSubjectSchedule,
  MarksStatusItem,
  MarksStatusResponse,
  ExamPublishResponse,
} from './exam';

// ─── Marks ────────────────────────────────────────────────────────────────────
/**
 * `Mark` is canonically defined in ./marks (it mirrors the backend
 * `MarkResponse` schema). It used to be duplicated here with a stale, narrower
 * shape, which is why the monitor screens could not type-check the context
 * fields the API already returns.
 */
export type { Mark, MarksListResponse } from './marks';

// ─── Homework ─────────────────────────────────────────────────────────────────
/**
 * `Homework` is canonically defined in ./homework (it mirrors the backend
 * `HomeworkResponse` schema). It used to be duplicated here with a slightly
 * different shape, so the same object had two incompatible types depending on
 * which module imported it.
 */
export type {
  Homework,
  HomeworkListResponse,
  HomeworkCreatePayload,
  HomeworkUpdatePayload,
} from './homework';

// ─── Announcement ─────────────────────────────────────────────────────────────
export interface Announcement {
  id: number;
  title: string;
  content?: string;
  description?: string;
  message?: string;
  audience?: string;
  grade_id?: number;
  section_id?: number;
  status?: string;
  created_at?: string;
  published_at?: string;
}

export interface AnnouncementCreatePayload {
  title: string;
  description: string;
  content?: string;
  audience: string;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  priority?: string;
  publish_date: string;
  expiry_date?: string;
  status?: string;
}

export interface AnnouncementUpdatePayload {
  title?: string;
  description?: string;
  content?: string;
  audience?: string;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  priority?: string;
  publish_date?: string;
  expiry_date?: string;
  status?: string;
}

export interface AnnouncementListResponse {
  total: number;
  items: Announcement[];
}

// ─── Notification ─────────────────────────────────────────────────────────────
export interface Notification {
  id: number;
  title: string;
  message?: string;
  body?: string;
  is_read?: boolean;
  read_at?: string | null;
  created_at?: string;
  notification_type?: string;
}

export interface NotificationListResponse {
  total: number;
  items: Notification[];
  unread_count: number;
}

// ─── Timetable ────────────────────────────────────────────────────────────────
export interface TimetableSlot {
  id: number;
  academic_year_id?: number;
  grade_id?: number;
  grade_name?: string;
  section_id?: number;
  section_name?: string;
  subject_id?: number;
  teacher_id?: number;
  day_of_week?: string | number;
  start_time?: string;
  end_time?: string;
  subject_name?: string;
  teacher_name?: string;
  period_number?: number;
}

export interface TimetableListResponse {
  total: number;
  items: TimetableSlot[];
}

// ─── Report Card ──────────────────────────────────────────────────────────────
export interface ReportCard {
  id?: number;
  student_id: number;
  academic_year_id: number;
  total_marks?: number;
  obtained_marks?: number;
  percentage?: number;
  grade?: string;
  rank?: number;
  teacher_remarks?: string;
  principal_remarks?: string;
  attendance_percentage?: number;
  subjects?: ReportCardSubject[];
}

export interface ReportCardSubject {
  subject_id: number;
  subject_name?: string;
  marks_obtained?: number;
  max_marks?: number;
  grade?: string;
}

export interface ReportCardListResponse {
  total: number;
  items: ReportCard[];
}

// ─── Enrollment ───────────────────────────────────────────────────────────────
export interface StudentEnrollment {
  id: number;
  enrollment_id?: number;
  student_id: number;
  student_name?: string;
  full_name?: string;
  admission_number?: string;
  roll_number?: string;
  gender?: string;
  grade_id?: number;
  grade_name?: string;
  section_id?: number;
  section_name?: string;
  academic_year_id?: number;
  academic_year_name?: string;
  attendance_percentage?: number;
  created_at?: string;
}

export interface EnrollmentCreatePayload {
  student_id: number;
  academic_year_id: number;
  section_id: number;
  roll_number?: string;
}

// ─── Settings ─────────────────────────────────────────────────────────────────
/**
 * Settings types are canonically defined in ./settings, which mirrors the
 * backend schemas (app/schemas/settings.py). The copies that used to live here
 * described a flat `display_name`/`email` profile shape that no endpoint ever
 * returned - `PUT /settings/user` actually takes `profile_information` and
 * `notification_preferences`.
 */
export type {
  SuperAdminSettings,
  PrincipalSettings,
  UserProfileSettings,
  UserProfileSettingsUpdate,
  PasswordChangePayload,
} from './settings';

// ─── Dashboard ────────────────────────────────────────────────────────────────
export interface SuperAdminDashboard {
  total_schools: number;
  active_schools: number;
  total_principals: number;
  total_teachers: number;
  total_students: number;
  system_health?: string;
  storage_usage?: string;
}

export interface PrincipalDashboard {
  total_teachers: number;
  total_students: number;
  upcoming_exams?: Exam[];
  announcements?: Announcement[];
  attendance_today?: number;
}

export interface TeacherDashboard {
  todays_timetable: TimetableSlot[];
  attendance_pending: boolean;
  homework_summary: Homework[];
  announcements: Announcement[];
}

export interface StudentDashboard {
  todays_timetable?: TimetableSlot[];
  homework?: Homework[];
  upcoming_exams?: Exam[];
  announcements?: Announcement[];
  attendance_percentage?: number;
}

// ─── Grade & Teacher Subjects ──────────────────────────────────────────────────
export interface GradeSubject {
  id: number;
  grade_id: number;
  subject_id: number;
}
export interface GradeSubjectCreatePayload {
  grade_id: number;
  subject_id: number;
}

export interface TeacherSubject {
  id: number;
  teacher_id: number;
  subject_id: number;
  grade_id: number;
  section_id: number;
  school_id: number;
  created_at: string;
  updated_at: string;
}
export interface TeacherSubjectCreatePayload {
  teacher_id: number;
  subject_id: number;
  grade_id: number;
  section_id: number;
  school_id: number;
}
