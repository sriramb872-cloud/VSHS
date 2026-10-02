// src/pages/superadmin/SubscriptionRole.tsx
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, DollarSign, Loader2, Pencil, Plus, Power, Save } from 'lucide-react';
import { ConfirmDialog, EmptyState, ErrorState, LoadingSkeleton } from '../../components/shared';
import { AccessBadge } from '../../components/subscriptions/AccessBadge';
import { formatDate } from '../../components/subscriptions/format';
import { errorMessage } from '../../helpers/errorMessage';
import { subscriptionsService } from '../../services/subscriptions';
import type {
  BillingInterval,
  DurationUnit,
  SchoolRoleDetailResponse,
  SubscriptionPlan,
} from '../../types/subscription';

const DURATION_UNITS: DurationUnit[] = ['DAY', 'MONTH', 'YEAR'];
const BILLING_INTERVALS: BillingInterval[] = [
  'ONE_TIME',
  'WEEKLY',
  'MONTHLY',
  'QUARTERLY',
  'YEARLY',
  'CUSTOM',
];

interface PlanDraft {
  name: string;
  description: string;
  price: string;
  currency: string;
  billing_interval: BillingInterval;
  duration_value: string;
  duration_unit: DurationUnit;
}

const draftFrom = (plan: SubscriptionPlan): PlanDraft => ({
  name: plan.name,
  description: plan.description || '',
  price: String(plan.price),
  currency: plan.currency,
  billing_interval: plan.billing_interval as BillingInterval,
  duration_value: String(plan.duration_value),
  duration_unit: plan.duration_unit as DurationUnit,
});

const EMPTY_DRAFT: PlanDraft = {
  name: '',
  description: '',
  price: '',
  currency: 'INR',
  billing_interval: 'MONTHLY',
  duration_value: '1',
  duration_unit: 'MONTH',
};

const ROLE_TITLES: Record<string, string> = {
  PRINCIPAL: 'Principals',
  TEACHER: 'Teachers',
  STUDENT: 'Students',
};

/**
 * Super Admin > one role's plan catalogue for one school.
 *
 * Price, currency and duration are all free-form inputs validated by the
 * server (`INVALID_PRICE`, `INVALID_DURATION`, `INVALID_ROLE`) - nothing here
 * assumes a 30-day month or a fixed currency. Plans are deactivated, never
 * deleted, so payment history keeps pointing at something real.
 */
