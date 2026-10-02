// src/services/auth.ts
import api, { clearTokens, setTokens } from './api';
import { LoginRequest, TokenResponse, PasswordChangeResponse } from '../types/auth';

export const authService = {
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/login', credentials);
    return response.data;
  },

  /**
   * Exchange the refresh token for a fresh access + refresh pair.
   * Rotation: the old refresh token is invalidated server-side by this call.
   */
  async refresh(refreshToken: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    const data = response.data;
    if (data?.access_token) {
      setTokens(data.access_token, data.refresh_token);
    }
    return data;
  },

  /**
   * Revoke the session server-side and clear local tokens.
   *
   * The server treats an unknown/expired token as already-logged-out, so this
   * never fails the sign-out UX; local state is cleared either way.
   */
  async logout(refreshToken?: string | null): Promise<void> {
    try {
      await api.post('/auth/logout', { refresh_token: refreshToken ?? null });
    } catch {
      /* server-side revocation is best-effort; local logout always proceeds */
    } finally {
      clearTokens();
    }
  },

  async changePassword(
    current_password: string,
    new_password: string
  ): Promise<PasswordChangeResponse> {
    const response = await api.post<PasswordChangeResponse>('/auth/change-password', {
      current_password,
      new_password,
    });
    return response.data;
  },

  getCurrentUserFromStorage(): string | null {
    return localStorage.getItem('scholaris_access_token');
  },
};
