// src/components/subscriptions/CheckoutDialog.tsx
/**
 * Checkout dialog for BOTH payment providers (`MePlans.payment_provider`).
 *
 * RAZORPAY (production, UPI only)
 *   1. the server opens an ORDER for the plan's own price (paise) and returns
 *      the publishable key id + order id - never a secret;
 *   2. this dialog lazy-loads Checkout.js and opens Razorpay's hosted window
 *      with UPI as the only instrument;
 *   3. Razorpay's `handler` gives us exactly two values (payment id +
 *      signature), which are POSTed to `/payments/{id}/verify`. The order id,
 *      the amount and the currency come from OUR payment row, and the server
 *      fetches the payment back from Razorpay before anything activates;
 *   4. UPI is asynchronous, so a PENDING answer starts a short poll of
 *      `GET /payments/{id}` (the webhook may finalize it a moment later).
 *
 * INTERNAL (development only)
 *   The client reports a simulated outcome; the server verifies its signed
 *   payload. Rendered only when the API says mock payments are enabled
 *   (`ENVIRONMENT != production` AND `PAYMENT_PROVIDER = INTERNAL`).
 *
 * Access itself is never derived here: success just re-reads `/me`.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  CreditCard,
  Loader2,
  Smartphone,
  X,
  XCircle,
} from 'lucide-react';
import { subscriptionsService } from '../../services/subscriptions';
import { errorMessage } from '../../helpers/errorMessage';
import {
  loadRazorpayCheckout,
  type RazorpayCheckoutResult,
} from '../../utils/razorpayCheckout';
import type {
  CheckoutResponse,
  MockCheckoutOutcome,
  SubscriptionPayment,
  SubscriptionPlan,
} from '../../types/subscription';
import { formatDuration, formatPrice } from './format';

interface CheckoutDialogProps {
  open: boolean;
  plan: SubscriptionPlan | null;
  /** `MePlans.mock_payments_enabled` - false in production. */
  mockEnabled: boolean;
  /** `MePlans.payment_provider` - INTERNAL | RAZORPAY. */
  paymentProvider?: string;
  onClose: () => void;
  /** Called after any provider outcome so the caller can refresh `/me`. */
  onSettled?: (payment: SubscriptionPayment) => void;
}

type Phase =
  | 'idle'
  | 'opening'
  | 'verifying'
  | 'waiting'
  | 'timeout'
  | 'success'
  | 'failed'
  | 'dismissed';

/** Poll `GET /payments/{id}` while UPI is still awaiting its app approval. */
const POLL_INTERVAL_MS = 3_000;
/** ~2 minutes of polling, then we stop and say we will activate on our own. */
const MAX_POLL_ATTEMPTS = 40;

const OUTCOMES: Array<{
  outcome: MockCheckoutOutcome;
  label: string;
  icon: React.ReactNode;
  className: string;
}> = [
  {
    outcome: 'SUCCESS',
    label: 'Simulate success',
    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
    className: 'bg-emerald-600 hover:bg-emerald-700',
  },
  {
    outcome: 'FAILED',
    label: 'Simulate failure',
    icon: <XCircle className="w-3.5 h-3.5" />,
    className: 'bg-rose-600 hover:bg-rose-700',
  },
  {
    outcome: 'CANCELLED',
    label: 'Simulate cancellation',
    icon: <Clock className="w-3.5 h-3.5" />,
    className: 'bg-slate-600 hover:bg-slate-700',
  },
  {
    outcome: 'PENDING',
    label: 'Leave pending',
    icon: <Clock className="w-3.5 h-3.5" />,
    className: 'bg-amber-600 hover:bg-amber-700',
  },
];

