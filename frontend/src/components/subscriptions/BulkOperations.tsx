// src/components/subscriptions/BulkOperations.tsx
/**
 * Bulk subscription operations for a school (Super Admin).
 *
 * The server runs each user inside its own SAVEPOINT within one outer
 * transaction, writes an audit row per success, and returns a per-user
 * failure summary - which is rendered verbatim here so a partially applied
 * bulk action is never mistaken for a full success.
 *
 * Selection is supplied by the parent (the user table owns the checkboxes);
 * this component owns the action form and the result report.
 */
import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, Layers, Loader2, Play, XCircle } from 'lucide-react';
import { ConfirmDialog } from '../shared';
import { subscriptionsService } from '../../services/subscriptions';
import { errorMessage } from '../../helpers/errorMessage';
import type {
  BulkAction,
  BulkOperationResponse,
  SubscriptionPlan,
} from '../../types/subscription';

interface BulkOperationsProps {
  schoolId: number;
  userIds: number[];
  /** Plans belonging to this school (used by ASSIGN_PLAN). */
  plans: SubscriptionPlan[];
  onDone: (result: BulkOperationResponse) => void;
  onClearSelection: () => void;
}

const ACTIONS: Array<{ value: BulkAction; label: string; needs: 'free' | 'plan' | 'duration' | null }> = [
  { value: 'FREE_UNTIL', label: 'Grant free access until…', needs: 'free' },
  { value: 'REMOVE_FREE', label: 'Remove free override', needs: null },
  { value: 'ASSIGN_PLAN', label: 'Assign a plan', needs: 'plan' },
  { value: 'EXTEND', label: 'Extend existing subscription', needs: 'duration' },
  { value: 'SUSPEND', label: 'Suspend', needs: null },
  { value: 'RESTORE', label: 'Restore', needs: null },
  { value: 'CANCEL', label: 'Cancel', needs: null },
];

const pad = (n: number): string => String(n).padStart(2, '0');

