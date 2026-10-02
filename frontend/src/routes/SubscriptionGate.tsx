// src/routes/SubscriptionGate.tsx
/**
 * Guards the *content* of a role shell once entitlement is known to be absent.
 *
 * What it does:
 *   - reads the single server-resolved `AccessStatus` from SubscriptionContext;
 *   - while that is still unknown (first load, or `/subscription/me` could not
 *     be read) it renders the children, because a flaky network or a slow
 *     request must never trap a signed-in user behind a lock screen;
 *   - never hides the subscription, profile, settings or notification pages,
 *     because the first one is how a locked user gets unlocked;
 *   - when the server has explicitly answered `has_access: false` it replaces
 *     the rest of the content with the lock screen.
 *
 * What it never does: grant access. The sidebar, header and every guarded API
 * call re-check entitlement on the server regardless of what this renders.
 */
import React from 'react';
import { useLocation } from 'react-router-dom';
import { LockScreen } from '../components/subscriptions/LockScreen';
import { useAuth } from '../contexts/AuthContext';
import { useSubscription } from '../contexts/SubscriptionContext';

const GateSkeleton: React.FC = () => (
  <div className="flex items-center justify-center min-h-[40vh]">
    <div className="w-8 h-8 border-[3px] border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
  </div>
);

/**
 * Route segments that must stay reachable while the modules are locked.
 *
 * The contract is not "the sidebar survives" but "the locked user can fix it".
 * `/subscription` is the route that actually restores access, and profile,
 * settings and notifications are account-level pages the backend never gates -
 * blocking them would leave someone locked in with no way out.
 */
const ALWAYS_OPEN_SEGMENTS = new Set([
  'subscription',
  'settings',
  'profile',
  'notifications',
]);

/** `/student/homework/:id` -> `homework`, i.e. only the segment after the role. */
function segmentAfterRole(pathname: string): string | null {
  const [, , second] = pathname.split('/');
  return second || null;
}

export const SubscriptionGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { status, loading } = useSubscription();
  const { user } = useAuth();
  const { pathname } = useLocation();

  // Belt and braces: the server already exempts SUPER_ADMIN in
  // `SubscriptionService.get_access_status`, so this can only ever be hit if
  // the two ever disagree - and locking the operator out of the console that
  // fixes billing would be the worst possible failure mode. The server remains
  // the authority for every guarded endpoint.
  if (user?.role === 'SUPER_ADMIN') return <>{children}</>;

  if (!status) {
    if (loading) return <GateSkeleton />;
    return <>{children}</>;
  }

  if (status.has_access) return <>{children}</>;

  const segment = segmentAfterRole(pathname);
  if (segment && ALWAYS_OPEN_SEGMENTS.has(segment)) return <>{children}</>;

  return <LockScreen status={status} displayName={user?.display_name} />;
};

export default SubscriptionGate;
