// src/services/auth.ts
import api from './api';
import { LoginRequest, TokenResponse } from '../types/auth';

export const authService = {
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/login', credentials);
    return response.data;
  },

  logout(): void {
    localStorage.removeItem('scholaris_access_token');
  },

  getCurrentUserFromStorage(): string | null {
    return localStorage.getItem('scholaris_access_token');
  }
};