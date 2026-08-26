// src/services/calendar.ts
import api from './api';
import {
  CalendarEvent,
  CalendarEventListResponse,
  CalendarEventCreatePayload,
  CalendarEventUpdatePayload,
  CalendarQueryParams,
} from '../types/calendar';

export const calendarService = {
  async listEvents(params?: CalendarQueryParams): Promise<CalendarEventListResponse> {
    const response = await api.get<CalendarEventListResponse>('/calendar-events', { params });
    return response.data;
  },

  async getEvent(eventId: number): Promise<CalendarEvent> {
    const response = await api.get<CalendarEvent>(`/calendar-events/${eventId}`);
    return response.data;
  },

  async createEvent(payload: CalendarEventCreatePayload): Promise<CalendarEvent> {
    const response = await api.post<CalendarEvent>('/calendar-events', payload);
    return response.data;
  },

  async updateEvent(eventId: number, payload: CalendarEventUpdatePayload): Promise<CalendarEvent> {
    const response = await api.patch<CalendarEvent>(`/calendar-events/${eventId}`, payload);
    return response.data;
  },

  async deleteEvent(eventId: number): Promise<CalendarEvent> {
    const response = await api.delete<CalendarEvent>(`/calendar-events/${eventId}`);
    return response.data;
  },
};

export default calendarService;