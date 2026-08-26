// src/services/announcement.ts
import api from './api';
import {
  Announcement,
  AnnouncementCreatePayload,
  AnnouncementUpdatePayload,
  AnnouncementListResponse,
} from '../types';

export interface AnnouncementParams {
  audience?: string;
  grade_id?: number;
  section_id?: number;
  status?: string;
  skip?: number;
  limit?: number;
}

export const announcementService = {
  async listAnnouncements(params?: AnnouncementParams): Promise<AnnouncementListResponse> {
    const response = await api.get<AnnouncementListResponse>('/announcements/', { params });
    return response.data;
  },

  async getAnnouncement(id: number): Promise<Announcement> {
    const response = await api.get<Announcement>(`/announcements/${id}`);
    return response.data;
  },

  async createAnnouncement(payload: AnnouncementCreatePayload): Promise<Announcement> {
    const response = await api.post<Announcement>('/announcements/', payload);
    return response.data;
  },

  async updateAnnouncement(id: number, payload: AnnouncementUpdatePayload): Promise<Announcement> {
    const response = await api.put<Announcement>(`/announcements/${id}`, payload);
    return response.data;
  },

  async deleteAnnouncement(id: number): Promise<Announcement> {
    const response = await api.delete<Announcement>(`/announcements/${id}`);
    return response.data;
  },

  async publishAnnouncement(id: number): Promise<Announcement> {
    const response = await api.post<Announcement>(`/announcements/${id}/publish`);
    return response.data;
  },

  async archiveAnnouncement(id: number): Promise<Announcement> {
    const response = await api.post<Announcement>(`/announcements/${id}/archive`);
    return response.data;
  },
};