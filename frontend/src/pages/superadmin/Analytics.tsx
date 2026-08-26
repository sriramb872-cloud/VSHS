// src/pages/superadmin/Analytics.tsx
import React, { useState, useEffect } from 'react';
import { BarChart3, Building, Users, Activity } from 'lucide-react';
import { StatCard, LoadingSkeleton, EmptyState } from '../../components/shared';

export const SuperAdminAnalytics: React.FC = () => {
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch platform analytics using existing services
    setLoading(false);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Platform Analytics</h1>
        <p className="text-xs text-slate-500">System growth and engagement metrics</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      {loading ? (
        <LoadingSkeleton type="metrics" count={3} />
      ) : !analytics ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <StatCard
            title="Total Schools"
            label="Schools"
            value="0"
            icon={<Building className="w-5 h-5 text-indigo-600" />}
            iconBgClass="bg-indigo-50 text-indigo-600"
          />
          <StatCard
            title="Total Users"
            label="Users"
            value="0"
            icon={<Users className="w-5 h-5 text-purple-600" />}
            iconBgClass="bg-purple-50 text-purple-600"
          />
          <StatCard
            title="Active Schools"
            label="Active"
            value="0"
            icon={<Activity className="w-5 h-5 text-emerald-600" />}
            iconBgClass="bg-emerald-50 text-emerald-600"
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <StatCard
            title="Total Schools"
            label="Schools"
            value={analytics.total_schools ?? '-'}
            icon={<Building className="w-5 h-5 text-indigo-600" />}
            iconBgClass="bg-indigo-50 text-indigo-600"
          />
          <StatCard
            title="Total Users"
            label="Users"
            value={analytics.total_users ?? '-'}
            icon={<Users className="w-5 h-5 text-purple-600" />}
            iconBgClass="bg-purple-50 text-purple-600"
          />
          <StatCard
            title="Active Schools"
            label="Active"
            value={analytics.active_schools ?? '-'}
            icon={<Activity className="w-5 h-5 text-emerald-600" />}
            iconBgClass="bg-emerald-50 text-emerald-600"
          />
        </div>
      )}
    </div>
  );
};

export default SuperAdminAnalytics;