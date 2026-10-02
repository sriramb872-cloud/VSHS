// src/pages/superadmin/Subscriptions.tsx
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Building,
  CheckCircle2,
  CreditCard,
  RefreshCw,
  Search,
  TrendingDown,
  TrendingUp,
  Users,
  XCircle,
} from 'lucide-react';
import {
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  MobileListItem,
  StatCard,
} from '../../components/shared';
import { AccessBadge } from '../../components/subscriptions/AccessBadge';
import { formatDate } from '../../components/subscriptions/format';
import { subscriptionsService } from '../../services/subscriptions';
import { errorMessage } from '../../helpers/errorMessage';
import type {
  SchoolSubscriptionSummary,
  SubscriptionMetrics,
} from '../../types/subscription';

/**
 * Super Admin > Subscriptions: platform-wide metrics plus a per-school rollup.
 *
 * Every number is an aggregate the API computed from real rows
 * (`GET /subscription/metrics` and `GET /subscription/schools`) - nothing on
 * this screen is estimated, interpolated or cached from a previous session.
 */
export const SuperAdminSubscriptions: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<SubscriptionMetrics | null>(null);
  const [schools, setSchools] = useState<SchoolSubscriptionSummary[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [metricsData, schoolsData] = await Promise.all([
        subscriptionsService.metrics(),
        subscriptionsService.listSchools({ limit: 100 }),
      ]);
      setMetrics(metricsData);
      setSchools(schoolsData.items);
    } catch (err) {
      setError(errorMessage(err, 'Failed to load subscriptions.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = schools.filter((school) => {
    const needle = search.trim().toLowerCase();
    if (!needle) return true;
    return (
      school.name.toLowerCase().includes(needle) ||
      (school.code || '').toLowerCase().includes(needle)
    );
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Subscriptions</h1>
          <p className="text-xs text-slate-500">School licensing, plans and billing status</p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 active:scale-95 text-slate-700 font-bold text-xs transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorState title="Load Error" message={error} onRetry={load} />}

      {metrics && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            icon={<Building className="w-5 h-5" />}
            label="Schools"
            value={metrics.total_schools}
            iconBgClass="bg-indigo-50 text-indigo-600"
          />
          <StatCard
            icon={<CreditCard className="w-5 h-5" />}
            label="Subscriptions on"
            value={metrics.subscriptions_enabled}
            subtitle={`of ${metrics.total_schools}`}
            iconBgClass="bg-emerald-50 text-emerald-600"
          />
          <StatCard
            icon={<Users className="w-5 h-5" />}
            label="Active users"
            value={metrics.active_user_subscriptions}
            subtitle="with a live subscription"
            iconBgClass="bg-cyan-50 text-cyan-600"
          />
          <StatCard
            icon={<TrendingDown className="w-5 h-5" />}
            label="Expired users"
            value={metrics.expired_user_subscriptions}
            iconBgClass="bg-amber-50 text-amber-600"
          />
          <StatCard
            icon={<CheckCircle2 className="w-5 h-5" />}
            label="Payments succeeded"
            value={metrics.successful_payments}
            iconBgClass="bg-emerald-50 text-emerald-600"
          />
          <StatCard
            icon={<XCircle className="w-5 h-5" />}
            label="Payments failed"
            value={metrics.failed_payments}
            subtitle="failed or cancelled"
            iconBgClass="bg-rose-50 text-rose-600"
          />
          <StatCard
            icon={<RefreshCw className="w-5 h-5" />}
            label="Payments pending"
            value={metrics.pending_payments}
            iconBgClass="bg-amber-50 text-amber-600"
          />
          <StatCard
            icon={<BarChart3 className="w-5 h-5" />}
            label="Schools free now"
            value={metrics.schools_currently_free}
            iconBgClass="bg-cyan-50 text-cyan-600"
          />
        </div>
      )}

      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by school name or code..."
          className="w-full h-11 pl-10 pr-4 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs sm:text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
        />
      </div>

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : error ? null : filtered.length === 0 ? (
        <EmptyState
          title="No Schools Found"
          description={
            search
              ? 'No school matches your search criteria.'
              : 'There are no schools onboarded yet.'
          }
          icon={<Building className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {filtered.map((school) => (
            <MobileListItem
              key={school.school_id}
              title={school.name}
              subtitle={
                <>
                  {school.code ? `Code: ${school.code}` : ''}
                  {school.code ? ' · ' : ''}
                  {school.active_subscriptions} active · {school.expired_subscriptions} expired
                  {school.free_until ? ` · free until ${formatDate(school.free_until)}` : ''}
                </>
              }
              icon={<Building className="w-5 h-5 text-indigo-600" />}
              avatarBg="bg-indigo-50 text-indigo-600"
              badge={<AccessBadge status={school.status} />}
              onClick={() => navigate(`/superadmin/subscriptions/${school.school_id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminSubscriptions;
