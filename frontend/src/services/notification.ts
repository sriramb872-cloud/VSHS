// src/services/notification.ts
import api from './api';
import {
  Notification,
  NotificationCreatePayload,
  NotificationListResponse,
  NotificationQueryParams,
  TeacherClassInfo,
} from '../types/notification';

export const notificationService = {
  async listNotifications(params?: NotificationQueryParams): Promise<NotificationListResponse> {
    const response = await api.get<NotificationListResponse>('/notifications/', { params });
    return response.data;
  },

  async createNotification(payload: NotificationCreatePayload): Promise<Notification> {
    const response = await api.post<Notification>('/notifications/', payload);
    return response.data;
  },

  async getTeacherClassInfo(): Promise<TeacherClassInfo> {
    const response = await api.get<TeacherClassInfo>('/notifications/teacher/class-info');
    return response.data;
  },

  async markAsRead(id: number): Promise<Notification> {
    const response = await api.patch<Notification>(`/notifications/${id}/read`);
    return response.data;
  },

  async markAllAsRead(): Promise<{ message: string; updated_count: number }> {
    const response = await api.post<{ message: string; updated_count: number }>('/notifications/read-all');
    return response.data;
  },

  async deleteNotification(id: number): Promise<void> {
    await api.delete(`/notifications/${id}`);
  },
};