// src/types/subscription.ts
/**
 * Types for the Subscription & Access Control module.
 *
 * Every shape here mirrors a backend schema 1:1 - nothing is invented in the
 * UI. Sources of truth:
 *
 *   app/schemas/subscription.py         access, schools, roles, users,
 *                                        overrides, bulk, metrics, /me views
 *   app/schemas/subscription_plan.py    plans
 *   app/schemas/subscription_payment.py payments
 *
 * Datetimes are naive-UTC ISO strings (`2026-10-02T09:16:37.708426`), the
 * house policy documented in `app/core/time_utils.py`.
 */

// ─── Vocabulary ─────────────────────────────────────────────────────────────

/** The only roles that can ever be charged (`BILLABLE_ROLES` on the server). */
export type BillableRole = 'PRINCIPAL' | 'TEACHER' | 'STUDENT';

/** Roles a plan can be written for (same set as `BILLABLE_ROLES`). */
export type PlanRole = BillableRole;

export type DurationUnit = 'DAY' | 'MONTH' | 'YEAR';

export type BillingInterval =
  | 'ONE_TIME'
  | 'WEEKLY'
  | 'MONTHLY'
  | 'QUARTERLY'
  | 'YEARLY'
  | 'CUSTOM';

/** `AccessStatus.status` - what the lock screen renders on. */
export type AccessStatusValue = 'ACTIVE' | 'PAYMENT_REQUIRED' | 'SUSPENDED';

/** Stored `subscriptions.status` rows. */
export type SubscriptionRowStatus = 'ACTIVE' | 'SUSPENDED' | 'CANCELLED' | 'EXPIRED';

/**
 * Why the resolver granted or denied. Reported verbatim by the API; the UI
 * only ever *explains* these, it never recomputes them.
 */
export type AccessReason =
  | 'SUPER_ADMIN'
  | 'NON_BILLABLE_ROLE'
  | 'SCHOOL_SUBSCRIPTIONS_DISABLED'
  | 'SCHOOL_FREE'
  | 'USER_FREE_OVERRIDE'
  | 'ADMIN_GRANT'
  | 'PAYMENT'
  | 'ROLE_PLAN'
  | 'INDIVIDUAL_OVERRIDE'
  | 'SCHOOL_OVERRIDE'
  | 'EXPIRED'
  | 'SUSPENDED'
  | 'CANCELLED'
  | 'NONE'
  | 'SCHOOL_CONTEXT_MISSING'
  | (string & {});

/** Per-user bucket in the school user listing. */
export type UserSubscriptionStatus = 'ACTIVE' | 'FREE' | 'EXPIRED' | 'SUSPENDED' | 'NONE';

/** School rollup status. */
export type SchoolSubscriptionStatus = 'DISABLED' | 'FREE' | 'ACTIVE' | 'PARTIAL' | 'NO_PLANS';

export type PaymentStatus = 'PENDING' | 'SUCCESS' | 'FAILED' | 'CANCELLED';

/** Simulated provider outcomes accepted by the development checkout. */
export type MockCheckoutOutcome = 'SUCCESS' | 'FAILED' | 'CANCELLED' | 'PENDING';

export type SubscriptionSource =
  | 'ADMIN_GRANT'
  | 'PAYMENT'
  | 'ROLE_PLAN'
  | 'INDIVIDUAL_OVERRIDE'
  | 'SCHOOL_OVERRIDE'
  | (string & {});

/** Server-side bulk action whitelist (`BULK_ACTIONS`). */
export type BulkAction =
  | 'FREE_UNTIL'
  | 'REMOVE_FREE'
  | 'ASSIGN_PLAN'
  | 'EXTEND'
  | 'SUSPEND'
  | 'RESTORE'
  | 'CANCEL';

// ─── Structured errors ──────────────────────────────────────────────────────

/**
 * The subscription domain is the ONLY place in this API where
 * `HTTPException.detail` is an object rather than a string.
 */
export interface SubscriptionErrorDetail {
  code: string;
  message: string;
  /** Present on a 403 from a gated router. */
  subscription_status?: AccessStatusValue;
  reason?: AccessReason;
  expires_at?: string | null;
}

