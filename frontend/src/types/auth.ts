// src/types/auth.ts
export interface LoginRequest {
  mobile: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  /**
   * Rotating refresh token for `POST /auth/refresh`. Present on login and on
   * every refresh; stored (hashed server-side) so the session survives access
   * token expiry.
   */
  refresh_token?: string | null;
  /** Access token lifetime in seconds. */
  expires_in?: number | null;
  refresh_token_expires_in?: number | null;
  must_change_password?: boolean;
  role?: 'SUPER_ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'STUDENT';
  full_name?: string;
  user_id?: number;
  school_id?: number;
}

/** `POST /auth/change-password` and `POST /settings/user/change-password`. */
export interface PasswordChangeResponse extends TokenResponse {
  message: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token?: string | null;
}

export interface AuthenticatedUser {
  id: number;
  school_id: number | null;
  mobile: string;
  display_name: string;
  role: 'SUPER_ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'STUDENT';
  is_active: boolean;
  must_change_password?: boolean;
}

export interface AuthState {
  user: AuthenticatedUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}