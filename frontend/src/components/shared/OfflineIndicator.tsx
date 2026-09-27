// src/components/shared/OfflineIndicator.tsx
import React from 'react';
import { WifiOff, RefreshCw } from 'lucide-react';
import { usePWA } from '../../contexts/PWAContext';

/**
 * A single, honest connectivity banner.
 *
 * Shown when the browser reports it is offline, or when an API request has
 * actually failed with no network. It deliberately does not attempt to render
 * any ERP data while offline - SCHOLARIS reads live data from the server on
 * every page, and inventing a local copy would be wrong.
 *
 * Rendered in normal document flow (not fixed) so it pushes content down
 * instead of covering a header, a dialog, or a form.
 */
export const OfflineIndicator: React.FC = () => {
  const { isOnline, hadNetworkFailure, offlineReady, isStandalone } = usePWA();

  // A hard offline condition, or a latched network failure that has not yet
  // been cleared by an `online` event.
  const show = !isOnline || hadNetworkFailure;
  if (!show) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="offline-indicator"
      className="sticky top-0 z-30 border-b border-amber-300 bg-amber-50 text-amber-900"
    >
      <div className="mx-auto flex w-full max-w-7xl items-center gap-2.5 px-3 py-2 sm:px-5">
        <WifiOff className="h-4 w-4 flex-shrink-0 text-amber-600" aria-hidden="true" />
        <p className="text-xs font-semibold leading-snug sm:text-sm">
          You&rsquo;re offline. Reconnect to continue &mdash; live SCHOLARIS data needs a connection.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="ml-auto inline-flex h-8 flex-shrink-0 items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-2.5 text-xs font-bold text-amber-800 transition-colors hover:bg-amber-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          <span className="hidden sm:inline">Retry</span>
          <span className="sr-only sm:hidden">Retry</span>
        </button>
      </div>
      {!isStandalone && offlineReady ? (
        <p className="mx-auto w-full max-w-7xl px-3 pb-2 text-[11px] text-amber-700 sm:px-5">
          The app shell is cached, so the screen below still loads while offline.
        </p>
      ) : null}
    </div>
  );
};

export default OfflineIndicator;