/** Default free window: 7 days from now (naive UTC, matching the API). */
const defaultFreeUntil = (): string => {
  const date = new Date(Date.now() + 7 * 86_400_000);
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(
    date.getUTCHours()
  )}:${pad(date.getUTCMinutes())}`;
};

export const BulkOperations: React.FC<BulkOperationsProps> = ({
  schoolId,
  userIds,
  plans,
  onDone,
  onClearSelection,
}) => {
  const [action, setAction] = useState<BulkAction>('FREE_UNTIL');
  const [freeUntil, setFreeUntil] = useState<string>(defaultFreeUntil);
  const [planId, setPlanId] = useState<number | ''>('');
  const [durationValue, setDurationValue] = useState(1);
  const [durationUnit, setDurationUnit] = useState<'DAY' | 'MONTH' | 'YEAR'>('MONTH');
  const [reason, setReason] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const spec = ACTIONS.find((item) => item.value === action) || ACTIONS[0];

  const buildPayload = () => {
    const payload: Parameters<typeof subscriptionsService.bulkOperation>[1] = {
      action,
      user_ids: userIds,
    };
    if (spec.needs === 'free') payload.free_until = freeUntil ? `${freeUntil}:00` : null;
    if (spec.needs === 'plan') payload.plan_id = Number(planId);
    if (spec.needs === 'duration') {
      payload.duration_value = Number(durationValue);
      payload.duration_unit = durationUnit;
    }
    if (reason.trim()) payload.reason = reason.trim();
    return payload;
  };

  const ready =
    userIds.length > 0 &&
    (spec.needs !== 'free' || !!freeUntil) &&
    (spec.needs !== 'plan' || !!planId) &&
    (spec.needs !== 'duration' || Number(durationValue) >= 1);

  const run = async () => {
    setConfirming(false);
    setRunning(true);
    setError(null);
    try {
      const result = await subscriptionsService.bulkOperation(schoolId, buildPayload());
      onDone(result);
      if (result.failed.length === 0) onClearSelection();
    } catch (err) {
      setError(errorMessage(err, 'The bulk operation could not be run.'));
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 mb-1">
        <Layers className="w-4 h-4 text-indigo-600" />
        <h2 className="text-sm font-bold text-slate-900">Bulk operations</h2>
        <span className="ml-auto text-[11px] text-slate-400">{userIds.length} selected</span>
      </div>
      <p className="text-[11px] text-slate-500 mb-3">
        Every selected user runs in its own savepoint inside one transaction: successes commit
        with an audit row, failures are reported per user and never half-applied.
      </p>

      {userIds.length === 0 ? (
        <div className="rounded-xl bg-slate-50 border border-dashed border-slate-200 p-4 text-xs text-slate-500 text-center">
          Select one or more users below to enable bulk actions.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="text-[11px] font-semibold text-slate-600">Action</span>
              <select
                value={action}
                onChange={(event) => setAction(event.target.value as BulkAction)}
                className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {ACTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>

            {spec.needs === 'free' && (
              <label className="block">
                <span className="text-[11px] font-semibold text-slate-600">Free until (UTC)</span>
                <input
                  type="datetime-local"
                  value={freeUntil}
                  onChange={(event) => setFreeUntil(event.target.value)}
                  className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </label>
            )}

            {spec.needs === 'plan' && (
              <label className="block">
                <span className="text-[11px] font-semibold text-slate-600">Plan</span>
                <select
                  value={planId}
                  onChange={(event) =>
                    setPlanId(event.target.value ? Number(event.target.value) : '')
                  }
                  className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Choose a plan…</option>
                  {plans.map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.name} · {plan.role} · {plan.price} {plan.currency} /{' '}
                      {plan.duration_value} {plan.duration_unit}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {spec.needs === 'duration' && (
              <div className="flex items-end gap-2">
                <label className="block flex-1">
                  <span className="text-[11px] font-semibold text-slate-600">Amount</span>
                  <input
                    type="number"
                    min={1}
                    value={durationValue}
                    onChange={(event) => setDurationValue(Number(event.target.value))}
                    className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </label>
                <label className="block w-32">
                  <span className="text-[11px] font-semibold text-slate-600">Unit</span>
                  <select
                    value={durationUnit}
                    onChange={(event) =>
                      setDurationUnit(event.target.value as 'DAY' | 'MONTH' | 'YEAR')
                    }
                    className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="DAY">Days</option>
                    <option value="MONTH">Months</option>
                    <option value="YEAR">Years</option>
                  </select>
                </label>
              </div>
            )}
          </div>

          <label className="block">
            <span className="text-[11px] font-semibold text-slate-600">Reason (optional, audited)</span>
            <input
              type="text"
              maxLength={500}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="e.g. Diwali credit for the whole section"
              className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </label>

          {error && (
            <div className="rounded-xl bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
              {error}
            </div>
          )}

          <button
            type="button"
            disabled={!ready || running}
            onClick={() => setConfirming(true)}
            className="flex items-center justify-center gap-1.5 w-full sm:w-auto px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 disabled:opacity-50 text-white font-bold text-xs transition-all"
          >
            {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>
              Run {spec.label.replace('…', '')} on {userIds.length}{' '}
              {userIds.length === 1 ? 'user' : 'users'}
            </span>
          </button>
        </div>
      )}

      <ConfirmDialog
        isOpen={confirming}
        title="Run bulk operation?"
        message={`This will apply "${spec.label}" to ${userIds.length} ${
          userIds.length === 1 ? 'user' : 'users'
        } in this school. Each change is audited, and any user that fails is reported individually.`}
        confirmLabel="Run"
        isDanger={action === 'CANCEL' || action === 'SUSPEND'}
        onConfirm={run}
        onCancel={() => setConfirming(false)}
        isLoading={running}
      />
    </section>
  );
};

interface BulkResultReportProps {
  result: BulkOperationResponse;
  onClose: () => void;
}

/** Renders the per-user summary the API returned - failures are not hidden. */
export const BulkResultReport: React.FC<BulkResultReportProps> = ({ result, onClose }) => {
  const ok = result.failed.length === 0;
  return (
    <section
      className={`rounded-2xl border p-4 ${
        ok ? 'bg-emerald-50/60 border-emerald-200/70' : 'bg-amber-50/70 border-amber-200/70'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          {ok ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-amber-700 mt-0.5" />
          )}
          <div className="text-xs text-slate-700">
            <p className="font-bold text-slate-900">
              {result.action.replace(/_/g, ' ')} · {result.succeeded.length} of{' '}
              {result.requested} applied
            </p>
            {!ok && (
              <p className="mt-0.5">
                {result.failed.length} failed - the successful users were still committed.
              </p>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-[11px] font-semibold text-slate-500 hover:text-slate-700"
        >
          Dismiss
        </button>
      </div>

      {result.failed.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {result.failed.map((failure) => (
            <li
              key={failure.user_id}
              className="flex items-start gap-2 text-xs text-rose-800 bg-white/70 rounded-lg px-2.5 py-2 border border-rose-200/70"
            >
              <XCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <span>
                <span className="font-mono">#{failure.user_id}</span> ·{' '}
                <span className="font-semibold">{failure.code}</span> - {failure.message}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

export default BulkOperations;
