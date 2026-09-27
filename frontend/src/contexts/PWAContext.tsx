// src/contexts/PWAContext.tsx
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  isServiceWorkerSupported,
  registerServiceWorker,
} from '../pwa/registerServiceWorker';
import { onNetworkFailure, onNetworkSuccess } from '../services/api';

/** The non-standard event Chromium fires when the app is installable. */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
}

export type OfflineReason = 'browser-offline' | 'service-worker';

export interface PWAContextValue {
  /** `navigator.onLine`, kept in sync with the online/offline events. */
  isOnline: boolean;
  /** A background request failed because there was no network. */
  hadNetworkFailure: boolean;
  /** True once the service worker has cached the shell for offline use. */
  offlineReady: boolean;
  /** A newer build is installed and waiting for the user to accept it. */
  updateAvailable: boolean;
  /** The user asked to install; a prompt is being held. */
  canInstall: boolean;
  /** The browser exposes the install prompt (Chromium/Android/desktop). */
  installPromptAvailable: boolean;
  /** Running as an installed app (standalone display mode). */
  isStandalone: boolean;
  /** Service worker is supported and controlling the page. */
  serviceWorkerReady: boolean;
  /** Ask the browser to show its install UI. No-op when unavailable. */
  promptInstall: () => Promise<'accepted' | 'dismissed' | 'unavailable'>;
  /** Activate the waiting service worker and reload. */
  applyUpdate: () => Promise<void>;
  /** The user dismissed the install card; do not show it again. */
  dismissInstall: () => void;
  /** A request failed with no network. Called by the axios layer. */
  reportNetworkFailure: () => void;
}

const PWAContext = createContext<PWAContextValue | undefined>(undefined);

const DISMISS_KEY = 'scholaris_pwa_install_dismissed';
const OFFLINE_READY_KEY = 'scholaris_pwa_offline_ready';

/** Read a boolean from localStorage without throwing (private mode, etc.). */
function readFlag(key: string): boolean {
  try {
    return window.localStorage.getItem(key) === '1';
  } catch {
    return false;
  }
}

function writeFlag(key: string, value: boolean): void {
  try {
    if (value) window.localStorage.setItem(key, '1');
    else window.localStorage.removeItem(key);
  } catch {
    /* storage unavailable; dismissal just won't persist */
  }
}

/**
 * Standalone detection.
 *
 * `display-mode: standalone` is the standard check. The `navigator.standalone`
 * property is iOS Safari's older equivalent and still needed there, because
 * iOS never fires `beforeinstallprompt` and users install via Share >
 * "Add to Home Screen" - so on iOS we cannot show an install button at all.
 */
function detectStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  const mm = window.matchMedia?.('(display-mode: standalone)');
  if (mm?.matches) return true;
  const nav = navigator as Navigator & { standalone?: boolean };
  if (nav.standalone === true) return true;
  // Some Android launchers report `minimal-ui` / `fullscreen` for a
  // home-screen shortcut.
  return (
    window.matchMedia?.('(display-mode: minimal-ui)')?.matches === true ||
    window.matchMedia?.('(display-mode: fullscreen)')?.matches === true
  );
}

