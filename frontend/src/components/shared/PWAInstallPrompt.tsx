// src/components/shared/PWAInstallPrompt.tsx
import React, { useEffect, useState } from 'react';
import { Download, X } from 'lucide-react';
import { usePWA } from '../../contexts/PWAContext';

/**
 * "Install SCHOLARIS" card.
 *
 * Behaviour that matters:
 *  * Only rendered when the browser has actually fired
 *    `beforeinstallprompt`. iOS Safari never fires it, so no dead button is
 *    shown there; iOS users install via Share > Add to Home Screen.
 *  * Hidden entirely once running standalone, and after a successful install.
 *  * Dismissal persists in localStorage so it does not reappear on every
 *    refresh.
 *  * Non-modal and non-blocking: it sits in the bottom-left dock, clear of the
 *    mobile bottom navigation and of the pet widget, and never covers a form
 *    or a dialog.
 */
export const PWAInstallPrompt: React.FC = () => {
  const { installPromptAvailable, isStandalone, promptInstall } = usePWA();
  const [dismissed, setDismissed] = useState(false);
  const [busy, setBusy] = useState(false);

  // Re-show on a later visit if the user dismissed a long time ago, so a new
  // user is not permanently opted out by one stray tap.
  useEffect(() => {
    let show = false;
    try {
      const raw = window.localStorage.getItem('scholaris_pwa_install_dismissed_at');
      if (!raw) show = true;
      else {
        const age = Date.now() - Number(raw);
        show = !Number.isFinite(age) || age > 1000 * 60 * 60 * 24 * 30; // 30 days
      }
    } catch {
      show = true;
    }
    setDismissed(!show);
  }, []);

  if (dismissed || isStandalone || !installPromptAvailable) return null;

  const onInstall = async () => {
    if (busy) return;
    setBusy(true);
    const outcome = await promptInstall();
    if (outcome !== 'unavailable') {
      setDismissed(true);
      try {
        window.localStorage.setItem('scholaris_pwa_install_dismissed_at', String(Date.now()));
      } catch {
        /* storage unavailable */
      }
    }
    setBusy(false);
  };

  const onDismiss = () => {
    setDismissed(true);
    try {
      window.localStorage.setItem('scholaris_pwa_install_dismissed_at', String(Date.now()));
    } catch {
      /* storage unavailable */
    }
  };

  return (
    <div
      role="region"
      aria-label="Install SCHOLARIS"
      data-testid="pwa-install-prompt"
      className="w-[min(22rem,calc(100vw-2rem))] rounded-2xl border border-slate-200 bg-white p-4 shadow-xl"
    >
      <div className="flex items-start gap-2.5">
        <img
          src="/icons/icon-192.png"
          alt=""
          width={40}
          height={40}
          className="h-10 w-10 flex-shrink-0 rounded-xl"
        />
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-bold text-slate-900">Install SCHOLARIS</h2>
          <p className="mt-0.5 text-xs leading-snug text-slate-600">
            Add it to your home screen and launch it like a native app, with offline access to the
            app shell.
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="-mr-1 -mt-1 rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]"
        >
          <X className="h-4 w-4" aria-hidden="true" />
          <span className="sr-only">Dismiss install prompt</span>
        </button>
      </div>

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={onInstall}
          disabled={busy}
          className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-xl bg-[var(--brand)] text-xs font-bold text-white transition-colors hover:bg-[var(--brand-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)] focus-visible:ring-offset-2 disabled:opacity-60"
        >
          <Download className="h-3.5 w-3.5" aria-hidden="true" />
          {busy ? 'Installing\u2026' : 'Install'}
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="inline-flex h-9 items-center justify-center rounded-xl border border-slate-200 px-3 text-xs font-bold text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
        >
          Not now
        </button>
      </div>
    </div>
  );
};

export default PWAInstallPrompt;
