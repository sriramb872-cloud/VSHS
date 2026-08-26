// src/types/calendar.ts

export type StandardCalendarEventType =
  | 'Holiday'
  | 'School Event'
  | 'Examination'
  | 'Parent-Teacher Meeting'
  | 'Staff Meeting'
  | 'Meeting'
  | 'Academic Event'
  | 'Sports'
  | 'Cultural Event'
  | 'Result Day'
  | 'Other';

export type CalendarEventType = StandardCalendarEventType | string;

export interface CalendarEvent {
  id: number;
  school_id?: number;
  title: string;
  description?: string | null;
  event_type: string;
  start_date: string;
  end_date: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CalendarEventListResponse {
  total: number;
  items: CalendarEvent[];
}

export interface CalendarEventCreatePayload {
  title: string;
  description?: string;
  event_type: string;
  start_date: string;
  end_date?: string;
  is_active?: boolean;
}

export interface CalendarEventUpdatePayload {
  title?: string;
  description?: string;
  event_type?: string;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
}

export interface CalendarQueryParams {
  skip?: number;
  limit?: number;
  event_type?: string;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
  school_id?: number;
}