export const PWAProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isOnline, setIsOnline] = useState<boolean>(() =>
    typeof navigator === 'undefined' ? true : navigator.onLine,
  );
  const [hadNetworkFailure, setHadNetworkFailure] = useState(false);
  const [offlineReady, setOfflineReady] = useState<boolean>(() => readFlag(OFFLINE_READY_KEY));
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [installDismissed, setInstallDismissed] = useState<boolean>(() => readFlag(DISMISS_KEY));
  const [isStandalone, setIsStandalone] = useState(detectStandalone);
  const [serviceWorkerReady, setServiceWorkerReady] = useState(false);

  /**
   * Imperative handle to the "activate the waiting worker" function.
   *
   * This is a `useRef`, deliberately not `useState`. Passing a function
   * straight to a state setter - `setApplyUpdate(applyUpdate)` - makes React
   * treat it as a state *updater* and invoke it with the previous state, which
   * silently ran the update-and-reload path on every mount and produced a
   * reload loop. A ref also removes the need for this handle to trigger
   * renders, so `applyUpdate` can stay referentially stable.
   */
  const applyUpdateRef = useRef<(() => Promise<void>) | null>(null);

  // --- connectivity ------------------------------------------------------
  useEffect(() => {
    const sync = () => {
      const online = navigator.onLine !== false;
      setIsOnline(online);
      // Only clear the latched failure when the browser says it is online
      // again; do not clear it merely because `online` fired while the link is
      // still unusable (captive portals, dead Wi-Fi).
      if (online) setHadNetworkFailure(false);
    };

    const goOnline = () => sync();
    const goOffline = () => {
      setIsOnline(false);
      setHadNetworkFailure(true);
    };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') sync();
    };

    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    // Re-check whenever the tab becomes visible again. This is what makes the
    // banner self-healing: a user who reconnects and switches back to the app
    // gets an accurate state without needing a reload.
    window.addEventListener('focus', onVisibility);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
      window.removeEventListener('focus', onVisibility);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);

  // A request that never reached the server also means we are effectively
  // offline, even though `navigator.onLine` can still report `true` (it only
  // reports link state, not reachability of the API host). Conversely, a
  // request that succeeds proves we are back, which clears a stale latch.
  useEffect(
    () =>
      onNetworkFailure(() => {
        setHadNetworkFailure(true);
        setIsOnline(false);
      }),
    [],
  );
  useEffect(
    () =>
      onNetworkSuccess(() => {
        setHadNetworkFailure(false);
        setIsOnline(true);
      }),
    [],
  );

  // --- install prompt ----------------------------------------------------
  useEffect(() => {
    const onBeforeInstallPrompt = (event: Event) => {
      // Keep the default mini-infobar off; we render our own prompt.
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setDeferredPrompt(null);
      setIsStandalone(true);
      setInstallDismissed(true);
      writeFlag(DISMISS_KEY, true);
    };

    window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  // --- standalone display mode ------------------------------------------
  useEffect(() => {
    const queries = [
      window.matchMedia?.('(display-mode: standalone)'),
      window.matchMedia?.('(display-mode: minimal-ui)'),
      window.matchMedia?.('(display-mode: fullscreen)'),
    ].filter(Boolean) as MediaQueryList[];

    const sync = () => setIsStandalone(detectStandalone());
    queries.forEach((q) => q.addEventListener('change', sync));
    return () => queries.forEach((q) => q.removeEventListener('change', sync));
  }, []);

  // --- service worker ----------------------------------------------------
  useEffect(() => {
    if (!isServiceWorkerSupported()) return;

    // A worker can already be controlling the page (e.g. after a reload).
    if (navigator.serviceWorker.controller) {
      setServiceWorkerReady(true);
    }

    const applyUpdate = registerServiceWorker({
      onNeedRefresh: () => setUpdateAvailable(true),
      onOfflineReady: () => {
        setOfflineReady(true);
        setServiceWorkerReady(true);
        writeFlag(OFFLINE_READY_KEY, true);
      },
      onError: (message) => {
        // eslint-disable-next-line no-console
        console.warn('[pwa] continuing without offline support:', message);
        setServiceWorkerReady(false);
      },
    });

    applyUpdateRef.current = applyUpdate;
    return () => {
      // Do not unregister on unmount: the worker must outlive the React tree.
      // Only drop the local handle.
      applyUpdateRef.current = null;
    };
  }, []);

  const applyUpdateAction = useCallback(async () => {
    const impl = applyUpdateRef.current;
    if (impl) {
      await impl();
      return;
    }
    // No worker to update (unsupported, or registration failed). A plain reload
    // still gets the user the current build.
    window.location.reload();
  }, []);

  const promptInstall = useCallback(async (): Promise<'accepted' | 'dismissed' | 'unavailable'> => {
    if (!deferredPrompt) return 'unavailable';
    try {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        setInstallDismissed(true);
        writeFlag(DISMISS_KEY, true);
      }
      // The event is single-use.
      setDeferredPrompt(null);
      return outcome;
    } catch {
      setDeferredPrompt(null);
      return 'unavailable';
    }
  }, [deferredPrompt]);

  const dismissInstall = useCallback(() => {
    setInstallDismissed(true);
    writeFlag(DISMISS_KEY, true);
  }, []);

  const reportNetworkFailure = useCallback(() => {
    setHadNetworkFailure(true);
    setIsOnline(false);
  }, []);

  const value = useMemo<PWAContextValue>(
    () => ({
      isOnline,
      hadNetworkFailure,
      offlineReady,
      updateAvailable,
      canInstall: !!deferredPrompt,
      // Only true on browsers that actually expose the install prompt.
      installPromptAvailable: !!deferredPrompt,
      isStandalone,
      serviceWorkerReady,
      promptInstall,
      applyUpdate: applyUpdateAction,
      dismissInstall,
      reportNetworkFailure,
    }),
    [
      isOnline,
      hadNetworkFailure,
      offlineReady,
      updateAvailable,
      deferredPrompt,
      isStandalone,
      serviceWorkerReady,
      promptInstall,
      applyUpdateAction,
      dismissInstall,
      reportNetworkFailure,
    ],
  );

  return <PWAContext.Provider value={value}>{children}</PWAContext.Provider>;
};

export function usePWA(): PWAContextValue {
  const ctx = useContext(PWAContext);
  if (!ctx) {
    throw new Error('usePWA must be used inside <PWAProvider>');
  }
  return ctx;
}

export default PWAProvider;
