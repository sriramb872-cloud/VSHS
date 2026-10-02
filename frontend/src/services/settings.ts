// src/services/settings.ts
import api, { setTokens } from './api';
import { PasswordChangeResponse } from '../types/auth';
import {
  PasswordChangePayload,
  PrincipalSettings,
  PrincipalSettingsUpdate,
  SuperAdminSettings,
  SuperAdminSettingsUpdate,
  UserProfileSettings,
  UserProfileSettingsUpdate,
} from '../types/settings';

export const settingsService = {
  async getSuperAdminSettings(): Promise<SuperAdminSettings> {
    const response = await api.get<SuperAdminSettings>('/settings/super-admin');
    return response.data;
  },

  async updateSuperAdminSettings(payload: SuperAdminSettingsUpdate): Promise<SuperAdminSettings> {
    const response = await api.put<SuperAdminSettings>('/settings/super-admin', payload);
    return response.data;
  },

  async getPrincipalSettings(): Promise<PrincipalSettings> {
    const response = await api.get<PrincipalSettings>('/settings/principal');
    return response.data;
  },

  async updatePrincipalSettings(payload: PrincipalSettingsUpdate): Promise<PrincipalSettings> {
    const response = await api.put<PrincipalSettings>('/settings/principal', payload);
    return response.data;
  },

  async getUserSettings(): Promise<UserProfileSettings> {
    const response = await api.get<UserProfileSettings>('/settings/user');
    return response.data;
  },

  async updateUserSettings(payload: UserProfileSettingsUpdate): Promise<UserProfileSettings> {
    const response = await api.put<UserProfileSettings>('/settings/user', payload);
    return response.data;
  },

  async changePassword(payload: PasswordChangePayload): Promise<PasswordChangeResponse> {
    const response = await api.post<PasswordChangeResponse>('/settings/user/change-password', payload);
    return response.data;
  },
};
