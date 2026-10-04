// src/utils/razorpayCheckout.ts
/**
 * Lazy loader + typings for Razorpay's hosted Checkout (`checkout.js`).
 *
 * The script is fetched from Razorpay's CDN the FIRST time a user opens a
 * checkout and never earlier: nobody should download a third-party payment
 * script on page load, and it must not become part of the critical path for
 * a student who never pays. The promise is module-level, so N concurrent
 * callers still produce exactly ONE `<script>` tag.
 *
 * Only PUBLIC values are handled here (the publishable key id, an order id,
 * an amount in paise). Key secrets and webhook secrets never reach the
 * browser - see `backend-python/app/services/payment_providers/razorpay.py`.
 *
 * The CSP in `vercel.json` must allow this origin:
 *   script-src https://checkout.razorpay.com
 *   frame-src   https://checkout.razorpay.com https://api.razorpay.com
 *   connect-src https://api.razorpay.com https://lumberjack.razorpay.com
 */

const CHECKOUT_SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js';

/** Reject instead of leaving the user staring at a spinner forever. */
const LOAD_TIMEOUT_MS = 15_000;

/** What Razorpay hands back to `handler` once the payment is done. */
export interface RazorpayCheckoutResult {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

/**
 * The options this app passes to Checkout. Deliberately narrow: only the
 * keys we actually set are typed, so a typo fails `npm run typecheck`
 * instead of silently opening a mis-configured checkout.
 */
export interface RazorpayCheckoutOptions {
  key: string;
  amount: number;
  currency: string;
  name?: string;
  description?: string;
  order_id: string;
  handler: (result: RazorpayCheckoutResult) => void;
  prefill?: Record<string, string>;
  notes?: Record<string, string>;
  theme?: { color?: string; backdrop_color?: string; hide_topbar?: boolean };
  /** Instrument switches. The backend enforces UPI regardless of this. */
  method?: Record<string, boolean>;
  config?: {
    display?: {
      blocks?: Record<string, { name: string; instruments?: Array<{ method: string }> }>;
      sequence?: string[];
      hide?: Array<{ method: string[] }>;
      preferences?: { default_block?: string };
    };
  };
  modal?: {
    ondismiss?: () => void;
    confirm_close?: boolean;
    escape?: boolean;
    animation?: boolean;
    backdropclose?: boolean;
  };
}

export interface RazorpayCheckoutInstance {
  open(): void;
  close(): void;
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => RazorpayCheckoutInstance;
  }
}

let loading: Promise<void> | null = null;

/** Resolve when `window.Razorpay` exists; one in-flight load at most. */
export function loadRazorpayCheckout(): Promise<void> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('Razorpay checkout requires a browser.'));
  }
  if (window.Razorpay) return Promise.resolve();
  if (loading) return loading;

  loading = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = CHECKOUT_SCRIPT_URL;
    script.async = true;

    const cleanup = () => {
      window.clearTimeout(timer);
      script.removeEventListener('load', onLoad);
      script.removeEventListener('error', onError);
    };

    const fail = (message: string) => {
      cleanup();
      script.remove();
      loading = null;
      reject(new Error(message));
    };

    const timer = window.setTimeout(() => {
      fail('The payment window could not be loaded. Check your connection and try again.');
    }, LOAD_TIMEOUT_MS);

    const onLoad = () => {
      cleanup();
      if (window.Razorpay) {
        resolve();
      } else {
        fail('The payment window loaded but did not initialise. Please try again.');
      }
    };

    const onError = () => {
      fail('Could not load the payment window. Please try again.');
    };

    script.addEventListener('load', onLoad);
    script.addEventListener('error', onError);
    document.head.appendChild(script);
  });

  return loading;
}

export default loadRazorpayCheckout;
