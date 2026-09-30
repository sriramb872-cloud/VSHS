// src/components/shared/PWAUpdatePrompt.tsx
import React, { useRef, useState } from 'react';
import { RefreshCw, X } from 'lucide-react';
import { usePWA } from '../../contexts/PWAContext';

/**
 * "A new version of SCHOLARIS is available."
 *
 * The waiting service worker is never activated automatically, so this is the
 * only path to a new build. That matters here: a silent swap could discard a
 * half-typed attendance remark or an unsaved marks entry. The user presses
 * Update, we activate the worker and reload once it takes control.
 *
 * Keyboard/AT behaviour: a polite live region, real buttons, visible focus
 * rings, and focus is NOT stolen on appear (so it cannot interrupt whatever
 * the user is doing). Nothing is trapped.
 */
export const PWAUpdatePrompt: React.FC = () => {
  const { updateAvailable, applyUpdate } = usePWA();
  const [applying, setApplying] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const busyRef = useRef(false);

  if (!updateAvailable || dismissed) return null;

  const onUpdate = async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setApplying(true);
    await applyUpdate();
    // applyUpdate reloads the page; if reload was blocked, unstick the button.
    setApplying(false);
    busyRef.current = false;
  };

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="pwa-update-prompt"
      className="w-[min(22rem,calc(100vw-2rem))] rounded-2xl border border-[var(--brand-border)] bg-white p-4 shadow-xl"
    >
      <div className="flex items-start gap-2.5">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-[var(--brand-light)] text-[var(--brand)]">
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-bold text-slate-900">Update available</h2>
          <p className="mt-0.5 text-xs leading-snug text-slate-600">
            A new version of SCHOLARIS has been deployed. Update now to get the latest fixes.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="-mr-1 -mt-1 rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]"
        >
          <X className="h-4 w-4" aria-hidden="true" />
          <span className="sr-only">Dismiss update notification</span>
        </button>
      </div>

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={onUpdate}
          disabled={applying}
          className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-xl bg-[var(--brand)] text-xs font-bold text-white transition-colors hover:bg-[var(--brand-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)] focus-visible:ring-offset-2 disabled:opacity-60"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${applying ? 'animate-spin' : ''}`} aria-hidden="true" />
          {applying ? 'Updating\u2026' : 'Update'}
        </button>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="inline-flex h-9 items-center justify-center rounded-xl border border-slate-200 px-3 text-xs font-bold text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
        >
          Later
        </button>
      </div>
    </div>
  );
};

export default PWAUpdatePrompt;
