// src/services/users.ts
import api from './api';
import { AppUser, UserUpdatePayload } from '../types';

export const usersService = {
  async listUsers(params?: { skip?: number; limit?: number; role?: string; search?: string; is_active?: string; school_id?: number }): Promise<AppUser[]> {
    const response = await api.get<AppUser[]>('/users', { params });
    return response.data;
  },

  async getMyUserProfile(): Promise<AppUser> {
    const response = await api.get<AppUser>('/users/me');
    return response.data;
  },

  async updateMyUserProfile(payload: UserUpdatePayload): Promise<AppUser> {
    const response = await api.patch<AppUser>('/users/me', payload);
    return response.data;
  },

  async getUser(id: number): Promise<AppUser> {
    const response = await api.get<AppUser>(`/users/${id}`);
    return response.data;
  },

  async updateUser(id: number, payload: UserUpdatePayload): Promise<AppUser> {
    const response = await api.patch<AppUser>(`/users/${id}`, payload);
    return response.data;
  },

  async resetUserPassword(id: number, password: string): Promise<void> {
    await api.post(`/users/${id}/reset-password`, { password });
  },

  async setUserActive(id: number, active: boolean): Promise<AppUser> {
    return this.updateUser(id, { is_active: active ? 'ACTIVE' : 'INACTIVE' } as UserUpdatePayload);
  },
};

export default usersService;

