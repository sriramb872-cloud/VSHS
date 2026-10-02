// src/pages/superadmin/SubscriptionUser.tsx
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  CalendarClock,
  Clock,
  FileText,
  Gift,
  Loader2,
  Power,
  Receipt,
  RefreshCw,
  Save,
  UserCheck,
} from 'lucide-react';
import { ConfirmDialog, EmptyState, ErrorState, LoadingSkeleton } from '../../components/shared';
import { AccessBadge } from '../../components/subscriptions/AccessBadge';
import {
  formatDateTime,
  formatDate,
  formatDuration,
  fromDateTimeLocal,
  toDateTimeLocal,
} from '../../components/subscriptions/format';
import { subscriptionsService } from '../../services/subscriptions';
import { errorMessage } from '../../helpers/errorMessage';
import type {
  DurationUnit,
  SubscriptionPlan,
  UserSubscriptionDetail,
} from '../../types/subscription';

type ManualAction = 'grant' | 'extend' | 'suspend' | 'restore' | 'cancel';

const ACTION_LABELS: Record<ManualAction, string> = {
  grant: 'Grant',
  extend: 'Extend',
  suspend: 'Suspend',
  restore: 'Restore',
  cancel: 'Cancel',
};

/**
 * Super Admin > one user's subscription record.
 *
 * Everything shown is read from `GET /subscription/users/{id}` - the resolver's
 * own verdict, the stored entitlements, the individual override, the payment
 * rows and the audit trail. The manual operations are the ones the ops team
 * actually needs (grant / extend / cancel / suspend / restore plus a free
 * override), and each of them is confirmed before it is sent because every one
 * writes an immutable audit row.
 *
 * The account state (`users.is_active`) is deliberately NOT part of this page:
 * subscription state and account state are different concerns and the backend
 * never conflates them.
 */
