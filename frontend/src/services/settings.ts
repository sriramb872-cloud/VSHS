// src/services/settings.ts
import api from './api';
import { UserProfileSettings, PasswordChangePayload } from '../types';

export const settingsService = {
  async getSuperAdminSettings(): Promise<Record<string, unknown>> {
    const response = await api.get<Record<string, unknown>>('/settings/super-admin');
    return response.data;
  },

  async updateSuperAdminSettings(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
    const response = await api.put<Record<string, unknown>>('/settings/super-admin', payload);
    return response.data;
  },

  async getPrincipalSettings(): Promise<Record<string, unknown>> {
    const response = await api.get<Record<string, unknown>>('/settings/principal');
    return response.data;
  },

  async updatePrincipalSettings(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
    const response = await api.put<Record<string, unknown>>('/settings/principal', payload);
    return response.data;
  },

  async getUserSettings(): Promise<UserProfileSettings> {
    const response = await api.get<UserProfileSettings>('/settings/user');
    return response.data;
  },

  async updateUserSettings(payload: Partial<UserProfileSettings>): Promise<UserProfileSettings> {
    const response = await api.put<UserProfileSettings>('/settings/user', payload);
    return response.data;
  },

  async changePassword(payload: PasswordChangePayload): Promise<{ message: string }> {
    const response = await api.post<{ message: string }>('/settings/user/change-password', payload);
    return response.data;
  },
};