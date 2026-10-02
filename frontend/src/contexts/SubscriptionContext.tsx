// src/contexts/SubscriptionContext.tsx
/**
 * App-wide subscription state.
 *
 * Holds ONE copy of `GET /subscription/me` so the sidebar, the lock screen and
 * the subscription page all agree on the same server-resolved answer. The
 * context never decides entitlement itself: `access.has_access` is produced by
 * the single authoritative resolver on the backend.
 *
 * Failure policy is deliberately asymmetric:
 *   - entitlement questions FAIL OPEN (if `/subscription/me` cannot be read we
 *     render the app and let each guarded endpoint answer for itself, because
 *     a flaky network must not trap a signed-in user behind a lock screen);
 *   - entitlement answers themselves are FAIL CLOSED (a resolved
 *     `has_access: false` locks the gated content until the server says
 *     otherwise).
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { SUBSCRIPTION_REQUIRED_EVENT } from '../services/api';
import { subscriptionsService } from '../services/subscriptions';
import { useAuth } from './AuthContext';
import type { AccessStatus, MeSubscription } from '../types/subscription';

interface SubscriptionContextType {
  /** Full `/subscription/me` payload, or null while unknown/unavailable. */
  data: MeSubscription | null;
  /** Convenience accessor for `data.access`. */
  status: AccessStatus | null;
  /** True until the first `/subscription/me` response settles. */
  loading: boolean;
  /**
   * Only true when the server has *explicitly* said `has_access: false`.
   * Unknown/failed loads are not a lock.
   */
  locked: boolean;
  refresh: () => Promise<void>;
}

const SubscriptionContext = createContext<SubscriptionContextType | undefined>(undefined);

/** Collapse a burst of 403s into a single re-read. */
const REFRESH_DEBOUNCE_MS = 400;

export const SubscriptionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState<MeSubscription | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const timerRef = useRef<number | null>(null);
  const lastUserRef = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const me = await subscriptionsService.me();
      setData(me);
    } catch {
      // Fail open: unknown is not the same as locked (see module docstring).
    } finally {
      setLoading(false);
    }
  }, []);

  // Re-read whenever the signed-in identity changes (login, logout, switch).
  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setData(null);
      lastUserRef.current = null;
      setLoading(false);
      return;
    }
    if (lastUserRef.current === user.id) return;
    lastUserRef.current = user.id;
    setLoading(true);
    void refresh();
  }, [authLoading, user, refresh]);

  // The API tells us the moment an entitlement is refused, so the gate can
  // flip immediately rather than at the next scheduled refresh.
  useEffect(() => {
    const onRequired = () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null;
        void refresh();
      }, REFRESH_DEBOUNCE_MS);
    };
    window.addEventListener(SUBSCRIPTION_REQUIRED_EVENT, onRequired);
    // Also covers an explicit "entitlement may have changed" broadcast (the
    // subscription page dispatches it after a successful mock checkout).
    window.addEventListener('scholaris:subscription-changed', onRequired);
    return () => {
      window.removeEventListener(SUBSCRIPTION_REQUIRED_EVENT, onRequired);
      window.removeEventListener('scholaris:subscription-changed', onRequired);
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [refresh]);

  const value = useMemo<SubscriptionContextType>(
    () => ({
      data,
      status: data?.access ?? null,
      loading,
      locked: !!data && !data.access.has_access,
      refresh,
    }),
    [data, loading, refresh]
  );

  return <SubscriptionContext.Provider value={value}>{children}</SubscriptionContext.Provider>;
};

export const useSubscription = (): SubscriptionContextType => {
  const context = useContext(SubscriptionContext);
  if (!context) {
    throw new Error('useSubscription must be used within a SubscriptionProvider');
  }
  return context;
};

export default SubscriptionProvider;