export const CheckoutDialog: React.FC<CheckoutDialogProps> = ({
  open,
  plan,
  mockEnabled,
  paymentProvider = 'INTERNAL',
  onClose,
  onSettled,
}) => {
  const [payment, setPayment] = useState<CheckoutResponse | null>(null);
  const [creating, setCreating] = useState(false);
  const [settling, setSettling] = useState<MockCheckoutOutcome | null>(null);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<Phase>('idle');
  const [error, setError] = useState<string | null>(null);

  // The Razorpay callbacks outlive this component's render closure, so the
  // payment id is read from a ref instead of a captured value.
  const paymentIdRef = useRef<number | null>(null);

  const isRazorpay = paymentProvider.toUpperCase() === 'RAZORPAY';
  // Simulated outcomes only exist outside production AND only for the
  // INTERNAL provider - a Razorpay checkout must never show them.
  const showMock = !isRazorpay && mockEnabled;

  const reset = useCallback(() => {
    setPayment(null);
    paymentIdRef.current = null;
    setCreating(false);
    setSettling(null);
    setBusy(false);
    setPhase('idle');
    setError(null);
  }, []);

  const close = useCallback(() => {
    reset();
    onClose();
  }, [onClose, reset]);

  /**
   * Refresh the row while KEEPING the checkout-only fields (key id, order
   * id, paise) that `POST /payments` returned and `/payments/{id}` omits.
   */
  const mergePayment = useCallback((updated: SubscriptionPayment) => {
    setPayment((current) => ({ ...(current as CheckoutResponse), ...updated }));
  }, []);

  /** Terminal SUCCESS: refresh the app-wide access state and show it. */
  const finishSuccess = useCallback(
    (updated: SubscriptionPayment) => {
      mergePayment(updated);
      setPhase('success');
      setBusy(false);
      setError(null);
      onSettled?.(updated);
      // Let the app-wide access state re-read immediately.
      window.dispatchEvent(new Event('scholaris:subscription-changed'));
    },
    [mergePayment, onSettled]
  );

  // Open: open a PENDING payment for the selected plan (amount comes from the
  // server's plan row, never from this client).
  useEffect(() => {
    if (!open || !plan) return;
    let cancelled = false;
    setCreating(true);
    setError(null);
    subscriptionsService
      .createCheckout(plan.id)
      .then((created) => {
        if (cancelled) return;
        paymentIdRef.current = created.id;
        setPayment(created);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err, 'Could not start the checkout.'));
      })
      .finally(() => {
        if (!cancelled) setCreating(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, plan]);

  /* ---------------------------------------------------------------------
   * Razorpay: open, verify, poll
   * ------------------------------------------------------------------ */

  /** Razorpay's `handler`: verify server-side, then wait if still PENDING. */
  const handleRazorpayResult = useCallback(
    async (result: RazorpayCheckoutResult) => {
      const paymentId = paymentIdRef.current;
      if (paymentId === null) return;
      setPhase('verifying');
      setBusy(true);
      setError(null);
      try {
        const updated = await subscriptionsService.verifyPayment(paymentId, {
          razorpay_payment_id: result.razorpay_payment_id,
          razorpay_signature: result.razorpay_signature,
        });
        if (updated.status === 'SUCCESS') {
          finishSuccess(updated);
          return;
        }
        mergePayment(updated);
        if (updated.status === 'FAILED') {
          setPhase('failed');
          setError('The payment could not be completed.');
        } else {
          // Verified but not captured yet (UPI authorised): wait for the webhook.
          setPhase('waiting');
        }
      } catch (err) {
        // Not confirmed YET is not the same as failed: Razorpay's webhook may
        // still finalize it, so poll instead of claiming the money is gone.
        setError(errorMessage(err, 'We could not confirm the payment yet.'));
        setPhase('waiting');
      } finally {
        setBusy(false);
      }
    },
    [finishSuccess, mergePayment]
  );

  const openRazorpay = useCallback(async () => {
    const checkout = payment;
    if (
      !checkout?.razorpay_key_id ||
      !checkout.razorpay_order_id ||
      !checkout.amount_paise
    ) {
      setError('This checkout has no Razorpay order. Close it and try again.');
      return;
    }
    setPhase('opening');
    setBusy(true);
    setError(null);
    try {
      await loadRazorpayCheckout();
      const Checkout = window.Razorpay;
      if (!Checkout) {
        throw new Error('The payment window is unavailable right now.');
      }
      const instance = new Checkout({
        // PUBLIC values only: key id, order id, paise amount, currency.
        key: checkout.razorpay_key_id,
        amount: checkout.amount_paise,
        currency: checkout.currency,
        name: 'Scholaris',
        description: plan
          ? `${plan.name} - ${formatDuration(plan.duration_value, plan.duration_unit)}`
          : undefined,
        order_id: checkout.razorpay_order_id,
        prefill: {},
        notes: plan ? { plan: String(plan.id) } : undefined,
        theme: { color: '#4f46e5' },
        // UPI only - every other instrument is switched off client-side too,
        // and the SERVER independently rejects a non-UPI payment.
        method: {
          upi: true,
          card: false,
          netbanking: false,
          wallet: false,
          emi: false,
          paylater: false,
          cardless: false,
        },
        config: {
          display: {
            blocks: {
              upi: { name: 'Pay via UPI', instruments: [{ method: 'upi' }] },
            },
            sequence: ['upi'],
            hide: [
              {
                method: ['card', 'netbanking', 'wallet', 'emi', 'paylater', 'cardless'],
              },
            ],
            preferences: { default_block: 'upi' },
          },
        },
        handler: (result) => {
          void handleRazorpayResult(result);
        },
        modal: {
          ondismiss: () => {
            setPhase('dismissed');
            setBusy(false);
          },
          confirm_close: true,
          animation: true,
        },
      });
      instance.open();
      // Stay in 'opening' while Razorpay's own window owns the flow: the
      // handler moves us to 'verifying' and `modal.ondismiss` to 'dismissed'
      // (which offers a retry), so this button cannot be double-clicked.
      setBusy(false);
    } catch (err) {
      setPhase('idle');
      setBusy(false);
      setError(errorMessage(err, 'Could not open the payment window.'));
    }
  }, [handleRazorpayResult, payment, plan]);

  // UPI approval is asynchronous: while we are waiting, re-read OUR payment
  // row every few seconds instead of guessing. Stops after ~2 minutes.
  const paymentId = payment?.id ?? null;
  useEffect(() => {
    if (phase !== 'waiting' || paymentId === null) return;

    let cancelled = false;
    let attempts = 0;
    let timer: number | null = null;

    const stop = () => {
      if (timer !== null) {
        window.clearTimeout(timer);
        timer = null;
      }
    };

    const check = async () => {
      if (cancelled) return;
      attempts += 1;
      try {
        const latest = await subscriptionsService.getPayment(paymentId);
        if (cancelled) return;
        mergePayment(latest);
        if (latest.status === 'SUCCESS') {
          finishSuccess(latest);
          return;
        }
        if (latest.status === 'FAILED') {
          setPhase('failed');
          setError('The payment could not be completed.');
          return;
        }
      } catch {
        // A transient read error must not end the wait - keep polling until
        // the time budget below is spent.
      }
      if (attempts >= MAX_POLL_ATTEMPTS) {
        setPhase('timeout');
        return;
      }
      timer = window.setTimeout(() => {
        void check();
      }, POLL_INTERVAL_MS);
    };

    // A user coming back from their UPI app should not wait another cycle.
    const onVisibility = () => {
      if (document.visibilityState !== 'visible') return;
      stop();
      void check();
    };
    document.addEventListener('visibilitychange', onVisibility);

    void check();

    return () => {
      cancelled = true;
      stop();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [finishSuccess, mergePayment, paymentId, phase]);

  /* ---------------------------------------------------------------------
   * Mock provider (development)
   * ------------------------------------------------------------------ */

  const settle = async (outcome: MockCheckoutOutcome) => {
    if (!payment) return;
    setSettling(outcome);
    setError(null);
    try {
      const updated = await subscriptionsService.completeMockCheckout(payment.id, outcome);
      mergePayment(updated);
      onSettled?.(updated);
      // Let the app-wide access state re-read immediately.
      window.dispatchEvent(new Event('scholaris:subscription-changed'));
      if (outcome === 'SUCCESS') {
        setPhase('success');
      }
    } catch (err) {
      setError(errorMessage(err, 'The provider rejected this checkout.'));
    } finally {
      setSettling(null);
    }
  };

  const cancelPayment = async () => {
    if (!payment) return;
    setSettling('CANCELLED');
    setError(null);
    try {
      const updated = await subscriptionsService.cancelPayment(payment.id);
      mergePayment(updated);
      onSettled?.(updated);
      window.dispatchEvent(new Event('scholaris:subscription-changed'));
      close();
    } catch (err) {
      setError(errorMessage(err, 'Could not cancel this checkout.'));
    } finally {
      setSettling(null);
    }
  };

  if (!open || !plan) return null;

  const settled = payment?.status !== undefined && payment.status !== 'PENDING';
  const locked = creating || busy || settling !== null;
  const statusRow = (text: string) => (
    <div className="flex items-center gap-2 rounded-xl bg-slate-50 border border-slate-200 p-3 text-xs text-slate-600">
      <Loader2 className="w-4 h-4 animate-spin text-slate-400 flex-shrink-0" />
      <span>{text}</span>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
      <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs" onClick={locked ? undefined : close} />

      <div className="relative z-50 w-full max-w-sm bg-white rounded-2xl shadow-xl overflow-hidden p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="p-2.5 rounded-full bg-[var(--brand-light)] text-[var(--brand)]">
            <CreditCard className="w-5 h-5" />
          </div>
          <button
            onClick={close}
            disabled={locked}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 disabled:opacity-50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <h3 className="text-base font-bold text-slate-900 mb-1">{plan.name}</h3>
        <p className="text-xs text-slate-500 mb-4">
          {formatPrice(plan.price, plan.currency)} · {formatDuration(plan.duration_value, plan.duration_unit)}
        </p>

        {creating && statusRow('Creating a pending payment…')}

        {payment && !creating && (
          <div className="rounded-xl bg-slate-50 border border-slate-200 p-3 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between gap-3">
              <span>Order</span>
              <span className="font-mono text-slate-800 truncate">{payment.provider_order_id}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span>Provider</span>
              <span className="font-mono text-slate-800">{payment.provider}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span>Status</span>
              <span className="font-semibold text-slate-800">{payment.status}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span>Amount</span>
              <span className="font-semibold text-slate-800">
                {formatPrice(payment.amount, payment.currency)}
              </span>
            </div>
          </div>
        )}

        {!showMock && !isRazorpay && (
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3">
            <AlertTriangle className="w-4 h-4 text-amber-700 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-900 leading-relaxed">
              Online payments are disabled in this environment. The mock checkout is only
              available outside production - nothing can be simulated here.
            </p>
          </div>
        )}

        {error && phase !== 'dismissed' && phase !== 'failed' && (
          <div className="mt-3 rounded-xl bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
            {error}
          </div>
        )}

        {/* ── Razorpay (UPI) ─────────────────────────────────────────── */}
        {isRazorpay && payment && !creating && (
          <div className="mt-4 space-y-2">
            {phase === 'idle' && (
              <button
                type="button"
                onClick={() => void openRazorpay()}
                disabled={locked}
                className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center justify-center gap-2 active:scale-98 disabled:opacity-50 transition-all"
              >
                <Smartphone className="w-4 h-4" />
                Pay {formatPrice(payment.amount, payment.currency)} via UPI
              </button>
            )}

            {phase === 'opening' && statusRow('Opening the payment window…')}
            {phase === 'verifying' && statusRow('Confirming your payment…')}

            {phase === 'waiting' && (
              <div className="rounded-xl bg-slate-50 border border-slate-200 p-3 text-xs text-slate-600 space-y-1">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                  <span className="font-bold text-slate-800">Waiting for UPI confirmation</span>
                </div>
                <p className="leading-relaxed">
                  Approve the request in your UPI app. Your plan is activated automatically as
                  soon as the payment is confirmed - you can keep this window open.
                </p>
              </div>
            )}

            {phase === 'timeout' && (
              <div className="rounded-xl bg-sky-50 border border-sky-200 p-3 text-xs text-sky-900 space-y-2">
                <p className="leading-relaxed">
                  We&apos;ll activate your plan automatically once the payment is confirmed. Check
                  back shortly.
                </p>
                <button
                  type="button"
                  onClick={() => setPhase('waiting')}
                  className="w-full py-2 rounded-lg bg-white border border-sky-200 text-sky-800 font-semibold text-xs hover:bg-sky-100 transition-all"
                >
                  Check again
                </button>
              </div>
            )}

            {phase === 'dismissed' && (
              <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 text-xs space-y-1">
                <p className="font-bold text-amber-900">Payment not completed</p>
                <p className="text-amber-800 leading-relaxed">
                  The payment window was closed before the payment finished. Nothing was charged
                  for this order - you can try again whenever you are ready.
                </p>
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => void openRazorpay()}
                    className="py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-[11px] active:scale-98 transition-all"
                  >
                    Try again
                  </button>
                  <button
                    type="button"
                    onClick={close}
                    className="py-2 rounded-xl bg-white border border-amber-200 text-amber-900 font-semibold text-[11px] hover:bg-amber-100 transition-all"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}

            {phase === 'failed' && (
              <div className="rounded-xl bg-rose-50 border border-rose-200 p-3 text-xs space-y-1">
                <div className="flex items-center gap-1.5">
                  <XCircle className="w-3.5 h-3.5 text-rose-600" />
                  <span className="font-bold text-rose-900">Payment failed</span>
                </div>
                <p className="text-rose-800 leading-relaxed">
                  {error || 'The payment could not be completed. No money was captured.'}
                </p>
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => void openRazorpay()}
                    className="py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-[11px] active:scale-98 transition-all"
                  >
                    Try again
                  </button>
                  <button
                    type="button"
                    onClick={close}
                    className="py-2 rounded-xl bg-white border border-rose-200 text-rose-800 font-semibold text-[11px] hover:bg-rose-100 transition-all"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}

            {phase === 'success' && (
              <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3 text-xs space-y-1">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="font-bold text-emerald-900">Payment received</span>
                </div>
                <p className="text-emerald-800 leading-relaxed">
                  Your subscription is active. A receipt is available in your payment history.
                </p>
                <button
                  type="button"
                  onClick={close}
                  className="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[11px] active:scale-98 transition-all"
                >
                  Done
                </button>
              </div>
            )}

            {(phase === 'idle' || phase === 'opening') && (
              <p className="text-[11px] text-slate-400 text-center">
                UPI only - you complete the payment in your UPI app.
              </p>
            )}
          </div>
        )}

        {/* ── INTERNAL mock provider (development) ───────────────────── */}
        {showMock && payment && !creating && !settled && phase === 'idle' && (
          <div className="mt-4 space-y-2">
            <p className="text-[11px] text-slate-400 text-center">
              Development provider - choose the outcome to simulate.
            </p>
            <div className="grid grid-cols-2 gap-2">
              {OUTCOMES.map((item) => (
                <button
                  key={item.outcome}
                  type="button"
                  disabled={settling !== null || creating}
                  onClick={() => settle(item.outcome)}
                  className={`flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-white font-bold text-[11px] active:scale-98 disabled:opacity-50 transition-all ${item.className}`}
                >
                  {settling === item.outcome ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    item.icon
                  )}
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
            <button
              type="button"
              disabled={settling !== null}
              onClick={cancelPayment}
              className="w-full py-2 rounded-lg text-xs font-semibold text-slate-500 hover:bg-slate-50 transition-all"
            >
              Cancel this checkout
            </button>
          </div>
        )}

        {showMock && settled && phase !== 'success' && (
          <div className="mt-4">
            <p className="text-xs text-slate-600 text-center mb-3">
              Checkout finished with status <span className="font-bold">{payment?.status}</span>.
            </p>
            <button
              type="button"
              onClick={close}
              className="w-full py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-all"
            >
              Close
            </button>
          </div>
        )}

        {showMock && phase === 'success' && (
          <div className="mt-4">
            <button
              type="button"
              onClick={close}
              className="w-full py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-all"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CheckoutDialog;
