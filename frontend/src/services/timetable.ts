// src/services/timetable.ts
import api from './api';
import { TimetableSlot, TimetableListResponse } from '../types';

export interface TimetableParams {
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  teacher_id?: number;
  skip?: number;
  limit?: number;
}

export interface TimetableCreatePayload {
  grade_id: number;
  subject_id: number;
  teacher_id: number;
  start_time: string;
  end_time: string;
  day_of_week?: string;
  academic_year_id?: number;
  section_id?: number;
  period_number?: number;
  room_number?: string;
}

export interface TimetableUpdatePayload {
  grade_id?: number;
  subject_id?: number;
  teacher_id?: number;
  day_of_week?: string;
  start_time?: string;
  end_time?: string;
  period_number?: number;
  room_number?: string;
}


export const timetableService = {
  async listTimetables(params?: TimetableParams): Promise<TimetableListResponse> {
    const response = await api.get<TimetableListResponse>('/timetables/', { params });
    return response.data;
  },

  async getTimetable(id: number): Promise<TimetableSlot> {
    const response = await api.get<TimetableSlot>(`/timetables/${id}`);
    return response.data;
  },

  async createTimetable(payload: TimetableCreatePayload): Promise<TimetableSlot> {
    const response = await api.post<TimetableSlot>('/timetables/', payload);
    return response.data;
  },

  async updateTimetable(id: number, payload: TimetableUpdatePayload): Promise<TimetableSlot> {
    const response = await api.put<TimetableSlot>(`/timetables/${id}`, payload);
    return response.data;
  },

  async deleteTimetable(id: number): Promise<TimetableSlot> {
    const response = await api.delete<TimetableSlot>(`/timetables/${id}`);
    return response.data;
  },
};