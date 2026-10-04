// src/services/subscriptions.ts
/**
 * Subscription & Access Control API client.
 *
 * Thin, typed wrappers over `/api/v1/subscription*`. No entitlement logic
 * lives here: `has_access` and every other decision come from the single
 * authoritative resolver on the server (`SubscriptionService.get_access_status`).
 *
 * Errors returned by this domain carry a structured `detail` object
 * (`{ code, message, ... }`) instead of a plain string - see
 * `src/helpers/errorMessage.ts` and `isSubscriptionRequired` below.
 */
import api from './api';
import type {
  AccessStatus,
  BulkOperationPayload,
  BulkOperationResponse,
  CheckoutResponse,
  ExtendSubscriptionPayload,
  GrantSubscriptionPayload,
  MePlans,
  MeSubscription,
  MockCheckoutOutcome,
  RazorpayVerifyPayload,
  SchoolRolesResponse,
  SchoolRoleDetailResponse,
  SchoolSettings,
  SchoolSettingsUpdatePayload,
  SchoolSubscriptionListResponse,
  SchoolSubscriptionSummary,
  SchoolUsersListResponse,
  SchoolUsersQuery,
  Subscription,
  SubscriptionListResponse,
  SubscriptionMetrics,
  SubscriptionPayment,
  SubscriptionPaymentListResponse,
  SubscriptionPlan,
  SubscriptionPlanCreatePayload,
  SubscriptionPlanListResponse,
  SubscriptionPlanUpdatePayload,
  SubscriptionStatePayload,
  UserOverride,
  UserOverrideCreatePayload,
  UserOverrideUpdatePayload,
  UserSubscriptionDetail,
} from '../types/subscription';

const BASE = '/subscription';

/* -------------------------------------------------------------------------
 * Structured error helpers
 * ---------------------------------------------------------------------- */

interface SubscriptionLikeError {
  response?: { status?: number; data?: { detail?: unknown } };
}

/**
 * `true` when the server rejected a request because the caller has no
 * entitlement right now (`403` + `detail.code === 'SUBSCRIPTION_REQUIRED'`).
 *
 * Used by the gate so a billing lock can never be confused with an ordinary
 * authorization failure (403 without that code) or with a validation error.
 */
export function isSubscriptionRequired(error: unknown): boolean {
  const err = error as SubscriptionLikeError;
  if (err?.response?.status !== 403) return false;
  const detail = err.response.data?.detail;
  return (
    typeof detail === 'object' &&
    detail !== null &&
    (detail as { code?: unknown }).code === 'SUBSCRIPTION_REQUIRED'
  );
}

/** Machine-readable code of a structured subscription error, if any. */
export function subscriptionErrorCode(error: unknown): string | null {
  const detail = (error as SubscriptionLikeError)?.response?.data?.detail;
  if (typeof detail === 'object' && detail !== null) {
    const code = (detail as { code?: unknown }).code;
    if (typeof code === 'string') return code;
  }
  return null;
}

