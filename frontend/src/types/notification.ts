// src/types/notification.ts
export type NotificationType =
  | 'PUBLIC'
  | 'STAFF_ONLY'
  | 'CLASS_ONLY'
  | 'ONLY_FOR_CLASS'
  | 'ONLY_FOR_STUDENT';

export type NotificationCategory = 'PUBLIC' | 'CLASS' | 'CLASS_TEACHER' | 'STAFF';

export interface Notification {
  id: number;
  school_id?: number | null;
  sender_id?: number | null;
  sender_name?: string | null;
  sender_role?: string | null;
  title: string;
  message: string;
  notification_type: NotificationType | string;
  target_class_id?: number | null;
  target_class_name?: string | null;
  target_student_id?: number | null;
  target_student_name?: string | null;
  category?: NotificationCategory | string | null;
  user_id?: number | null;
  data?: Record<string, any>;
  is_read: boolean;
  reference_id?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface NotificationCreatePayload {
  title: string;
  message: string;
  notification_type: NotificationType;
  target_class_id?: number | null;
  target_student_id?: number | null;
  data?: Record<string, any>;
}

export interface NotificationListResponse {
  total: number;
  items: Notification[];
  unread_count: number;
}

export interface NotificationQueryParams {
  skip?: number;
  limit?: number;
  category?: NotificationCategory | string;
  notification_type?: string;
  unread_only?: boolean;
}

export interface StudentSummary {
  id: number;
  student_id: number;
  full_name: string;
  roll_number?: string;
}

export interface TeacherClassInfo {
  is_class_teacher: boolean;
  section_id?: number;
  section_name?: string;
  grade_name?: string;
  students: StudentSummary[];
}