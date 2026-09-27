// src/pages/superadmin/Analytics.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { Building, Users, Activity, TrendingUp, GraduationCap, UserCog } from 'lucide-react';
import { StatCard, LoadingSkeleton, ErrorState, EmptyState } from '../../components/shared';
import { dashboardService } from '../../services/dashboard';
import { errorMessage } from '../../helpers/errorMessage';
import { SuperAdminDashboard } from '../../types/dashboard';

export const SuperAdminAnalytics: React.FC = () => {
  const [analytics, setAnalytics] = useState<SuperAdminDashboard | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadFailed, setLoadFailed] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // This page previously set `loading` to false in useEffect without ever
  // calling an API, so it always rendered three hard-coded zeros. It now reads
  // the same aggregate the Super Admin dashboard uses
  // (GET /dashboard/super-admin) instead of duplicating a second endpoint.
  const load = useCallback(async () => {
    setLoading(true);
    setLoadFailed(false);
    setError(null);
    try {
      setAnalytics(await dashboardService.getSuperAdminDashboard());
    } catch (err) {
      setLoadFailed(true);
      setError(errorMessage(err, 'Unable to load platform analytics right now.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const totalUsers =
    (analytics?.total_principals ?? 0) +
    (analytics?.total_teachers ?? 0) +
    (analytics?.total_students ?? 0);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Platform Analytics</h1>
        <p className="text-xs text-slate-500">System growth and engagement metrics</p>
      </div>

      {loadFailed ? (
        <ErrorState title="Load Error" message={error || 'Failed to load analytics'} onRetry={load} />
      ) : loading ? (
        <LoadingSkeleton type="metrics" count={3} />
      ) : !analytics ? (
        <EmptyState
          title="No Analytics Available"
          description="Platform metrics could not be loaded."
          icon={<TrendingUp className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <StatCard
              label="Schools"
              value={analytics.total_schools}
              icon={<Building className="w-5 h-5 text-indigo-600" />}
              iconBgClass="bg-indigo-50 text-indigo-600"
            />
            <StatCard
              label="Users"
              value={totalUsers}
              subtitle="Principals, teachers and students"
              icon={<Users className="w-5 h-5 text-purple-600" />}
              iconBgClass="bg-purple-50 text-purple-600"
            />
            <StatCard
              label="Active Schools"
              value={analytics.active_schools}
              icon={<Activity className="w-5 h-5 text-emerald-600" />}
              iconBgClass="bg-emerald-50 text-emerald-600"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <StatCard
              label="Principals"
              value={analytics.total_principals}
              icon={<UserCog className="w-5 h-5 text-amber-600" />}
              iconBgClass="bg-amber-50 text-amber-600"
            />
            <StatCard
              label="Teachers"
              value={analytics.total_teachers}
              icon={<GraduationCap className="w-5 h-5 text-sky-600" />}
              iconBgClass="bg-sky-50 text-sky-600"
            />
            <StatCard
              label="Students"
              value={analytics.total_students}
              icon={<Users className="w-5 h-5 text-rose-600" />}
              iconBgClass="bg-rose-50 text-rose-600"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">System Health</p>
              <p className="text-sm font-semibold text-slate-900 mt-1">{analytics.system_health}</p>
            </div>
            <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Storage Usage</p>
              <p className="text-sm font-semibold text-slate-900 mt-1">{analytics.storage_usage}</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default SuperAdminAnalytics;