export const subscriptionsService = {
  /* -----------------------------------------------------------------------
   * User-facing (never blocked by the lock screen)
   * -------------------------------------------------------------------- */

  async me(): Promise<MeSubscription> {
    const response = await api.get<MeSubscription>(`${BASE}/me`);
    return response.data;
  },

  async myPlans(): Promise<MePlans> {
    const response = await api.get<MePlans>(`${BASE}/me/plans`);
    return response.data;
  },

  async myHistory(): Promise<SubscriptionListResponse> {
    const response = await api.get<SubscriptionListResponse>(`${BASE}/me/history`);
    return response.data;
  },

  async myPayments(): Promise<SubscriptionPaymentListResponse> {
    const response = await api.get<SubscriptionPaymentListResponse>(`${BASE}/me/payments`);
    return response.data;
  },

  /** One-shot access probe used by the gate and the lock screen. */
  async access(): Promise<AccessStatus> {
    const data = await this.me();
    return data.access;
  },

  /* -----------------------------------------------------------------------
   * Payments
   *
   * `PAYMENT_PROVIDER` decides what happens next:
   *   INTERNAL - development only: the client reports a simulated outcome and
   *              the server verifies its signed payload.
   *   RAZORPAY - the browser opens Checkout.js, then reports ONLY the ids
   *              Razorpay handed it; verification, amount and currency are
   *              the server's job (see `verifyPayment`).
   * -------------------------------------------------------------------- */

  async createCheckout(planId: number): Promise<CheckoutResponse> {
    const response = await api.post<CheckoutResponse>(`${BASE}/payments`, {
      plan_id: planId,
    });
    return response.data;
  },

  /**
   * Report Razorpay's checkout result to the server for verification.
   *
   * The client sends ONLY the payment id and the signature Razorpay
   * produced. The order id, the expected amount and the expected currency
   * are read from the payment row on the server, and the payment itself is
   * fetched back from Razorpay before anything is activated - so this call
   * can never claim a success that did not happen.
   */
  async verifyPayment(
    paymentId: number,
    payload: RazorpayVerifyPayload
  ): Promise<SubscriptionPayment> {
    const response = await api.post<SubscriptionPayment>(
      `${BASE}/payments/${paymentId}/verify`,
      payload
    );
    return response.data;
  },

  /**
   * Re-read one of the caller's own payments (404 for anyone else's row).
   *
   * Used while a UPI payment is still waiting for approval in the customer's
   * UPI app: the browser callback and the webhook are both asynchronous, so
   * the UI polls this instead of guessing.
   */
  async getPayment(paymentId: number): Promise<SubscriptionPayment> {
    const response = await api.get<SubscriptionPayment>(
      `${BASE}/payments/${paymentId}`
    );
    return response.data;
  },

  async completeMockCheckout(
    paymentId: number,
    outcome: MockCheckoutOutcome
  ): Promise<SubscriptionPayment> {
    const response = await api.post<SubscriptionPayment>(
      `${BASE}/payments/${paymentId}/mock/complete`,
      { outcome }
    );
    return response.data;
  },

  async cancelPayment(paymentId: number): Promise<SubscriptionPayment> {
    const response = await api.post<SubscriptionPayment>(
      `${BASE}/payments/${paymentId}/cancel`
    );
    return response.data;
  },

  /* -----------------------------------------------------------------------
   * Super Admin: schools
   * -------------------------------------------------------------------- */

  async listSchools(params?: {
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<SchoolSubscriptionListResponse> {
    const response = await api.get<SchoolSubscriptionListResponse>(`${BASE}/schools`, {
      params,
    });
    return response.data;
  },

  async getSchool(schoolId: number): Promise<SchoolSubscriptionSummary> {
    const response = await api.get<SchoolSubscriptionSummary>(`${BASE}/schools/${schoolId}`);
    return response.data;
  },

  async getSchoolSettings(schoolId: number): Promise<SchoolSettings> {
    const response = await api.get<SchoolSettings>(`${BASE}/schools/${schoolId}/settings`);
    return response.data;
  },

  async updateSchoolSettings(
    schoolId: number,
    payload: SchoolSettingsUpdatePayload
  ): Promise<SchoolSettings> {
    const response = await api.patch<SchoolSettings>(
      `${BASE}/schools/${schoolId}/settings`,
      payload
    );
    return response.data;
  },

  async getSchoolRoles(schoolId: number): Promise<SchoolRolesResponse> {
    const response = await api.get<SchoolRolesResponse>(`${BASE}/schools/${schoolId}/roles`);
    return response.data;
  },

  async getSchoolRole(schoolId: number, role: string): Promise<SchoolRoleDetailResponse> {
    const response = await api.get<SchoolRoleDetailResponse>(
      `${BASE}/schools/${schoolId}/roles/${role}`
    );
    return response.data;
  },

  async listSchoolUsers(
    schoolId: number,
    query?: SchoolUsersQuery
  ): Promise<SchoolUsersListResponse> {
    const response = await api.get<SchoolUsersListResponse>(
      `${BASE}/schools/${schoolId}/users`,
      { params: query }
    );
    return response.data;
  },

  async bulkOperation(
    schoolId: number,
    payload: BulkOperationPayload
  ): Promise<BulkOperationResponse> {
    const response = await api.post<BulkOperationResponse>(
      `${BASE}/schools/${schoolId}/bulk`,
      payload
    );
    return response.data;
  },

  /* -----------------------------------------------------------------------
   * Super Admin: plans
   * -------------------------------------------------------------------- */

  async listPlans(): Promise<SubscriptionPlanListResponse> {
    const response = await api.get<SubscriptionPlanListResponse>(`${BASE}/plans`);
    return response.data;
  },

  async createPlan(
    schoolId: number,
    payload: SubscriptionPlanCreatePayload
  ): Promise<SubscriptionPlan> {
    const response = await api.post<SubscriptionPlan>(
      `${BASE}/schools/${schoolId}/plans`,
      payload
    );
    return response.data;
  },

  async updatePlan(
    planId: number,
    payload: SubscriptionPlanUpdatePayload
  ): Promise<SubscriptionPlan> {
    const response = await api.patch<SubscriptionPlan>(`${BASE}/plans/${planId}`, payload);
    return response.data;
  },

  async deactivatePlan(planId: number): Promise<SubscriptionPlan> {
    const response = await api.post<SubscriptionPlan>(`${BASE}/plans/${planId}/deactivate`);
    return response.data;
  },

  /* -----------------------------------------------------------------------
   * Super Admin: per-user operations
   * -------------------------------------------------------------------- */

  async getUserDetail(userId: number): Promise<UserSubscriptionDetail> {
    const response = await api.get<UserSubscriptionDetail>(`${BASE}/users/${userId}`);
    return response.data;
  },

  async grant(userId: number, payload: GrantSubscriptionPayload): Promise<Subscription> {
    const response = await api.post<Subscription>(`${BASE}/users/${userId}/grant`, payload);
    return response.data;
  },

  async extend(userId: number, payload: ExtendSubscriptionPayload): Promise<Subscription> {
    const response = await api.post<Subscription>(`${BASE}/users/${userId}/extend`, payload);
    return response.data;
  },

  async cancel(userId: number, payload?: SubscriptionStatePayload): Promise<Subscription> {
    const response = await api.post<Subscription>(`${BASE}/users/${userId}/cancel`, payload ?? {});
    return response.data;
  },

  async suspend(userId: number, payload?: SubscriptionStatePayload): Promise<Subscription> {
    const response = await api.post<Subscription>(`${BASE}/users/${userId}/suspend`, payload ?? {});
    return response.data;
  },

  async restore(userId: number, payload?: SubscriptionStatePayload): Promise<Subscription> {
    const response = await api.post<Subscription>(`${BASE}/users/${userId}/restore`, payload ?? {});
    return response.data;
  },

  async createOverride(userId: number, payload: UserOverrideCreatePayload): Promise<UserOverride> {
    const response = await api.post<UserOverride>(`${BASE}/users/${userId}/override`, payload);
    return response.data;
  },

  async updateOverride(userId: number, payload: UserOverrideUpdatePayload): Promise<UserOverride> {
    const response = await api.patch<UserOverride>(`${BASE}/users/${userId}/override`, payload);
    return response.data;
  },

  async removeOverride(userId: number): Promise<void> {
    await api.delete(`${BASE}/users/${userId}/override`);
  },

  /* -----------------------------------------------------------------------
   * Super Admin: metrics (real aggregates only)
   * -------------------------------------------------------------------- */

  async metrics(): Promise<SubscriptionMetrics> {
    const response = await api.get<SubscriptionMetrics>(`${BASE}/metrics`);
    return response.data;
  },
};

export default subscriptionsService;
