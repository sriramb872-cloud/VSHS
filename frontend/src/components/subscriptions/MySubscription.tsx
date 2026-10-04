// src/components/subscriptions/MySubscription.tsx
/**
 * Self-service subscription screen (student / teacher / principal).
 *
 * Rendered by the three role pages so there is exactly one implementation of
 * "what is my status, what can I buy, what have I paid". It reads ONLY real
 * backend data - `GET /subscription/me`, `/me/plans`, `/me/history` and
 * `/me/payments`; there is no local fixture anywhere in this file.
 *
 * This screen is reachable even when access is denied: it is the destination
 * the lock screen sends people to, so it must never itself be gated.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { CalendarClock, CreditCard, History, Receipt, ShieldCheck, Sparkles } from 'lucide-react';
import {
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from '../shared';
import { subscriptionsService } from '../../services/subscriptions';
import { errorMessage } from '../../helpers/errorMessage';
import type {
  AccessStatus,
  MePlans,
  MeSubscription,
  Subscription,
  SubscriptionPayment,
  SubscriptionPlan,
} from '../../types/subscription';
import { AccessBadge } from './AccessBadge';
import { CheckoutDialog } from './CheckoutDialog';
import { PlanCard } from './PlanCard';
import {
  accessSummary,
  formatDate,
  formatDateTime,
  formatDuration,
  formatPrice,
  reasonLabel,
} from './format';

export const MySubscription: React.FC = () => {
  const [me, setMe] = useState<MeSubscription | null>(null);
  const [plans, setPlans] = useState<MePlans | null>(null);
  const [history, setHistory] = useState<Subscription[]>([]);
  const [payments, setPayments] = useState<SubscriptionPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlan | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [meData, plansData, historyData, paymentsData] = await Promise.all([
        subscriptionsService.me(),
        subscriptionsService.myPlans(),
        subscriptionsService.myHistory(),
        subscriptionsService.myPayments(),
      ]);
      setMe(meData);
      setPlans(plansData);
      setHistory(historyData.items);
      setPayments(paymentsData.items);
    } catch (err) {
      setError(errorMessage(err, 'Could not load your subscription.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onCheckoutSettled = useCallback(() => {
    void load();
    window.dispatchEvent(new Event('scholaris:subscription-changed'));
  }, [load]);

  if (loading && !me) return <LoadingSkeleton type="list" count={4} />;
  if (error && !me) return <ErrorState title="Subscription" message={error} onRetry={load} />;

  const access: AccessStatus | null = me?.access ?? null;
  const enabled = plans?.subscriptions_enabled ?? access?.subscriptions_enabled ?? false;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Subscription</h1>
        <p className="text-xs text-slate-500">Your access status, plans and payment history</p>
      </div>

      {/* ── Status ──────────────────────────────────────────────────── */}
      {access && (
        <div
          className={`rounded-2xl border p-4 ${
            access.has_access
              ? 'bg-emerald-50/60 border-emerald-200/70'
              : 'bg-amber-50/70 border-amber-200/70'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <AccessBadge status={access.status} access={access} />
                <span className="text-xs font-semibold text-slate-700">
                  {accessSummary(access)}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-1.5">{reasonLabel(access.reason)}</p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {me?.school_name ? `${me.school_name} · ` : ''}
                {me?.role}
              </p>
            </div>
            <ShieldCheck
              className={`w-5 h-5 flex-shrink-0 ${access.has_access ? 'text-emerald-600' : 'text-amber-600'}`}
            />
          </div>

          <dl className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
            {access.plan && (
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Plan</dt>
                <dd className="font-semibold text-slate-800">
                  {access.plan.name} · {formatDuration(access.plan.duration_value, access.plan.duration_unit)}
                </dd>
              </div>
            )}
            {access.expires_at && (
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Expires</dt>
                <dd className="font-semibold text-slate-800">{formatDateTime(access.expires_at)}</dd>
              </div>
            )}
            {access.school_free_until && (
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">School free until</dt>
                <dd className="font-semibold text-slate-800">{formatDate(access.school_free_until)}</dd>
              </div>
            )}
            {access.user_free_until && (
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Your free access until</dt>
                <dd className="font-semibold text-slate-800">{formatDate(access.user_free_until)}</dd>
              </div>
            )}
            <div className="flex justify-between gap-2">
              <dt className="text-slate-500">Subscriptions</dt>
              <dd className="font-semibold text-slate-800">
                {enabled ? 'Enabled for this school' : 'Switched off for this school'}
              </dd>
            </div>
          </dl>

          {!access.has_access && (
            <div className="mt-3 rounded-xl bg-white/70 border border-amber-200 p-3 text-xs text-slate-700 leading-relaxed">
              Attendance, homework, exams, marks, timetable, report cards and the calendar are
              locked until access is restored. Everything else - your profile, settings,
              notifications and this page - keeps working.
            </div>
          )}
        </div>
      )}

      {/* ── Plans ───────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Plans</h2>
        </div>

        {!enabled ? (
          <EmptyState
            title="Subscriptions are off"
            description="Your school has not switched on subscriptions, so there is nothing to purchase right now."
            icon={<CreditCard className="w-10 h-10 text-slate-300" />}
          />
        ) : !plans || plans.plans.length === 0 ? (
          <EmptyState
            title="No plans available"
            description="Your school has not published a plan for your role yet. Contact your administrator."
            icon={<CreditCard className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {plans.plans.map((plan) => (
                <PlanCard
                  key={plan.id}
                  plan={plan}
                  onSelect={setSelectedPlan}
                  footnote={
                    access?.plan?.id === plan.id && access?.expires_at
                      ? `Current plan · active until ${formatDate(access.expires_at)}`
                      : undefined
                  }
                />
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-3">
              {plans.mock_payments_enabled
                ? `Checkout runs through the ${plans.payment_provider} development provider. Payment details are verified on the server before access changes.`
                : 'Online payments are switched off in this environment, so checkout is unavailable.'}
            </p>
          </>
        )}
      </section>

      {/* ── History ─────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <History className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Subscription history</h2>
        </div>
        {history.length === 0 ? (
          <EmptyState
            title="No subscriptions yet"
            description="Grants and purchases will appear here."
            icon={<History className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {history.map((row) => (
              <li key={row.id} className="py-2.5 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-slate-800">
                      {row.plan?.name || 'Manual entitlement'}
                    </span>
                    <AccessBadge status={row.status} />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {formatDate(row.start_at)} → {formatDate(row.end_at)} · {row.source}
                  </p>
                </div>
                <span className="text-xs font-semibold text-slate-700 flex-shrink-0">
                  {row.amount !== null && row.amount !== undefined
                    ? formatPrice(Number(row.amount), row.currency)
                    : '—'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Payments ────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <Receipt className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Payments</h2>
        </div>
        {payments.length === 0 ? (
          <EmptyState
            title="No payments yet"
            description="Checkout attempts and their provider outcomes appear here."
            icon={<Receipt className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {payments.map((row) => (
              <li key={row.id} className="py-2.5 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-slate-800">{row.provider}</span>
                    <AccessBadge status={row.status} />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {formatDateTime(row.created_at)}
                    {row.paid_at ? ` · paid ${formatDateTime(row.paid_at)}` : ''}
                  </p>
                  <p className="text-[11px] text-slate-400 font-mono truncate">
                    {row.provider_order_id}
                  </p>
                </div>
                <span className="text-xs font-semibold text-slate-700 flex-shrink-0">
                  {formatPrice(row.amount, row.currency)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="flex items-center gap-2 text-[11px] text-slate-400">
        <CalendarClock className="w-3.5 h-3.5" />
        <span>
          All timestamps are UTC. Access is recalculated on every request - no scheduled job is
          involved.
        </span>
      </div>

      <CheckoutDialog
        open={!!selectedPlan}
        plan={selectedPlan}
        mockEnabled={plans?.mock_payments_enabled ?? false}
        paymentProvider={plans?.payment_provider ?? 'INTERNAL'}
        onClose={() => setSelectedPlan(null)}
        onSettled={onCheckoutSettled}
      />
    </div>
  );
};

export default MySubscription;
