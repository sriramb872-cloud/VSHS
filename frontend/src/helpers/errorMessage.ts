// src/helpers/errorMessage.ts
/**
 * Extract a human-readable message from a rejected axios request.
 *
 * Most backend routers raise `HTTPException(detail="...")`, but FastAPI's
 * request-validation failures return `detail` as a *list* of per-field
 * objects, so blindly rendering `detail` would print "[object Object]".
 * This helper normalises all three shapes (string, list of objects, object
 * with `message`) into one line the UI can show, and falls back to a
 * caller-supplied default when the server said nothing useful.
 *
 * Connectivity failures get their own wording. When a request never reached the
 * server there is no `detail` to show, and the page-level fallback text is
 * usually about the specific action ("Failed to save attendance"), which reads
 * as though the save was attempted and rejected. Telling the user they are
 * offline is both more accurate and more actionable. Importantly this only
 * changes the *message*: a failed request is still a failed request, and no
 * caller is allowed to treat it as a success.
 */
import { isNetworkError } from '../services/api';

/** Shown whenever a request could not reach the server. */
export const OFFLINE_MESSAGE = "You're offline. Reconnect to continue.";

export function errorMessage(err: unknown, fallback: string): string {
  if (isNetworkError(err)) {
    return OFFLINE_MESSAGE;
  }

  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        const record = item as { msg?: string; loc?: unknown[] };
        if (!record.msg) return '';
        const field = Array.isArray(record.loc)
          ? record.loc.filter((part) => part !== 'body').join('.')
          : '';
        return field ? `${field}: ${record.msg}` : record.msg;
      })
      .filter(Boolean);
    if (messages.length) return messages.join('; ');
  }

  // Structured object detail. Only the subscription domain does this
  // (`{ code: 'SUBSCRIPTION_REQUIRED', message: '...' }`, plus the bulk
  // failure objects); every other router still sends a plain string. The
  // `code` is deliberately NOT rendered - callers branch on it separately via
  // `subscriptionsService.subscriptionErrorCode`.
  if (detail !== null && typeof detail === 'object') {
    const record = detail as { message?: unknown; msg?: unknown };
    const message = typeof record.message === 'string' ? record.message : record.msg;
    if (typeof message === 'string' && message.trim()) return message;
  }

  return fallback;
}

export default errorMessage;
