// src/pwa/registerServiceWorker.ts
/**
 * Service-worker registration and update plumbing.
 *
 * This uses the plain Service Worker API rather than `workbox-window`. The only
 * thing that genuinely needs build-time support is generating a worker that
 * knows its own precache manifest, and that is what the `VitePWA` plugin does
 * in `vite.config.js`. Everything at runtime - registration, detecting that a
 * newer build is waiting, and the skip-waiting hand-off - is standard
 * `navigator.serviceWorker` and needs no library. Importing `workbox-window`
 * for it added ~8 KB gzip to the main chunk of an ERP that is otherwise fine,
 * which is not a trade worth making.
 *
 * Everything here is best-effort by design. A PWA is an enhancement: if the
 * browser has no service-worker support, registration is blocked, or the worker
 * fails to install, the ERP must keep working exactly as before. Every failure
 * path is caught and logged rather than thrown, because an exception here would
 * take the whole React tree down before it renders.
 */

/** Path emitted by the VitePWA plugin's `generateSW` mode. */
const SW_URL = '/sw.js';
/** Scope must cover every React Router path, which all live under `/`. */
const SW_SCOPE = '/';
/** Re-check for a new deploy hourly while the tab is open. */
const UPDATE_CHECK_INTERVAL_MS = 60 * 60 * 1000;

/**
 * `updateViaCache: 'none'` forces the worker script to be re-fetched rather
 * than served from the HTTP cache.
 *
 * `ServiceWorkerRegistration.update()` accepts this options bag at runtime
 * (Chrome 68+, Firefox, Safari 15.4+), but the bundled `lib.dom` typings in
 * this TypeScript version still declare it as taking no arguments. The cast
 * below widens the call to the real signature - it is a typing gap, not a
 * behaviour change, and it is the difference between picking up a deploy
 * promptly and a browser sitting on a stale shell for up to 24 hours.
 */
type UpdateWithOptions = (options?: {
  updateViaCache?: 'none' | 'imports' | 'all';
}) => Promise<ServiceWorkerRegistration>;

function updateRegistration(registration: ServiceWorkerRegistration): Promise<unknown> {
  return (registration.update as UpdateWithOptions).call(registration, {
    updateViaCache: 'none',
  });
}

/**
 * Is this URL actually going to be served as JavaScript?
 *
 * `navigator.serviceWorker.register()` rejects with "unsupported MIME type" for
 * a non-JS script, but only *after* the fetch, and while that is in flight the
 * registration sits in a permanent pending state: `navigator.serviceWorker.ready`
 * never resolves and the registration never completes. That is not harmless -
 * a never-settling registration left in place was enough to keep re-triggering
 * work on every mount.
 *
 * It also happens in normal operation: with the service worker disabled (the
 * default for `npm run dev`) a dev/static server answers `/sw.js` with the SPA
 * `index.html`, i.e. `text/html`. So we check the content type first and skip
 * registration entirely when there is no worker to install.
 */
async function isJavaScript(url: string): Promise<boolean> {
  try {
    const res = await fetch(url, { cache: 'no-store', headers: { Accept: 'application/javascript' } });
    if (!res.ok) return false;
    const type = res.headers.get('content-type') || '';
    return (
      type.includes('javascript') ||
      type.includes('ecmascript')
    );
  } catch {
    // Offline, or the request failed. Assume there is a worker; `register()`
    // will surface any real problem and it is caught below.
    return true;
  }
}

export interface ServiceWorkerCallbacks {
  /** A new build is ready. The user decides when to switch to it. */
  onNeedRefresh?: () => void;
  /** The worker is active and the app shell is cached for offline use. */
  onOfflineReady?: () => void;
  /** A registration problem worth surfacing to developers. */
  onError?: (message: string) => void;
}

/** `true` when the browser can actually run a service worker. */
export function isServiceWorkerSupported(): boolean {
  return typeof navigator !== 'undefined' && 'serviceWorker' in navigator;
}