export const SuperAdminSubscriptionRole: React.FC = () => {
  const navigate = useNavigate();
  const { schoolId, role } = useParams<{ schoolId: string; role: string }>();
  const id = Number(schoolId);
  const roleKey = (role || '').toUpperCase();

  const [detail, setDetail] = useState<SchoolRoleDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [creating, setCreating] = useState(false);
  const [createDraft, setCreateDraft] = useState<PlanDraft>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<PlanDraft>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);
  const [deactivating, setDeactivating] = useState<SubscriptionPlan | null>(null);

  const load = useCallback(async () => {
    if (!Number.isFinite(id) || !roleKey) {
      setError('Unknown role.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setDetail(await subscriptionsService.getSchoolRole(id, roleKey));
    } catch (err) {
      setError(errorMessage(err, 'Could not load this role.'));
    } finally {
      setLoading(false);
    }
  }, [id, roleKey]);

  useEffect(() => {
    void load();
  }, [load]);

  const createPlan = async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await subscriptionsService.createPlan(id, {
        role: roleKey as 'PRINCIPAL' | 'TEACHER' | 'STUDENT',
        name: createDraft.name.trim(),
        description: createDraft.description.trim() || undefined,
        price: Number(createDraft.price),
        currency: createDraft.currency.trim().toUpperCase() || 'INR',
        billing_interval: createDraft.billing_interval,
        duration_value: Number(createDraft.duration_value),
        duration_unit: createDraft.duration_unit,
      });
      setCreating(false);
      setCreateDraft(EMPTY_DRAFT);
      setNotice('Plan created and audited.');
      await load();
    } catch (err) {
      setError(errorMessage(err, 'Could not create the plan.'));
    } finally {
      setBusy(false);
    }
  };

  const saveEdit = async () => {
    if (editingId === null) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await subscriptionsService.updatePlan(editingId, {
        name: editDraft.name.trim(),
        description: editDraft.description.trim() || undefined,
        price: Number(editDraft.price),
        currency: editDraft.currency.trim().toUpperCase() || 'INR',
        billing_interval: editDraft.billing_interval,
        duration_value: Number(editDraft.duration_value),
        duration_unit: editDraft.duration_unit,
      });
      setEditingId(null);
      setNotice('Plan updated and audited.');
      await load();
    } catch (err) {
      setError(errorMessage(err, 'Could not update the plan.'));
    } finally {
      setBusy(false);
    }
  };

  const toggleActive = async (plan: SubscriptionPlan) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (plan.is_active) {
        await subscriptionsService.deactivatePlan(plan.id);
        setNotice(`"${plan.name}" deactivated - it can no longer be bought or assigned.`);
      } else {
        await subscriptionsService.updatePlan(plan.id, { is_active: true });
        setNotice(`"${plan.name}" reactivated.`);
      }
      await load();
    } catch (err) {
      setError(errorMessage(err, 'Could not change the plan state.'));
    } finally {
      setBusy(false);
      setDeactivating(null);
    }
  };

  const renderDraftFields = (
    draft: PlanDraft,
    onChange: (next: PlanDraft) => void
  ) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <label className="block sm:col-span-2">
        <span className="text-[11px] font-semibold text-slate-600">Plan name</span>
        <input
          type="text"
          maxLength={100}
          value={draft.name}
          onChange={(event) => onChange({ ...draft, name: event.target.value })}
          placeholder="e.g. Standard term plan"
          className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </label>

      <label className="block">
        <span className="text-[11px] font-semibold text-slate-600">Price</span>
        <input
          type="number"
          min={0}
          step="0.01"
          value={draft.price}
          onChange={(event) => onChange({ ...draft, price: event.target.value })}
          placeholder="0.00"
          className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </label>

      <label className="block">
        <span className="text-[11px] font-semibold text-slate-600">Currency (ISO)</span>
        <input
          type="text"
          maxLength={3}
          value={draft.currency}
          onChange={(event) => onChange({ ...draft, currency: event.target.value.toUpperCase() })}
          className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </label>

      <label className="block">
        <span className="text-[11px] font-semibold text-slate-600">Duration</span>
        <div className="mt-1 flex items-center gap-2">
          <input
            type="number"
            min={1}
            value={draft.duration_value}
            onChange={(event) => onChange({ ...draft, duration_value: event.target.value })}
            className="w-24 h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <select
            value={draft.duration_unit}
            onChange={(event) =>
              onChange({ ...draft, duration_unit: event.target.value as DurationUnit })
            }
            className="flex-1 h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {DURATION_UNITS.map((unit) => (
              <option key={unit} value={unit}>
                {unit === 'DAY' ? 'Days' : unit === 'MONTH' ? 'Months' : 'Years'}
              </option>
            ))}
          </select>
        </div>
      </label>

      <label className="block">
        <span className="text-[11px] font-semibold text-slate-600">Billing interval</span>
        <select
          value={draft.billing_interval}
          onChange={(event) =>
            onChange({ ...draft, billing_interval: event.target.value as BillingInterval })
          }
          className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {BILLING_INTERVALS.map((interval) => (
            <option key={interval} value={interval}>
              {interval.replace('_', ' ')}
            </option>
          ))}
        </select>
      </label>

      <label className="block sm:col-span-2">
        <span className="text-[11px] font-semibold text-slate-600">Description</span>
        <textarea
          rows={2}
          maxLength={500}
          value={draft.description}
          onChange={(event) => onChange({ ...draft, description: event.target.value })}
          placeholder="Optional, shown to the learner at checkout"
          className="mt-1 w-full px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </label>
    </div>
  );

  if (loading && !detail) return <LoadingSkeleton type="list" count={3} />;

  const plans = detail?.plans ?? [];

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
            <h1 className="text-xl font-bold text-slate-900">
              {ROLE_TITLES[roleKey] || roleKey} plans
            </h1>
            {detail && <AccessBadge status={detail.subscriptions_enabled ? 'ACTIVE' : 'DISABLED'} />}
          </div>
          <p className="text-xs text-slate-500">
            {detail?.subscriptions_enabled
              ? detail.free_until
                ? `Subscriptions on · school free until ${formatDate(detail.free_until)}`
                : 'Subscriptions on · no school-wide free window'
              : 'Subscriptions are switched off for this school'}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setCreating((value) => !value)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white font-bold text-xs transition-all flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>New plan</span>
        </button>
      </div>

      {error && <ErrorState title="Something went wrong" message={error} onRetry={load} />}
      {notice && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-3.5 py-2.5 text-xs text-emerald-800">
          {notice}
        </div>
      )}

      {creating && (
        <section className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-900">
              New {ROLE_TITLES[roleKey] || roleKey} plan
            </h2>
          </div>
          {renderDraftFields(createDraft, setCreateDraft)}
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={busy || !createDraft.name.trim() || !createDraft.price}
              onClick={() => void createPlan()}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs transition-all"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              <span>Create plan</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setCreating(false);
                setCreateDraft(EMPTY_DRAFT);
              }}
              className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-all"
            >
              Cancel
            </button>
          </div>
        </section>
      )}

      {plans.length === 0 ? (
        <EmptyState
          title="No plans for this role"
          description="Create the first plan to offer this role a price. A plan is an offer only - access still requires a grant or a payment."
          icon={<DollarSign className="w-10 h-10 text-slate-300" />}
          action={{ label: 'Create first plan', onClick: () => setCreating(true) }}
        />
      ) : (
        <div className="space-y-3">
          {plans.map((plan) => (
            <section key={plan.id} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-bold text-slate-900">{plan.name}</h3>
                    <AccessBadge status={plan.is_active ? 'ACTIVE' : 'NONE'}
                      label={plan.is_active ? 'Active' : 'Inactive'}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {plan.price} {plan.currency} · every {plan.duration_value}{' '}
                    {plan.duration_unit.toLowerCase()} · {plan.billing_interval}
                  </p>
                  {plan.description && (
                    <p className="text-xs text-slate-500 mt-1">{plan.description}</p>
                  )}
                </div>

                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingId(editingId === plan.id ? null : plan.id);
                      setEditDraft(draftFrom(plan));
                    }}
                    className="p-2 rounded-lg hover:bg-slate-100 text-slate-500"
                    title="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      plan.is_active ? setDeactivating(plan) : void toggleActive(plan)
                    }
                    className="p-2 rounded-lg hover:bg-slate-100 text-slate-500"
                    title={plan.is_active ? 'Deactivate' : 'Reactivate'}
                  >
                    <Power className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {editingId === plan.id && (
                <div className="mt-3 pt-3 border-t border-slate-100 space-y-3">
                  {renderDraftFields(editDraft, setEditDraft)}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={busy || !editDraft.name.trim() || !editDraft.price}
                      onClick={() => void saveEdit()}
                      className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs transition-all"
                    >
                      {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                      <span>Save changes</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingId(null)}
                      className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </section>
          ))}
        </div>
      )}

      <ConfirmDialog
        isOpen={!!deactivating}
        title="Deactivate this plan?"
        message={`"${deactivating?.name || ''}" will stop being purchasable and assignable immediately. The plan row and every payment that references it are kept - nothing is deleted.`}
        confirmLabel="Deactivate"
        isDanger
        onConfirm={() => deactivating && void toggleActive(deactivating)}
        onCancel={() => setDeactivating(null)}
        isLoading={busy}
      />
    </div>
  );
};

export default SuperAdminSubscriptionRole;
