// src/services/users.ts
import api from './api';
import { AppUser, UserUpdatePayload } from '../types';

export const usersService = {
  async listUsers(params?: { skip?: number; limit?: number }): Promise<AppUser[]> {
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
};

export default usersService;

