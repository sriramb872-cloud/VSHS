// frontend/src/services/api.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('scholaris_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
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

api.interceptors.response.use(
  (response) => {
    // The request reached the server, so connectivity is demonstrably fine.
    emitNetworkSuccess();
    return response;
  },
  (error) => {
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

    if (error.response && error.response.status === 401) {
      localStorage.removeItem('scholaris_access_token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
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
 * `api.scholaris.in` vs the app host in production), so handing `/media/...`
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