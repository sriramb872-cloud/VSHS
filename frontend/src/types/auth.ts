// src/types/auth.ts
export interface LoginRequest {
  mobile: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role?: 'SUPER_ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'STUDENT';
  full_name?: string;
  user_id?: number;
  school_id?: number;
}

export interface AuthenticatedUser {
  id: number;
  school_id: number | null;
  mobile: string;
  display_name: string;
  role: 'SUPER_ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'STUDENT';
  is_active: boolean;
}

export interface AuthState {
  user: AuthenticatedUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}