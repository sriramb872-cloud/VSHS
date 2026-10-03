// frontend/src/services/api.ts
import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import { getStoredAcademicYearId } from './academicYearStorage';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/* -------------------------------------------------------------------------
 * Token storage
 * ---------------------------------------------------------------------- */

const ACCESS_TOKEN_KEY = 'scholaris_access_token';
const REFRESH_TOKEN_KEY = 'scholaris_refresh_token';

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/** Persist a token pair returned by login / refresh / password change. */
export function setTokens(access: string, refresh?: string | null): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  if (refresh) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

/**
 * Drop both tokens locally. Does not call the server - the server-side
 * revocation is `/auth/logout`, which callers should invoke first when they
 * still hold a refresh token.
 */
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/**
 * Requests whose academic year must NOT follow the header selector.
 *
 * `/academic-years` itself (the school's year catalogue) would otherwise be
 * asking the server for "the list of years in year X", which is meaningless.
 * A call may also opt out explicitly by passing
 * `headers: { 'X-Academic-Year-Id': '' }`.
 */
const YEAR_INDEPENDENT_URLS = [/\/academic-years(\/|\?|$)/];

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Attach the academic-year context so the backend can scope the request.
    const url = config.url ?? '';
    const optedOut =
      YEAR_INDEPENDENT_URLS.some((pattern) => pattern.test(url)) ||
      // An empty string is an explicit "do not send a year for this call".
      config.headers['X-Academic-Year-Id'] === '';

    if (optedOut) {
      delete config.headers['X-Academic-Year-Id'];
    } else if (!config.headers['X-Academic-Year-Id']) {
      const yearId = getStoredAcademicYearId();
      if (yearId) {
        config.headers['X-Academic-Year-Id'] = String(yearId);
      }
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Network-failure listeners.
 *
 * A request that never reached the server (offline, DNS failure, connection
 * refused) is different from a request the server rejected. The UI needs to
 * tell the user "you are offline, reconnect to continue" rather than showing a
 * generic error, and it must never present such a failure as a success.
 *
 * Registered from `PWAProvider`; the default set is empty so `api.ts` has no
 * hard dependency on the PWA layer.
 */
type NetworkFailureListener = (method: string, url: string) => void;
type NetworkSuccessListener = () => void;

const networkFailureListeners = new Set<NetworkFailureListener>();
const networkSuccessListeners = new Set<NetworkSuccessListener>();

export function onNetworkFailure(listener: NetworkFailureListener): () => void {
  networkFailureListeners.add(listener);
  return () => {
    networkFailureListeners.delete(listener);
  };
}

/**
 * Notified whenever a request completes. Used to clear a latched "offline"
 * state: a single failed request must not pin the offline banner on screen
 * forever if connectivity came back without an `online` event (which happens
 * on captive portals, flaky mobile links and in some browsers).
 */
export function onNetworkSuccess(listener: NetworkSuccessListener): () => void {
  networkSuccessListeners.add(listener);
  return () => {
    networkSuccessListeners.delete(listener);
  };
}

function emitNetworkFailure(method: string, url: string): void {
  for (const listener of networkFailureListeners) {
    try {
      listener(method, url);
    } catch {
      /* a listener must never break the request pipeline */
    }
  }
}

function emitNetworkSuccess(): void {
  for (const listener of networkSuccessListeners) {
    try {
      listener();
    } catch {
      /* a listener must never break the request pipeline */
    }
  }
}

/** `true` when the error means "the request never reached the server". */
export function isNetworkError(error: unknown): boolean {
  const err = error as {
    response?: unknown;
    request?: unknown;
    code?: string;
    message?: string;
  };
  // A response means the server DID answer (even 4xx/5xx), so this is not a
  // connectivity problem.
  if (err?.response) return false;
  if (!err?.request) return false;
  return (
    err.code === 'ERR_NETWORK' ||
    err.message === 'Network Error' ||
    err.code === 'ECONNABORTED' ||
    err.code === 'ETIMEDOUT'
  );
}

/* -------------------------------------------------------------------------
 * 401 -> refresh -> retry
 *
 * Access tokens are short-lived (default 30 min), so a plain 401 handler that
 * bounces the user to /login would log everyone out twice an hour. Instead:
 *
 *   - concurrent 401s share ONE in-flight refresh (single-flight), so a burst
 *     of parallel requests cannot burn the rotating refresh token 10 times;
 *   - refresh tokens are one-time-use (rotation), so a replayed/old token
 *     fails server-side - we therefore only ever send the current one;
 *   - if refresh fails the session is genuinely over: clear tokens and go to
 *     /login exactly once.
 * ---------------------------------------------------------------------- */

/** Endpoints where a 401 must NOT trigger a refresh attempt. */
const AUTH_PATHS = ['/auth/login', '/auth/refresh', '/auth/logout', '/auth/logout-all'];

/** Bare client for the refresh call itself - bypasses these interceptors. */
const rawClient = axios.create({ baseURL: API_BASE_URL });

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;
    try {
      const response = await rawClient.post<{ access_token: string; refresh_token?: string | null }>(
        '/auth/refresh',
        { refresh_token: refreshToken }
      );
      const { access_token, refresh_token } = response.data;
      if (!access_token) return null;
      // Rotation: the server invalidated the old refresh token, so persist
      // the replacement together with the new access token.
      setTokens(access_token, refresh_token);
      return access_token;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

function redirectToLogin(): void {
  clearTokens();
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

/**
 * Fired whenever the API answers `403` with
 * `detail.code === 'SUBSCRIPTION_REQUIRED'`.
 *
 * The subscription gate listens for this so it can re-read the authoritative
 * access status the moment a feature call is refused, instead of waiting for
 * the next poll. Never used to *grant* access - the server is the only
 * authority on that.
 */
export const SUBSCRIPTION_REQUIRED_EVENT = 'scholaris:subscription-required';

api.interceptors.response.use(
  (response) => {
    // The request reached the server, so connectivity is demonstrably fine.
    emitNetworkSuccess();
    return response;
  },
  async (error) => {
    if (isNetworkError(error)) {
      // Let the app-wide offline state know. The promise is still rejected, so
      // no caller can mistake this for a success.
      emitNetworkFailure(
        (error.config?.method ?? 'get').toUpperCase(),
        error.config?.url ?? ''
      );
    } else {
      // Any other response (even 4xx/5xx) proves the network is up.
      emitNetworkSuccess();
    }

    const status = error.response?.status;
    const originalConfig = error.config as
      | (AxiosRequestConfig & { __authRetried?: boolean })
      | undefined;
    const url = originalConfig?.url ?? '';

    if (status === 401 && originalConfig && !originalConfig.__authRetried) {
      const isAuthCall = AUTH_PATHS.some((path) => url.includes(path));
      if (!isAuthCall) {
        originalConfig.__authRetried = true;
        const freshToken = await refreshAccessToken();
        if (freshToken) {
          originalConfig.headers = {
            ...originalConfig.headers,
            Authorization: `Bearer ${freshToken}`,
          };
          return api(originalConfig);
        }
        // Refresh failed (expired/revoked/rotated-away): the session is over.
        redirectToLogin();
        return Promise.reject(error);
      }
    }

    if (status === 401) {
      // Refresh path itself was rejected, or an auth endpoint 401'd.
      redirectToLogin();
    }

    // The subscription domain is the only place `detail` is an object, so the
    // code is unambiguous. Emit an app-wide signal so the gate can refresh the
    // entitlement state *without* every caller having to catch this shape.
    // The rejection is still propagated - no caller may treat it as a success.
    if (status === 403) {
      const detail = error.response?.data?.detail;
      if (
        detail !== null &&
        typeof detail === 'object' &&
        (detail as { code?: unknown }).code === 'SUBSCRIPTION_REQUIRED'
      ) {
        window.dispatchEvent(
          new CustomEvent(SUBSCRIPTION_REQUIRED_EVENT, {
            detail: {
              reason: (detail as { reason?: string }).reason ?? null,
              expires_at: (detail as { expires_at?: string | null }).expires_at ?? null,
            },
          })
        );
      }
    }

    return Promise.reject(error);
  }
);

/** Origin that serves the API, e.g. `http://localhost:8000`. */
export const API_ORIGIN = API_BASE_URL.replace(/\/api\/v\d+\/?$/, '');

/**
 * Resolve a server-relative media path to a fetchable URL.
 *
 * The backend stores profile photos as `/media/profile_photos/<file>` and
 * mounts StaticFiles at `/media` on the API process. The web app is served from
 * a *different* origin in every real deployment (Vite on :5173 in dev,
 * `backend-production-510f.up.railway.app` vs the app host in production), so handing `/media/...`
 * straight to an `<img src>` makes the browser request it from the web origin
 * and get a 404 - the upload silently never appears.
 *
 * Absolute URLs (and data:/blob: URIs) are returned untouched.
 */
export function mediaUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined;
  if (/^(https?:)?\/\//i.test(path) || /^(data|blob):/i.test(path)) return path;
  return `${API_ORIGIN}${path.startsWith('/') ? path : `/${path}`}`;
}

export default api;