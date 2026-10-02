// src/pages/superadmin/SubscriptionSchool.tsx
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  CalendarClock,
  Layers,
  Loader2,
  RefreshCw,
  Save,
  Search,
  Users,
} from 'lucide-react';
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from '../../components/shared';
import { AccessBadge } from '../../components/subscriptions/AccessBadge';
import {
  BulkOperations,
  BulkResultReport,
} from '../../components/subscriptions/BulkOperations';
import {
  formatDateTime,
  fromDateTimeLocal,
  sameMinute,
  toDateTimeLocal,
} from '../../components/subscriptions/format';
import { subscriptionsService } from '../../services/subscriptions';
import { errorMessage } from '../../helpers/errorMessage';
import type {
  BulkOperationResponse,
  SchoolRolesResponse,
  SchoolSettings,
  SchoolSubscriptionSummary,
  SchoolUserSubscriptionItem,
  SubscriptionPlan,
} from '../../types/subscription';

const PAGE_SIZE = 25;

const ROLE_LABELS: Record<string, string> = {
  PRINCIPAL: 'Principals',
  TEACHER: 'Teachers',
  STUDENT: 'Students',
};

/**
 * Super Admin > one school's subscription control panel.
 *
 * Four concerns, all backed by real endpoints:
 *   1. settings (enable/disable + school-wide free window) - PATCH semantics
 *      are "omit = unchanged, null = remove", so the form only sends what the
 *      admin actually edited (an empty PATCH is a structured NO_CHANGES);
 *   2. role plans (per-role pricing/duration, never a hardcoded 30 days);
 *   3. the user roster with role/status/search filters;
 *   4. bulk operations with the server's per-user failure summary.
 */
