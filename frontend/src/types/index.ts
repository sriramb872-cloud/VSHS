// src/types/index.ts — Comprehensive V1 Domain Types

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
  mobile: string;
  email?: string | null;
  display_name: string;
  role: UserRole;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UserUpdatePayload {
  display_name?: string;
  email?: string;
  is_active?: boolean;
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

export interface PrincipalUpdatePayload {
  display_name?: string;
  full_name?: string;
  email?: string;
  mobile?: string;
  profile_photo?: string;
  employee_id?: string;
  joining_date?: string;
  is_active?: boolean;
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
  email?: string;
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
  email?: string;
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
export type AttendanceStatus = 'PRESENT' | 'ABSENT' | 'LATE' | 'EXCUSED';

export interface AttendanceRecord {
  id: number;
  student_id: number;
  section_id: number;
  date: string;
  status: AttendanceStatus | string;
}

export interface AttendanceMarkPayload {
  student_id: number;
  section_id: number;
  date: string;
  status: AttendanceStatus;
}

// ─── Exam ─────────────────────────────────────────────────────────────────────
export interface Exam {
  id: number;
  title?: string;
  name?: string;
  exam_type?: string;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  teacher_id?: number;
  start_date?: string;
  end_date?: string;
  date?: string;
  max_marks?: number;
  description?: string;
  status?: string;
}

export interface ExamCreatePayload {
  title: string;
  exam_type?: string;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  date?: string;
  max_marks?: number;
  description?: string;
}

export interface ExamUpdatePayload {
  title?: string;
  exam_type?: string;
  date?: string;
  max_marks?: number;
  description?: string;
  status?: string;
}

export interface ExamListResponse {
  total: number;
  items: Exam[];
}

// ─── Marks ────────────────────────────────────────────────────────────────────
export interface Mark {
  id: number;
  student_id: number;
  exam_id: number;
  subject_id?: number;
  grade_id?: number;
  section_id?: number;
  academic_year_id?: number;
  teacher_id?: number;
  marks_obtained?: number;
  max_marks?: number;
  grade?: string;
  remarks?: string;
}

export interface MarksEntryRow {
  student_id: number;
  marks_obtained: number;
  remarks?: string;
}

export interface MarksEntryCreatePayload {
  exam_id: number;
  entries: MarksEntryRow[];
}

export interface MarksListResponse {
  total: number;
  items: Mark[];
}

// ─── Homework ─────────────────────────────────────────────────────────────────
export interface Homework {
  id: number;
  title: string;
  description?: string;
  due_date?: string;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  teacher_id?: number;
  status?: string;
  created_at?: string;
}

export interface HomeworkCreatePayload {
  title: string;
  description?: string;
  due_date?: string;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
}

export interface HomeworkUpdatePayload {
  title?: string;
  description?: string;
  due_date?: string;
  status?: string;
}

export interface HomeworkListResponse {
  total: number;
  items: Homework[];
}

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
  content?: string;
  audience?: string;
  grade_id?: number;
  section_id?: number;
}

export interface AnnouncementUpdatePayload {
  title?: string;
  content?: string;
  audience?: string;
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
  section_id?: number;
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
export interface UserProfileSettings {
  id?: number;
  display_name?: string;
  email?: string;
  mobile?: string;
  profile_picture?: string | null;
}

export interface PasswordChangePayload {
  current_password: string;
  new_password: string;
  confirm_password?: string;
}

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
