// src/types/dashboard.ts
export interface SuperAdminDashboard {
  total_schools: number;
  total_principals: number;
  total_teachers: number;
  total_students: number;
  active_schools: number;
  recent_activity: any[];
  system_health: string;
  storage_usage: string;
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