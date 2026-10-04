// src/services/passwordReset.ts
//
// Client for the "forgot password" flow (Flow A: self-service OTP) and the
// admin-assisted flow (Flow B: staff-issued temporary password).
//
// Security notes for anyone touching this file:
//   * the OTP and the reset token are short-lived secrets - never write them
//     to localStorage/sessionStorage, never log them;
//   * `/auth/forgot-password` always returns the same generic message, so the
//     UI must never branch on "user found / not found" at this step;
//   * errors arrive as `detail: { message, code }` - branch on `code`.
import api from './api';
import {
  AdminResetPasswordResponse,
  ForgotPasswordResponse,
  PasswordResetRequest,
  ResetErrorCode,
  ResetPasswordResponse,
  VerifyResetOtpResponse,
} from '../types/auth';

/** Message shown when the account can't receive a code (backend constant). */
export const ADMIN_HELP_MESSAGE =
  'Please contact your Principal or class teacher to reset your password.';

/** Normalized view of a failed reset call. */
export interface ResetError {
  message: string;
  code: ResetErrorCode | null;
  /** HTTP status, or 0 when the request never reached the server. */
  status: number;
  /** True when the device/server could not be reached at all. */
  offline: boolean;
}

/**
 * Normalize any thrown value into a `ResetError`.
 *
 * FastAPI sends `detail` as a string (simple errors), an array (validation)
 * or an object (these endpoints). Rendering the raw value in JSX crashes
 * React, so everything is flattened to `{ message, code }` here.
 */
export function toResetError(err: unknown, fallback: string): ResetError {
  const e = err as {
    response?: { status?: number; data?: { detail?: unknown; error?: unknown } };
    request?: unknown;
    code?: string;
    message?: string;
  };

  const status = e?.response?.status ?? 0;
  // No response at all => the request never reached the server.
  const offline = !e?.response && !!e?.request;

  const detail = e?.response?.data?.detail;

  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const d = detail as { message?: unknown; code?: unknown };
    return {
      message: typeof d.message === 'string' && d.message ? d.message : fallback,
      code: typeof d.code === 'string' ? (d.code as ResetErrorCode) : null,
      status,
      offline,
    };
  }

  if (typeof detail === 'string' && detail) {
    return { message: detail, code: null, status, offline };
  }

  if (Array.isArray(detail)) {
    const msg = detail
      .map((d) => (typeof d === 'string' ? d : (d as { msg?: string })?.msg ?? ''))
      .filter(Boolean)
      .join(', ');
    return { message: msg || fallback, code: null, status, offline };
  }

  // slowapi's 429 body is `{ error: "Rate limit exceeded: ..." }`.
  if (status === 429) {
    return {
      message: 'Too many attempts. Please wait a while and try again.',
      code: null,
      status,
      offline,
    };
  }

  if (offline) {
    return { message: 'You appear to be offline. Check your connection and try again.', code: null, status, offline };
  }

  return { message: fallback, code: null, status, offline };
}

export const passwordResetService = {
  /** Step 1. Response is identical for every input - never branch on it. */
  async forgotPassword(loginId: string): Promise<ForgotPasswordResponse> {
    const response = await api.post<ForgotPasswordResponse>('/auth/forgot-password', {
      login_id: loginId,
    });
    return response.data;
  },

  /** Step 2. Returns the single-use reset token on success. */
  async verifyOtp(loginId: string, otp: string): Promise<VerifyResetOtpResponse> {
    const response = await api.post<VerifyResetOtpResponse>('/auth/verify-reset-otp', {
      login_id: loginId,
      otp,
    });
    return response.data;
  },

  /** Step 3. Spends the token; it cannot be replayed afterwards. */
  async resetPassword(resetToken: string, newPassword: string): Promise<ResetPasswordResponse> {
    const response = await api.post<ResetPasswordResponse>('/auth/reset-password', {
      reset_token: resetToken,
      new_password: newPassword,
    });
    return response.data;
  },

  /* --- Flow B: admin-assisted ------------------------------------------ */

  async listRequests(
    status: 'pending' | 'completed' | 'rejected' | 'all' = 'pending'
  ): Promise<PasswordResetRequest[]> {
    const response = await api.get<PasswordResetRequest[]>('/admin/password-reset-requests', {
      params: { status },
    });
    return response.data;
  },

  async rejectRequest(requestId: number): Promise<{ message: string }> {
    const response = await api.post<{ message: string }>(
      `/admin/password-reset-requests/${requestId}/reject`
    );
    return response.data;
  },

  /**
   * Issue a one-time temporary password. The plaintext exists only in this
   * response - show it once to the admin and let it leave state afterwards.
   */
  async adminResetPassword(userId: number): Promise<AdminResetPasswordResponse> {
    const response = await api.post<AdminResetPasswordResponse>(
      `/admin/users/${userId}/reset-password`
    );
    return response.data;
  },
};

export default passwordResetService;
