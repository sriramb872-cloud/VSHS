// src/components/subscriptions/CheckoutDialog.tsx
/**
 * Development checkout for the INTERNAL mock payment provider.
 *
 * Phase 1 ships a provider ABSTRACTION plus this signed mock: the client only
 * reports which outcome the simulated provider returned, and the server
 * verifies the signed payload (and re-reads the amount from the database)
 * before any subscription is activated. A client claim alone never grants
 * access.
 *
 * The whole simulated flow is gated by `mock_payments_enabled`, which the API
 * turns off when `ENVIRONMENT=production` (or `ENABLE_MOCK_PAYMENTS=0`) - in
 * that case this dialog renders an explicit "not available" state instead of
 * buttons that would only fail.
 *
 * RAZORPAY INTEGRATION WAS NOT IMPLEMENTED IN THIS PHASE: the same dialog will
 * host the real provider redirect later, behind the same
 * `createCheckout -> provider -> apply entitlement` flow.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CreditCard, Loader2, X, XCircle, CheckCircle2, Ban, Clock } from 'lucide-react';
import { subscriptionsService } from '../../services/subscriptions';
import { errorMessage } from '../../helpers/errorMessage';
import type {
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
  onClose: () => void;
  /** Called after any provider outcome so the caller can refresh `/me`. */
  onSettled?: (payment: SubscriptionPayment) => void;
}

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
    icon: <Ban className="w-3.5 h-3.5" />,
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
  onClose,
  onSettled,
}) => {
  const [payment, setPayment] = useState<SubscriptionPayment | null>(null);
  const [creating, setCreating] = useState(false);
  const [settling, setSettling] = useState<MockCheckoutOutcome | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setPayment(null);
    setCreating(false);
    setSettling(null);
    setError(null);
  }, []);

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
        if (!cancelled) setPayment(created);
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

  const close = () => {
    reset();
    onClose();
  };

  const settle = async (outcome: MockCheckoutOutcome) => {
    if (!payment) return;
    setSettling(outcome);
    setError(null);
    try {
      const updated = await subscriptionsService.completeMockCheckout(payment.id, outcome);
      setPayment(updated);
      onSettled?.(updated);
      // Let the app-wide access state re-read immediately.
      window.dispatchEvent(new Event('scholaris:subscription-changed'));
      if (outcome === 'SUCCESS') {
        window.setTimeout(close, 700);
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
      setPayment(updated);
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

  const settled = payment?.status && payment.status !== 'PENDING';

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
      <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs" onClick={creating ? undefined : close} />

      <div className="relative z-50 w-full max-w-sm bg-white rounded-2xl shadow-xl overflow-hidden p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="p-2.5 rounded-full bg-[var(--brand-light)] text-[var(--brand)]">
            <CreditCard className="w-5 h-5" />
          </div>
          <button
            onClick={close}
            disabled={creating || settling !== null}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 disabled:opacity-50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <h3 className="text-base font-bold text-slate-900 mb-1">{plan.name}</h3>
        <p className="text-xs text-slate-500 mb-4">
          {formatPrice(plan.price, plan.currency)} · {formatDuration(plan.duration_value, plan.duration_unit)}
        </p>

        {creating && (
          <div className="flex items-center gap-2 rounded-xl bg-slate-50 border border-slate-200 p-3 text-xs text-slate-600">
            <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
            <span>Creating a pending payment…</span>
          </div>
        )}

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

        {!mockEnabled && (
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3">
            <AlertTriangle className="w-4 h-4 text-amber-700 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-900 leading-relaxed">
              Online payments are disabled in this environment. The mock checkout is only
              available outside production - nothing can be simulated here.
            </p>
          </div>
        )}

        {error && (
          <div className="mt-3 rounded-xl bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
            {error}
          </div>
        )}

        {mockEnabled && payment && !settled && (
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

        {payment && settled && (
          <div className="mt-4">
            <p className="text-xs text-slate-600 text-center mb-3">
              Checkout finished with status <span className="font-bold">{payment.status}</span>.
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
      </div>
    </div>
  );
};

export default CheckoutDialog;
