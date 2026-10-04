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

/* -------------------------------------------------------------------------
 * Password reset (forgot password)
 * ---------------------------------------------------------------------- */

/**
 * `POST /auth/forgot-password`.
 *
 * Deliberately generic: the server answers the same way whether the login ID
 * exists, has no email, or was unknown. `message` is the only user-facing
 * text the client may show for this call.
 */
export interface ForgotPasswordResponse {
  message: string;
  expires_in_minutes?: number;
}

/**
 * `POST /auth/verify-reset-otp`.
 *
 * `reset_token` is the ONLY place it is ever returned: single-use, short-lived
 * (10 min), spent by `/auth/reset-password`. Never persist it to storage.
 */
export interface VerifyResetOtpResponse {
  message: string;
  reset_token: string;
  expires_in_minutes?: number;
}

/** `POST /auth/reset-password`. */
export interface ResetPasswordResponse {
  message: string;
}

/**
 * Stable `detail.code` values the reset endpoints return. `detail` is always
 * `{ message, code }`, so the UI branches on `code`, never on prose.
 */
export type ResetErrorCode =
  | 'INVALID_OTP'
  | 'OTP_EXPIRED'
  | 'OTP_LOCKED'
  | 'ADMIN_RESET_REQUIRED'
  | 'RESET_TOKEN_INVALID'
  | 'WEAK_PASSWORD'
  | 'FORBIDDEN_ROLE'
  | 'ALREADY_HANDLED';

/** One row of `GET /admin/password-reset-requests`. */
export interface PasswordResetRequest {
  id: number;
  user_id: number;
  user_name: string;
  role: string;
  mobile: string | null;
  email: string | null;
  has_email: boolean;
  school_id: number | null;
  status: 'pending' | 'completed' | 'rejected';
  requested_at: string | null;
  handled_by: number | null;
  handled_by_name: string | null;
  handled_at: string | null;
}

/**
 * `POST /admin/users/{id}/reset-password`.
 *
 * `temporary_password` is plaintext and returned exactly once - it exists only
 * in this response, never stored or retrievable again. The client must show it
 * once and drop it from state after the admin acknowledges it.
 */
export interface AdminResetPasswordResponse {
  message: string;
  temporary_password: string;
  must_change_password: boolean;
  user: { id: number; display_name: string; role: string };
}