/** `true` once the page is being served by an active service worker. */
export function isControlledByServiceWorker(): boolean {
  return typeof navigator !== 'undefined' && navigator.serviceWorker?.controller != null;
}

/**
 * Register the worker and wire the update signals.
 *
 * @returns a function that activates a waiting update and reloads, or `null`
 *          when service workers are unavailable.
 */
export function registerServiceWorker(
  callbacks: ServiceWorkerCallbacks = {},
): (() => Promise<void>) | null {
  if (!isServiceWorkerSupported()) {
    callbacks.onError?.('Service workers are not supported in this browser.');
    return null;
  }

  const applyUpdate = async (): Promise<void> => {
    try {
      const registration = await navigator.serviceWorker.getRegistration();
      const waiting = registration?.waiting;
      if (!waiting) {
        // Nothing staged (e.g. the worker was already activated). A plain
        // reload picks up whatever the network has.
        window.location.reload();
        return;
      }
      await new Promise<void>((resolve) => {
        let settled = false;
        const finish = () => {
          if (settled) return;
          settled = true;
          resolve();
        };
        navigator.serviceWorker.addEventListener('controllerchange', finish, { once: true });
        // The generated worker honours this message and activates immediately.
        waiting.postMessage({ type: 'SKIP_WAITING' });
        // Never leave the user stuck if `controllerchange` never arrives.
        window.setTimeout(finish, 2000);
      });
      window.location.reload();
    } catch {
      window.location.reload();
    }
  };

  const register = async (): Promise<void> => {
    try {
      if (!(await isJavaScript(SW_URL))) {
        // No worker deployed here (dev server, or a host that rewrites unknown
        // paths to the SPA). This is a normal situation, not an error.
        if (import.meta.env.DEV) {
          // eslint-disable-next-line no-console
          console.info(`[pwa] no service worker at ${SW_URL} - running without offline support.`);
        }
        return;
      }

      const registration = await navigator.serviceWorker.register(SW_URL, { scope: SW_SCOPE });

      // A worker already waiting on page load means a deploy landed while the
      // user was away.
      if (registration.waiting && navigator.serviceWorker.controller) {
        callbacks.onNeedRefresh?.();
      }

      registration.addEventListener('updatefound', () => {
        const installing = registration.installing;
        if (!installing) return;
        installing.addEventListener('statechange', () => {
          // "installed" while another worker is already in control means this
          // is an UPDATE. On a first install there is no controller, and the
          // user has nothing to be told.
          if (installing.state === 'installed' && navigator.serviceWorker.controller) {
            callbacks.onNeedRefresh?.();
          }
        });
      });

      // `ready` resolves once a worker is active, by which point the precache
      // it installed at build time is populated, so the shell works offline.
      navigator.serviceWorker.ready
        .then(() => callbacks.onOfflineReady?.())
        .catch(() => {
          /* never became ready; nothing to report */
        });

      window.setInterval(() => {
        // Bypass the HTTP cache for sw.js: a host serving it with a long
        // `max-age` would otherwise leave users on a stale shell.
        void updateRegistration(registration).catch(() => {
          /* an update check failing while offline is expected and harmless */
        });
      }, UPDATE_CHECK_INTERVAL_MS);

      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.info(`[pwa] service worker registered: ${SW_URL} (scope ${SW_SCOPE})`);
      }
    } catch (error) {
      // Never let PWA setup break the app.
      // eslint-disable-next-line no-console
      console.warn('[pwa] service worker registration failed:', error);
      callbacks.onError?.(error instanceof Error ? error.message : String(error));
    }
  };

  void register();
  return applyUpdate;
}

/** Tear the worker down. Used by tooling, never by the UI. */
export async function unregisterServiceWorker(): Promise<boolean> {
  if (!isServiceWorkerSupported()) return false;
  try {
    const registration = await navigator.serviceWorker.getRegistration();
    return (await registration?.unregister()) ?? false;
  } catch {
    return false;
  }
}
