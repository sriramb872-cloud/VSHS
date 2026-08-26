// src/types/announcement.ts
export type AnnouncementAudience = 'School-Wide' | 'Teachers' | 'Students' | 'Parents' | 'Grade' | 'Section';
export type AnnouncementPriority = 'Low' | 'Normal' | 'High' | 'Urgent';
export type AnnouncementStatus = 'Draft' | 'Published' | 'Archived';

export interface Announcement {
  id: number;
  title: string;
  description: string;
  audience: AnnouncementAudience;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  priority: AnnouncementPriority;
  publish_date: string;
  expiry_date?: string;
  status: AnnouncementStatus;
  author_id: number;
  created_at: string;
  updated_at?: string;
}

export interface AnnouncementListResponse {
  total: number;
  items: Announcement[];
}

export interface AnnouncementCreatePayload {
  title: string;
  description: string;
  audience: AnnouncementAudience;
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  priority?: AnnouncementPriority;
  publish_date: string;
  expiry_date?: string;
  status?: AnnouncementStatus;
}

export interface AnnouncementQueryParams {
  skip?: number;
  limit?: number;
  audience?: AnnouncementAudience;
  grade_id?: number;
  section_id?: number;
  status?: AnnouncementStatus;
}