export const SuperAdminSubscriptionUser: React.FC = () => {
  const navigate = useNavigate();
  const { schoolId, userId } = useParams<{ schoolId: string; userId: string }>();
  const id = Number(schoolId);
  const uid = Number(userId);

  const [detail, setDetail] = useState<UserSubscriptionDetail | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [grantPlanId, setGrantPlanId] = useState<number | ''>('');
  const [extendPlanId, setExtendPlanId] = useState<number | ''>('');
  const [extendValue, setExtendValue] = useState(1);
  const [extendUnit, setExtendUnit] = useState<DurationUnit>('MONTH');
  const [reason, setReason] = useState('');

  const [freeUntil, setFreeUntil] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [dirtyOverride, setDirtyOverride] = useState(false);

  const [pending, setPending] = useState<ManualAction | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!Number.isFinite(uid)) {
      setError('Unknown user.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await subscriptionsService.getUserDetail(uid);
      setDetail(data);
      setFreeUntil(toDateTimeLocal(data.override?.free_until));
      setOverrideReason(data.override?.reason || '');
      setDirtyOverride(false);
      // Plans are scoped server-side to the user's school + role, so the
      // pickers below can only ever offer valid choices.
      if (data.school_id) {
        const rolePlans = await subscriptionsService.getSchoolRole(
          data.school_id,
          data.role
        );
        setPlans(rolePlans.plans);
      } else {
        setPlans([]);
      }
    } catch (err) {
      setError(errorMessage(err, 'Could not load this user.'));
    } finally {
      setLoading(false);
    }
  }, [uid]);

  useEffect(() => {
    void load();
  }, [load]);

  const activePlans = useMemo(() => plans.filter((plan) => plan.is_active), [plans]);

  const run = async (action: ManualAction) => {
    setPending(null);
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const trimmed = reason.trim() || undefined;
      switch (action) {
        case 'grant': {
          if (!grantPlanId) return;
          await subscriptionsService.grant(uid, {
            plan_id: Number(grantPlanId),
            reason: trimmed,
          });
          setNotice('Subscription granted and audited.');
          break;
        }
        case 'extend': {
          const payload: Parameters<typeof subscriptionsService.extend>[1] = {};
          if (extendPlanId) payload.plan_id = Number(extendPlanId);
          else {
            payload.duration_value = Number(extendValue);
            payload.duration_unit = extendUnit;
          }
          payload.reason = trimmed;
          await subscriptionsService.extend(uid, payload);
          setNotice('Subscription extended and audited.');
          break;
        }
        case 'suspend':
          await subscriptionsService.suspend(uid, { reason: trimmed });
          setNotice('Subscription suspended. The account itself is untouched.');
          break;
        case 'restore':
          await subscriptionsService.restore(uid, { reason: trimmed });
          setNotice('Subscription restored and audited.');
          break;
        case 'cancel':
          await subscriptionsService.cancel(uid, { reason: trimmed });
          setNotice('Subscription cancelled. Paid time before the end date is preserved.');
          break;
      }
      setReason('');
      await load();
      window.dispatchEvent(new Event('scholaris:subscription-changed'));
    } catch (err) {
      setError(errorMessage(err, `Could not ${action} the subscription.`));
    } finally {
      setBusy(false);
    }
  };

  const saveOverride = async () => {
    if (!detail) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const payload = {
        free_until: fromDateTimeLocal(freeUntil),
        reason: overrideReason.trim() || undefined,
      };
      if (detail.override) {
        await subscriptionsService.updateOverride(uid, payload);
      } else {
        await subscriptionsService.createOverride(uid, {
          override_type: 'FREE',
          free_until: payload.free_until,
          reason: payload.reason,
        });
      }
      setNotice('Free override saved and audited.');
      setDirtyOverride(false);
      await load();
      window.dispatchEvent(new Event('scholaris:subscription-changed'));
    } catch (err) {
      setError(errorMessage(err, 'Could not save the free override.'));
    } finally {
      setBusy(false);
    }
  };

  const removeOverride = async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await subscriptionsService.removeOverride(uid);
      setNotice('Free override removed.');
      setDirtyOverride(false);
      await load();
      window.dispatchEvent(new Event('scholaris:subscription-changed'));
    } catch (err) {
      setError(errorMessage(err, 'Could not remove the free override.'));
    } finally {
      setBusy(false);
      setPending(null);
    }
  };

  if (loading && !detail) return <LoadingSkeleton type="list" count={4} />;

  if (!detail && error) {
    return (
      <div className="space-y-4">
        <ErrorState title="Could not load this user" message={error} onRetry={load} />
        <button
          type="button"
          onClick={() => navigate(`/superadmin/subscriptions/${id}`)}
          className="text-xs font-semibold text-slate-500 hover:text-slate-700"
        >
          ← Back to school
        </button>
      </div>
    );
  }

  const access = detail?.access;
  const rolePlans = activePlans;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <button
            type="button"
            onClick={() => navigate(`/superadmin/subscriptions/${id}`)}
            className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-700 mb-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>{detail?.school_name || 'Back to school'}</span>
          </button>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-slate-900 truncate">
              {detail?.display_name || 'User'}
            </h1>
            {access && <AccessBadge status={access.status} access={access} />}
          </div>
          <p className="text-xs text-slate-500">
            {detail?.role} · {detail?.mobile} · user #{detail?.user_id}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs transition-all flex-shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorState title="Something went wrong" message={error} onRetry={load} />}
      {notice && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-3.5 py-2.5 text-xs text-emerald-800">
          {notice}
        </div>
      )}

      {/* ── Access verdict ──────────────────────────────────────── */}
      {access && (
        <section
          className={`rounded-2xl border p-4 ${
            access.has_access
              ? 'bg-emerald-50/60 border-emerald-200/70'
              : 'bg-amber-50/70 border-amber-200/70'
          }`}
        >
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-slate-600" />
            <h2 className="text-sm font-bold text-slate-900">Resolved access</h2>
          </div>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-5 gap-y-1.5 text-xs">
            <div className="flex justify-between gap-2">
              <dt className="text-slate-500">Has access</dt>
              <dd className="font-semibold text-slate-800">{access.has_access ? 'Yes' : 'No'}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-slate-500">Reason</dt>
              <dd className="font-semibold text-slate-800">{access.reason}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-slate-500">Plan</dt>
              <dd className="font-semibold text-slate-800">
                {access.plan
                  ? `${access.plan.name} · ${formatDuration(
                      access.plan.duration_value,
                      access.plan.duration_unit
                    )}`
                  : '—'}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-slate-500">Expires</dt>
              <dd className="font-semibold text-slate-800">
                {formatDateTime(access.expires_at)}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-slate-500">School free until</dt>
              <dd className="font-semibold text-slate-800">
                {formatDateTime(access.school_free_until)}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-slate-500">User free until</dt>
              <dd className="font-semibold text-slate-800">
                {formatDateTime(access.user_free_until)}
              </dd>
            </div>
          </dl>
          <p className="text-[11px] text-slate-500 mt-2">
            This is the server's answer, recomputed from the database on this request - no cron,
            no cached flag. The account state is separate and untouched by anything below.
          </p>
        </section>
      )}

      {/* ── Manual operations ───────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-1">
          <Gift className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Manual operations</h2>
        </div>
        <p className="text-[11px] text-slate-500 mb-3">
          Every action below writes an audit row with your identity and reason, and is applied
          transactionally.
        </p>

        {rolePlans.length === 0 ? (
          <div className="rounded-xl bg-slate-50 border border-dashed border-slate-200 p-3.5 text-xs text-slate-500">
            This school has no active plan for a {detail?.role?.toLowerCase()} yet, so there is
            nothing to grant. Create one on the role page first, or use the free override below.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="rounded-xl border border-slate-200 p-3 space-y-2">
              <span className="text-[11px] font-semibold text-slate-600">Grant a plan</span>
              <select
                value={grantPlanId}
                onChange={(event) =>
                  setGrantPlanId(event.target.value ? Number(event.target.value) : '')
                }
                className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Choose a plan…</option>
                {rolePlans.map((plan) => (
                  <option key={plan.id} value={plan.id}>
                    {plan.name} · {plan.price} {plan.currency} / {plan.duration_value}{' '}
                    {plan.duration_unit}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={!grantPlanId || busy}
                onClick={() => setPending('grant')}
                className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs transition-all"
              >
                <UserCheck className="w-4 h-4" />
                <span>Grant</span>
              </button>
            </div>

            <div className="rounded-xl border border-slate-200 p-3 space-y-2">
              <span className="text-[11px] font-semibold text-slate-600">Extend</span>
              <select
                value={extendPlanId}
                onChange={(event) =>
                  setExtendPlanId(event.target.value ? Number(event.target.value) : '')
                }
                className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Custom duration…</option>
                {rolePlans.map((plan) => (
                  <option key={plan.id} value={plan.id}>
                    {plan.name} (+{plan.duration_value} {plan.duration_unit})
                  </option>
                ))}
              </select>
              {!extendPlanId && (
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    value={extendValue}
                    onChange={(event) => setExtendValue(Number(event.target.value))}
                    className="w-24 h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <select
                    value={extendUnit}
                    onChange={(event) => setExtendUnit(event.target.value as DurationUnit)}
                    className="flex-1 h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="DAY">Days</option>
                    <option value="MONTH">Months</option>
                    <option value="YEAR">Years</option>
                  </select>
                </div>
              )}
              <button
                type="button"
                disabled={busy}
                onClick={() => setPending('extend')}
                className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs transition-all"
              >
                <Clock className="w-4 h-4" />
                <span>Extend</span>
              </button>
            </div>
          </div>
        )}

        <label className="block mt-3">
          <span className="text-[11px] font-semibold text-slate-600">
            Reason (optional, recorded in the audit log)
          </span>
          <input
            type="text"
            maxLength={500}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="e.g. scholarship waiver for the autumn term"
            className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </label>

        <div className="flex flex-wrap items-center gap-2 mt-3">
          <button
            type="button"
            disabled={busy}
            onClick={() => setPending('suspend')}
            className="px-4 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-bold text-xs transition-all"
          >
            Suspend
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => setPending('restore')}
            className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold text-xs transition-all"
          >
            Restore
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => setPending('cancel')}
            className="px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white font-bold text-xs transition-all"
          >
            Cancel subscription
          </button>
        </div>
      </section>

      {/* ── Individual free override ────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-1">
          <CalendarClock className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Individual free override</h2>
        </div>
        <p className="text-[11px] text-slate-500 mb-3">
          A per-user free window that sits above any role plan. Removing it never touches a paid
          subscription.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[11px] font-semibold text-slate-600">Free access until (UTC)</span>
            <input
              type="datetime-local"
              value={freeUntil}
              onChange={(event) => {
                setFreeUntil(event.target.value);
                setDirtyOverride(true);
              }}
              className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <span className="block mt-1 text-[11px] text-slate-400">
              {detail?.override?.free_until
                ? `Currently: ${formatDateTime(detail.override.free_until)}.`
                : 'No override on this user.'}{' '}
              Empty = remove the window.
            </span>
          </label>
          <label className="block">
            <span className="text-[11px] font-semibold text-slate-600">Reason (audited)</span>
            <input
              type="text"
              maxLength={500}
              value={overrideReason}
              onChange={(event) => {
                setOverrideReason(event.target.value);
                setDirtyOverride(true);
              }}
              className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-3">
          <button
            type="button"
            disabled={busy}
            onClick={() => void saveOverride()}
            className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-white font-bold text-xs transition-all ${
              dirtyOverride ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-slate-300'
            }`}
          >
            <Save className="w-4 h-4" />
            <span>{detail?.override ? 'Update override' : 'Create override'}</span>
          </button>
          {detail?.override && (
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                if (
                  window.confirm(
                    'Remove the individual free override from this user? Their paid subscription, if any, is unaffected.'
                  )
                ) {
                  void removeOverride();
                }
              }}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-all"
            >
              <Power className="w-4 h-4" />
              <span>Remove override</span>
            </button>
          )}
        </div>
      </section>

      {/* ── History ─────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Subscription history</h2>
        </div>
        {!detail || detail.history.length === 0 ? (
          <EmptyState
            title="No entitlements yet"
            description="Grants and payments will appear here."
            icon={<FileText className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {detail.history.map((row) => (
              <li key={row.id} className="py-2.5 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-slate-800">
                      {row.plan?.name || 'Manual entitlement'}
                    </span>
                    <AccessBadge status={row.status} />
                    <span className="text-[11px] text-slate-400">{row.source}</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {formatDateTime(row.start_at)} → {formatDateTime(row.end_at)}
                  </p>
                </div>
                <span className="text-xs font-semibold text-slate-700 flex-shrink-0">
                  {row.amount !== null && row.amount !== undefined
                    ? `${row.amount} ${row.currency || ''}`
                    : '—'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Payments ────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <Receipt className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Payments</h2>
        </div>
        {!detail || detail.payments.length === 0 ? (
          <EmptyState
            title="No payments"
            description="Checkout attempts for this user will appear here."
            icon={<Receipt className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {detail.payments.map((row) => (
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
                  {row.amount} {row.currency}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Audit ───────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Audit trail</h2>
        </div>
        {!detail || detail.audit.length === 0 ? (
          <EmptyState
            title="No audit entries"
            description="Access and billing changes for this user are recorded here."
            icon={<FileText className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {detail.audit.map((row) => (
              <li key={row.id} className="py-2.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-semibold text-slate-800">
                    {row.action.replace(/_/g, ' ')}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    {formatDate(row.created_at)}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-0.5 font-mono break-all">
                  {row.old_value || '—'} → {row.new_value || '—'}
                </p>
                {row.reason && (
                  <p className="text-[11px] text-slate-600 mt-0.5">Reason: {row.reason}</p>
                )}
                {row.admin_id && (
                  <p className="text-[11px] text-slate-400 mt-0.5">by admin #{row.admin_id}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <ConfirmDialog
        isOpen={pending !== null && pending !== 'cancel'}
        title={`${ACTION_LABELS[pending as ManualAction] || ''} this subscription?`}
        message={
          pending === 'grant'
            ? 'This grants a full entitlement immediately and writes an audit row.'
            : pending === 'extend'
              ? 'The subscription is extended from its existing end date, so no paid time is lost. An audit row is written.'
              : pending === 'suspend'
                ? 'Access is paused for the gated modules. The user account itself is NOT deactivated.'
                : 'The subscription is restored to ACTIVE and audited.'
        }
        confirmLabel={ACTION_LABELS[pending as ManualAction] || 'Confirm'}
        isDanger={pending === 'suspend'}
        onConfirm={() => pending && void run(pending)}
        onCancel={() => setPending(null)}
        isLoading={busy}
      />

      <ConfirmDialog
        isOpen={pending === 'cancel'}
        title="Cancel this subscription?"
        message="The row is marked CANCELLED and stops granting access. All previously paid time and the full history are preserved - nothing is deleted."
        confirmLabel="Cancel subscription"
        isDanger
        onConfirm={() => void run('cancel')}
        onCancel={() => setPending(null)}
        isLoading={busy}
      />
    </div>
  );
};

export default SuperAdminSubscriptionUser;