/** Detail emitted for `403 SUBSCRIPTION_REQUIRED`. */
export interface SubscriptionRequiredDetail extends SubscriptionErrorDetail {
  code: 'SUBSCRIPTION_REQUIRED';
}

// ─── Access resolution ──────────────────────────────────────────────────────

export interface PlanBrief {
  id: number;
  name: string;
  price: number;
  currency: string;
  billing_interval: string;
  duration_value: number;
  duration_unit: string;
}

export interface AccessStatus {
  has_access: boolean;
  status: AccessStatusValue;
  reason: AccessReason;
  plan: PlanBrief | null;
  expires_at: string | null;
  subscription_id: number | null;
  subscriptions_enabled: boolean;
  school_free_until: string | null;
  user_free_until: string | null;
  school_id: number | null;
  role: string;
  mock_payments_enabled: boolean;
  payment_provider: string;
}

// ─── Plans ──────────────────────────────────────────────────────────────────

export interface SubscriptionPlan {
  id: number;
  school_id: number;
  role: PlanRole | string;
  name: string;
  description?: string | null;
  price: number;
  currency: string;
  billing_interval: string;
  duration_value: number;
  duration_unit: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionPlanListResponse {
  total: number;
  items: SubscriptionPlan[];
}

export interface SubscriptionPlanCreatePayload {
  role: PlanRole;
  name: string;
  description?: string;
  price: number;
  currency?: string;
  billing_interval?: BillingInterval;
  duration_value: number;
  duration_unit: DurationUnit;
  is_active?: boolean;
}

export interface SubscriptionPlanUpdatePayload {
  name?: string;
  description?: string;
  price?: number;
  currency?: string;
  billing_interval?: BillingInterval;
  duration_value?: number;
  duration_unit?: DurationUnit;
  is_active?: boolean;
}

// ─── Subscriptions (entitlements) ───────────────────────────────────────────

export interface Subscription {
  id: number;
  school_id: number;
  user_id: number;
  plan_id: number | null;
  plan: PlanBrief | null;
  status: SubscriptionRowStatus | string;
  start_at: string;
  end_at: string;
  source: SubscriptionSource;
  amount: number | null;
  currency: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionListResponse {
  total: number;
  items: Subscription[];
}

// ─── School settings ────────────────────────────────────────────────────────

export interface SchoolSettings {
  school_id: number;
  subscriptions_enabled: boolean;
  free_until: string | null;
  updated_at?: string | null;
}

/** `free_until: null` removes the window; omit the key to leave it alone. */
export interface SchoolSettingsUpdatePayload {
  subscriptions_enabled?: boolean;
  free_until?: string | null;
  reason?: string;
}

// ─── Individual overrides ───────────────────────────────────────────────────

export interface UserOverride {
  id: number;
  school_id: number;
  user_id: number;
  override_type: string;
  free_until: string | null;
  reason: string | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface UserOverrideCreatePayload {
  override_type?: string;
  free_until?: string | null;
  reason?: string;
}

export interface UserOverrideUpdatePayload {
  free_until?: string | null;
  reason?: string;
}

// ─── Listings (Super Admin) ─────────────────────────────────────────────────

export interface SchoolSubscriptionSummary {
  school_id: number;
  name: string;
  code: string | null;
  is_active: boolean | null;
  subscriptions_enabled: boolean;
  free_until: string | null;
  status: SchoolSubscriptionStatus;
  students: number;
  teachers: number;
  others: number;
  active_subscriptions: number;
  expired_subscriptions: number;
}

export interface SchoolSubscriptionListResponse {
  total: number;
  items: SchoolSubscriptionSummary[];
}

export interface RoleSummary {
  role: string;
  total_users: number;
  active_plans: number;
  active: number;
  free: number;
  expired: number;
  suspended: number;
  none: number;
}

export interface SchoolRolesResponse {
  school_id: number;
  school_name: string;
  subscriptions_enabled: boolean;
  free_until: string | null;
  roles: RoleSummary[];
}

export interface SchoolRoleDetailResponse extends SchoolRolesResponse {
  plans: SubscriptionPlan[];
}

export interface SchoolUserSubscriptionItem {
  user_id: number;
  display_name: string;
  mobile: string;
  role: string;
  subscription_status: UserSubscriptionStatus | string;
  plan_name: string | null;
  expires_at: string | null;
  override_free_until: string | null;
}

export interface SchoolUsersListResponse {
  total: number;
  items: SchoolUserSubscriptionItem[];
}

export interface SubscriptionAuditLog {
  id: number;
  school_id: number | null;
  user_id: number | null;
  admin_id: number | null;
  action: string;
  old_value: string | null;
  new_value: string | null;
  reason: string | null;
  created_at: string;
}

export interface UserSubscriptionDetail {
  user_id: number;
  display_name: string;
  role: string;
  mobile: string;
  school_id: number | null;
  school_name: string | null;
  access: AccessStatus;
  subscription: Subscription | null;
  override: UserOverride | null;
  history: Subscription[];
  payments: SubscriptionPayment[];
  audit: SubscriptionAuditLog[];
}

// ─── Manual operations ──────────────────────────────────────────────────────

export interface GrantSubscriptionPayload {
  plan_id: number;
  reason?: string;
}

export interface ExtendSubscriptionPayload {
  plan_id?: number;
  duration_value?: number;
  duration_unit?: DurationUnit;
  reason?: string;
}

export interface SubscriptionStatePayload {
  reason?: string;
}

// ─── Bulk ───────────────────────────────────────────────────────────────────

export interface BulkOperationPayload {
  action: BulkAction;
  user_ids: number[];
  free_until?: string | null;
  plan_id?: number;
  duration_value?: number;
  duration_unit?: DurationUnit;
  reason?: string;
}

export interface BulkOperationFailure {
  user_id: number;
  code: string;
  message: string;
}

export interface BulkOperationResponse {
  action: string;
  requested: number;
  succeeded: number[];
  failed: BulkOperationFailure[];
}

// ─── Metrics ────────────────────────────────────────────────────────────────

export interface SubscriptionMetrics {
  total_schools: number;
  subscriptions_enabled: number;
  schools_currently_free: number;
  active_user_subscriptions: number;
  expired_user_subscriptions: number;
  pending_payments: number;
  successful_payments: number;
  failed_payments: number;
}

// ─── Payments ───────────────────────────────────────────────────────────────

export interface SubscriptionPayment {
  id: number;
  school_id: number;
  user_id: number | null;
  plan_id: number | null;
  subscription_id: number | null;
  amount: number;
  currency: string;
  provider: string;
  provider_order_id: string | null;
  provider_payment_id: string | null;
  status: PaymentStatus | string;
  paid_at: string | null;
  created_at: string;
}

export interface SubscriptionPaymentListResponse {
  total: number;
  items: SubscriptionPayment[];
}

/**
 * `POST /subscription/payments` - the payment row plus everything the
 * browser needs to open Razorpay's hosted checkout.
 *
 * Superset of `SubscriptionPayment`, so the development mock flow keeps
 * working unchanged (these three are simply `null` there). Only PUBLIC
 * values: the key id is publishable, and the key secret / webhook secret
 * are never part of any response.
 */
export interface CheckoutResponse extends SubscriptionPayment {
  /** Plan price converted to whole paise (the unit Razorpay's API uses). */
  amount_paise: number | null;
  /** Publishable Razorpay key id (`rzp_...`). */
  razorpay_key_id: string | null;
  /** Order created server-side; Checkout.js charges exactly this order. */
  razorpay_order_id: string | null;
}

/** Exactly the two ids Razorpay's `handler` returns - nothing else. */
export interface RazorpayVerifyPayload {
  razorpay_payment_id: string;
  razorpay_signature: string;
}

// ─── User-facing /me views ──────────────────────────────────────────────────

export interface MeSubscription {
  user_id: number;
  role: string;
  school_id: number | null;
  school_name: string | null;
  access: AccessStatus;
  subscription: Subscription | null;
  override: UserOverride | null;
}

export interface MePlans {
  school_id: number | null;
  school_name: string | null;
  subscriptions_enabled: boolean;
  free_until: string | null;
  role: string;
  plans: SubscriptionPlan[];
  mock_payments_enabled: boolean;
  payment_provider: string;
}

// ─── Query params used by the screens ───────────────────────────────────────

export interface SchoolUsersQuery {
  role?: string;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
}
