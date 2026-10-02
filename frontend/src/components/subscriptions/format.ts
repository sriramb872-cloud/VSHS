// src/components/subscriptions/format.ts
/**
 * Presentation helpers for subscription data.
 *
 * All timestamps come from the API as *naive-UTC* ISO strings (the house
 * policy in `backend-python/app/core/time_utils.py`). JavaScript would parse
 * `2026-10-02T09:16:37` as local time, which silently shifts every expiry by
 * the client's UTC offset - so `parseUtc` pins them to UTC explicitly.
 *
 * Nothing here derives entitlement: "do I have access" is always the server's
 * answer (`AccessStatus.has_access`).
 */
import type { AccessReason, AccessStatus } from '../../types/subscription';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** Parse a backend datetime string as UTC. Returns null for junk. */
export function parseUtc(value: string | null | undefined): Date | null {
  if (!value) return null;
  const iso = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`;
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

const pad = (n: number): string => String(n).padStart(2, '0');

/** `02 Oct 2026` */
export function formatDate(value: string | null | undefined): string {
  const date = parseUtc(value);
  if (!date) return '—';
  return `${pad(date.getUTCDate())} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

/** `02 Oct 2026, 14:46 UTC` */
export function formatDateTime(value: string | null | undefined): string {
  const date = parseUtc(value);
  if (!date) return '—';
  return `${formatDate(value)}, ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`;
}

/**
 * Whole days left until `value`, rounded UP so a subscription that expires in
 * 5 hours still says "expires today" rather than silently reading as 0 days.
 * Null when `value` is missing; negative once it has passed.
 */
export function daysRemaining(value: string | null | undefined): number | null {
  const date = parseUtc(value);
  if (!date) return null;
  const diff = date.getTime() - Date.now();
  return Math.ceil(diff / 86_400_000);
}

/** `1 day` / `12 days`, pluralised from a day count. */
export function pluralDays(days: number): string {
  return `${days} ${days === 1 ? 'day' : 'days'}`;
}

/** `₹100.00` / `USD 12.50` - symbols only where the code is unambiguous. */
export function formatPrice(price: number, currency?: string | null): string {
  const code = (currency || 'INR').toUpperCase();
  const value = Number(price ?? 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (code === 'INR') return `₹${value}`;
  if (code === 'USD') return `$${value}`;
  return `${code} ${value}`;
}

/** `30 days`, `1 month`, `1 year` - matches the plan's own units. */
export function formatDuration(value: number, unit: string): string {
  const u = (unit || '').toUpperCase();
  const label = u === 'DAY' ? (value === 1 ? 'day' : 'days')
    : u === 'MONTH' ? (value === 1 ? 'month' : 'months')
    : u === 'YEAR' ? (value === 1 ? 'year' : 'years')
    : u.toLowerCase();
  return `${value} ${label}`;
}

/** Interval label, e.g. `Billed monthly`. */
export function formatBillingInterval(interval: string | null | undefined): string {
  switch ((interval || '').toUpperCase()) {
    case 'ONE_TIME':
      return 'One-time';
    case 'WEEKLY':
      return 'Billed weekly';
    case 'MONTHLY':
      return 'Billed monthly';
    case 'QUARTERLY':
      return 'Billed quarterly';
    case 'YEARLY':
      return 'Billed yearly';
    default:
      return 'Custom interval';
  }
}

/** Human copy for each resolver reason (never used to re-decide anything). */
export function reasonLabel(reason: AccessReason): string {
  switch (reason) {
    case 'SUPER_ADMIN':
      return 'Platform administrator';
    case 'NON_BILLABLE_ROLE':
      return 'Not a billable role';
    case 'SCHOOL_SUBSCRIPTIONS_DISABLED':
      return 'Subscriptions are switched off for this school';
    case 'SCHOOL_FREE':
      return 'School-wide free period';
    case 'USER_FREE_OVERRIDE':
      return 'Free access granted to this user';
    case 'PAYMENT':
      return 'Paid subscription';
    case 'ADMIN_GRANT':
      return 'Granted by Super Admin';
    case 'ROLE_PLAN':
      return 'Role plan entitlement';
    case 'INDIVIDUAL_OVERRIDE':
      return 'Individual override';
    case 'SCHOOL_OVERRIDE':
      return 'School override';
    case 'EXPIRED':
      return 'Subscription expired';
    case 'SUSPENDED':
      return 'Subscription suspended';
    case 'CANCELLED':
      return 'Subscription cancelled';
    case 'SCHOOL_CONTEXT_MISSING':
      return 'Account has no school assigned';
    default:
      return 'No active subscription';
  }
}

/** Headline for the lock screen. */
export function lockHeadline(status: AccessStatus): string {
  if (status.status === 'SUSPENDED') return 'Your subscription is suspended';
  return 'Subscription required';
}

/** Supporting sentence for the lock screen - fact, not marketing. */
export function lockBody(status: AccessStatus): string {
  if (status.status === 'SUSPENDED') {
    return 'Your subscription is suspended. Access to attendance, homework, exams, marks, timetables, report cards and the calendar is paused until it is restored. Contact your school administrator.';
  }
  if (status.reason === 'EXPIRED') {
    return 'Your access to attendance, homework, exams, marks, timetables, report cards and the calendar expired. Renew a plan to restore it.';
  }
  if (status.reason === 'CANCELLED') {
    return 'This subscription was cancelled. Renew a plan to restore access.';
  }
  if (status.reason === 'NONE') {
    return 'This account does not have access to attendance, homework, exams, marks, timetables, report cards and the calendar yet. Choose a plan to get started.';
  }
  return 'Your school requires an active subscription for this module. Choose a plan to continue.';
}

/** Short status line for cards and the sidebar. */
export function accessSummary(status: AccessStatus): string {
  if (!status.subscriptions_enabled) return 'Subscriptions are off for this school';
  if (status.reason === 'SCHOOL_FREE' || status.reason === 'USER_FREE_OVERRIDE') {
    const until = status.expires_at;
    return until ? `Free until ${formatDate(until)}` : 'Free access';
  }
  if (!status.has_access) return lockHeadline(status);
  return status.expires_at ? `Active until ${formatDate(status.expires_at)}` : 'Active';
}

/* -------------------------------------------------------------------------
 * datetime-local plumbing
 *
 * The API takes/returns naive-UTC ISO datetimes; `<input type="datetime-local">`
 * speaks `YYYY-MM-DDTHH:MM` in whatever the browser thinks "now" is. Both
 * converters therefore work in UTC explicitly so an expiry picked in IST is
 * still the exact instant the server stores.
 * ---------------------------------------------------------------------- */

/** Naive-UTC ISO -> `YYYY-MM-DDTHH:MM` for a datetime-local input. */
export function toDateTimeLocal(value: string | null | undefined): string {
  const date = parseUtc(value);
  if (!date) return '';
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(
    date.getUTCHours()
  )}:${pad(date.getUTCMinutes())}`;
}

/** `YYYY-MM-DDTHH:MM` -> naive-UTC ISO (`:00` seconds), or null when empty. */
export function fromDateTimeLocal(value: string): string | null {
  if (!value) return null;
  return `${value}:00`;
}

/** Minute-level equality between a datetime-local value and an API value. */
export function sameMinute(a: string | null | undefined, b: string | null | undefined): boolean {
  const left = toDateTimeLocal(a);
  const right = toDateTimeLocal(b);
  if (!left || !right) return left === right;
  return left === right;
}