export const SuperAdminSubscriptionSchool: React.FC = () => {
  const navigate = useNavigate();
  const { schoolId } = useParams<{ schoolId: string }>();
  const id = Number(schoolId);

  const [summary, setSummary] = useState<SchoolSubscriptionSummary | null>(null);
  const [settings, setSettings] = useState<SchoolSettings | null>(null);
  const [roles, setRoles] = useState<SchoolRolesResponse | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [users, setUsers] = useState<SchoolUserSubscriptionItem[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);

  const [enabled, setEnabled] = useState(false);
  const [freeUntil, setFreeUntil] = useState('');
  const [reason, setReason] = useState('');

  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [skip, setSkip] = useState(0);
  const [selected, setSelected] = useState<number[]>([]);

  const [loading, setLoading] = useState(true);
  const [savingSettings, setSavingSettings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirmEnable, setConfirmEnable] = useState(false);
  const [bulkResult, setBulkResult] = useState<BulkOperationResponse | null>(null);

  const schoolPlans = useMemo(() => plans.filter((plan) => plan.school_id === id), [plans, id]);

  const loadAll = useCallback(async () => {
    if (!Number.isFinite(id)) {
      setError('Unknown school.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [summaryData, settingsData, rolesData, plansData] = await Promise.all([
        subscriptionsService.getSchool(id),
        subscriptionsService.getSchoolSettings(id),
        subscriptionsService.getSchoolRoles(id),
        subscriptionsService.listPlans(),
      ]);
      setSummary(summaryData);
      setSettings(settingsData);
      setRoles(rolesData);
      setPlans(plansData.items);
      setEnabled(settingsData.subscriptions_enabled);
      setFreeUntil(toDateTimeLocal(settingsData.free_until));
    } catch (err) {
      setError(errorMessage(err, 'Could not load this school.'));
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadUsers = useCallback(async () => {
    if (!Number.isFinite(id)) return;
    try {
      const data = await subscriptionsService.listSchoolUsers(id, {
        role: roleFilter || undefined,
        status: statusFilter || undefined,
        search: search.trim() || undefined,
        skip,
        limit: PAGE_SIZE,
      });
      setUsers(data.items);
      setTotalUsers(data.total);
    } catch (err) {
      setError(errorMessage(err, 'Could not load users.'));
    }
  }, [id, roleFilter, statusFilter, search, skip]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  // Reset paging/selection whenever the filter set changes.
  useEffect(() => {
    setSkip(0);
    setSelected([]);
  }, [roleFilter, statusFilter, search]);

  const settingsDirty = settings
    ? enabled !== settings.subscriptions_enabled || !sameMinute(freeUntil, settings.free_until)
    : false;

  const saveSettings = async () => {
    if (!settings) return;
    const payload: Parameters<typeof subscriptionsService.updateSchoolSettings>[1] = {};
    if (enabled !== settings.subscriptions_enabled) payload.subscriptions_enabled = enabled;
    if (!sameMinute(freeUntil, settings.free_until)) {
      payload.free_until = fromDateTimeLocal(freeUntil);
    }
    if (reason.trim()) payload.reason = reason.trim();

    if (Object.keys(payload).length === 0) {
      setNotice('Nothing changed - the values you sent match the current settings.');
      return;
    }

    setSavingSettings(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await subscriptionsService.updateSchoolSettings(id, payload);
      setSettings(updated);
      setEnabled(updated.subscriptions_enabled);
      setFreeUntil(toDateTimeLocal(updated.free_until));
      setReason('');
      setNotice('Settings saved and audited.');
      window.dispatchEvent(new Event('scholaris:subscription-changed'));
      await loadAll();
    } catch (err) {
      setError(errorMessage(err, 'Could not save the settings.'));
    } finally {
      setSavingSettings(false);
    }
  };

  const openRole = (role: string) => {
    // The role page owns its own fetch; navigating is all that is needed here.
    navigate(`/superadmin/subscriptions/${id}/roles/${role}`);
  };

  const toggleSelected = (userId: number) => {
    setSelected((current) =>
      current.includes(userId) ? current.filter((item) => item !== userId) : [...current, userId]
    );
  };

  const allOnPageSelected = users.length > 0 && users.every((user) => selected.includes(user.user_id));

  if (loading && !summary) return <LoadingSkeleton type="list" count={4} />;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <button
            type="button"
            onClick={() => navigate('/superadmin/subscriptions')}
            className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-700 mb-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>All schools</span>
          </button>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-slate-900 truncate">
              {summary?.name || 'School'}
            </h1>
            {summary && <AccessBadge status={summary.status} />}
          </div>
          <p className="text-xs text-slate-500">
            {summary?.code ? `${summary.code} · ` : ''}
            {summary?.students ?? 0} students · {summary?.teachers ?? 0} teachers ·{' '}
            {summary?.others ?? 0} others
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            void loadAll();
            void loadUsers();
          }}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs transition-all flex-shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorState title="Something went wrong" message={error} onRetry={() => { void loadAll(); void loadUsers(); }} />}
      {notice && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-3.5 py-2.5 text-xs text-emerald-800">
          {notice}
        </div>
      )}

      {/* ── Settings ─────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <CalendarClock className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">School settings</h2>
        </div>

        <div className="space-y-3">
          <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50/60 p-3 cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(event) => setEnabled(event.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-xs text-slate-700">
              <span className="font-semibold block">Require subscriptions</span>
              <span className="text-slate-500">
                When on, principals, teachers and students without an active entitlement, free
                window or grant are denied the gated modules. When off, everything stays open
                (the rollout default).
              </span>
            </span>
          </label>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="text-[11px] font-semibold text-slate-600">
                School-wide free access until (UTC)
              </span>
              <input
                type="datetime-local"
                value={freeUntil}
                onChange={(event) => setFreeUntil(event.target.value)}
                className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <span className="block mt-1 text-[11px] text-slate-400">
                Leave empty for no free window. {settings?.free_until ? `Currently: ${formatDateTime(settings.free_until)}.` : 'Currently: none.'}
              </span>
            </label>

            <label className="block">
              <span className="text-[11px] font-semibold text-slate-600">Reason (audited)</span>
              <input
                type="text"
                maxLength={500}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="e.g. enabling billing for the new term"
                className="mt-1 w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </label>
          </div>

          <button
            type="button"
            disabled={!settingsDirty || savingSettings}
            onClick={() => (enabled && !settings?.subscriptions_enabled ? setConfirmEnable(true) : saveSettings())}
            className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 disabled:opacity-50 text-white font-bold text-xs transition-all"
          >
            {savingSettings ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            <span>Save settings</span>
          </button>
        </div>
      </section>

      {/* ── Roles ────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-1">
          <Layers className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Plans by role</h2>
        </div>
        <p className="text-[11px] text-slate-500 mb-3">
          Each school prices its own roles. A plan is an offer - it never grants access by
          itself.
        </p>

        {!roles || roles.roles.length === 0 ? (
          <EmptyState
            title="No roles yet"
            description="This school has no users in a billable role."
            icon={<Layers className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {roles.roles.map((role) => (
              <button
                key={role.role}
                type="button"
                onClick={() => openRole(role.role)}
                className="text-left rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 p-3 transition-all"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold text-slate-900">
                    {ROLE_LABELS[role.role] || role.role}
                  </span>
                  <span className="text-[11px] text-slate-400">{role.active_plans} plans</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  {role.total_users} users · {role.active} active · {role.free} free ·{' '}
                  {role.expired} expired · {role.suspended} suspended · {role.none} none
                </p>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* ── Users ────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <Users className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-900">Users</h2>
          <span className="ml-auto text-[11px] text-slate-400">{totalUsers} total</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search name or mobile..."
              className="w-full h-10 pl-9 pr-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <select
            value={roleFilter}
            onChange={(event) => setRoleFilter(event.target.value)}
            className="h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All roles</option>
            <option value="PRINCIPAL">Principals</option>
            <option value="TEACHER">Teachers</option>
            <option value="STUDENT">Students</option>
          </select>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="h-10 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="FREE">Free</option>
            <option value="EXPIRED">Expired</option>
            <option value="SUSPENDED">Suspended</option>
            <option value="NONE">None</option>
          </select>
        </div>

        <div className="flex items-center justify-between mb-2">
          <label className="inline-flex items-center gap-2 text-[11px] text-slate-500 cursor-pointer">
            <input
              type="checkbox"
              checked={allOnPageSelected}
              onChange={() =>
                setSelected((current) =>
                  allOnPageSelected
                    ? current.filter(
                        (userId) => !users.some((user) => user.user_id === userId)
                      )
                    : Array.from(new Set([...current, ...users.map((user) => user.user_id)]))
                )
              }
              className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span>Select page</span>
          </label>
          <span className="text-[11px] text-slate-400">
            {selected.length} selected
          </span>
        </div>

        {users.length === 0 ? (
          <EmptyState
            title="No users match"
            description="Adjust the filters above."
            icon={<Users className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {users.map((user) => (
              <li key={user.user_id} className="py-2.5 flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={selected.includes(user.user_id)}
                  onChange={() => toggleSelected(user.user_id)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 flex-shrink-0"
                />
                <button
                  type="button"
                  onClick={() =>
                    navigate(`/superadmin/subscriptions/${id}/users/${user.user_id}`)
                  }
                  className="flex-1 min-w-0 text-left"
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-slate-900 truncate">
                      {user.display_name}
                    </span>
                    <AccessBadge status={user.subscription_status} />
                  </div>
                  <p className="text-[11px] text-slate-500 truncate">
                    {user.role} · {user.mobile}
                    {user.plan_name ? ` · ${user.plan_name}` : ''}
                    {/* While a FREE override is in force the API reports
                        `expires_at` as the override window, so labelling it
                        "until" next to the plan would read as if the paid plan
                        ended there. Mirrors the server's own condition. */}
                    {user.expires_at &&
                    !(user.subscription_status === 'FREE' && user.override_free_until)
                      ? ` · until ${formatDateTime(user.expires_at)}`
                      : ''}
                    {user.override_free_until
                      ? ` · free until ${formatDateTime(user.override_free_until)}`
                      : ''}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="flex items-center justify-between mt-3">
          <button
            type="button"
            disabled={skip === 0}
            onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
            className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 disabled:opacity-40 text-slate-700 font-semibold text-xs transition-all"
          >
            Previous
          </button>
          <span className="text-[11px] text-slate-400">
            {totalUsers === 0 ? 0 : skip + 1}–{Math.min(skip + PAGE_SIZE, totalUsers)} of{' '}
            {totalUsers}
          </span>
          <button
            type="button"
            disabled={skip + PAGE_SIZE >= totalUsers}
            onClick={() => setSkip(skip + PAGE_SIZE)}
            className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 disabled:opacity-40 text-slate-700 font-semibold text-xs transition-all"
          >
            Next
          </button>
        </div>
      </section>

      {bulkResult && (
        <BulkResultReport result={bulkResult} onClose={() => setBulkResult(null)} />
      )}

      <BulkOperations
        schoolId={id}
        userIds={selected}
        plans={schoolPlans}
        onDone={(result) => {
          setBulkResult(result);
          void loadUsers();
          void loadAll();
          window.dispatchEvent(new Event('scholaris:subscription-changed'));
        }}
        onClearSelection={() => setSelected([])}
      />

      <ConfirmDialog
        isOpen={confirmEnable}
        title="Require subscriptions for this school?"
        message="Principals, teachers and students without an active subscription, free window or grant will be locked out of the gated modules the next time they load a page."
        confirmLabel="Enable"
        onConfirm={() => {
          setConfirmEnable(false);
          void saveSettings();
        }}
        onCancel={() => setConfirmEnable(false)}
        isLoading={savingSettings}
      />
    </div>
  );
};

export default SuperAdminSubscriptionSchool;
