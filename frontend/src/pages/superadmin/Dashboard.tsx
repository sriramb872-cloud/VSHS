// src/pages/superadmin/Dashboard.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardService } from '../../services/dashboard';
import { SuperAdminDashboard } from '../../types/dashboard';
import { StatCard, LoadingSkeleton, ErrorState } from '../../components/shared';
import { Building, Users, Activity, HardDrive, Plus, Shield, Settings, FileText } from 'lucide-react';

export const SuperAdminDashboardPage: React.FC = () => {
  const [data, setData] = useState<SuperAdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const navigate = useNavigate();

  const fetchDashboard = () => {
    setLoading(true);
    setError(false);
    dashboardService
      .getSuperAdminDashboard()
      .then(setData)
      .catch((err) => {
        console.error(err);
        setError(true);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (loading) return <LoadingSkeleton type="metrics" count={4} />;
  if (error || !data) return <ErrorState title="Dashboard Unavailable" message="Failed to load system dashboard telemetry." onRetry={fetchDashboard} />;

  return (
    <div className="space-y-5">
      {/* Welcome Banner */}
      <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-indigo-900 via-indigo-800 to-purple-900 text-white shadow-md relative overflow-hidden">
        <div className="absolute right-0 top-0 translate-x-4 -translate-y-4 w-40 h-40 rounded-full bg-white/10 blur-2xl pointer-events-none" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/15 backdrop-blur text-xs font-medium text-indigo-200 mb-2">
            <Shield className="w-3.5 h-3.5" />
            <span>System Administration</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black tracking-tight text-white">System Telemetry Dashboard</h1>
          <p className="text-xs sm:text-sm text-indigo-200/90 mt-1 max-w-md">Overview of multi-tenant schools, system health metrics, and infrastructure usage.</p>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StatCard
          title="Total Schools"
          label="Schools"
          value={data.total_schools}
          icon={<Building className="w-5 h-5 text-indigo-600" />}
          iconBgClass="bg-indigo-50 text-indigo-600"
          onClick={() => navigate('/superadmin/schools')}
        />
        <StatCard
          title="Active Schools"
          label="Active"
          value={data.active_schools}
          icon={<Activity className="w-5 h-5 text-emerald-600" />}
          iconBgClass="bg-emerald-50 text-emerald-600"
          badgeText="Operational"
        />
        <StatCard
          title="Total Principals"
          label="Principals"
          value={data.total_principals}
          icon={<Users className="w-5 h-5 text-purple-600" />}
          iconBgClass="bg-purple-50 text-purple-600"
          onClick={() => navigate('/superadmin/principals')}
        />
        <StatCard
          title="Total Teachers"
          label="Teachers"
          value={data.total_teachers}
          icon={<Users className="w-5 h-5 text-blue-600" />}
          iconBgClass="bg-blue-50 text-blue-600"
        />
      </div>

      {/* Secondary Metrics & Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <StatCard
            title="System Health"
            label="Health Status"
            value={data.system_health || 'Healthy'}
            subtitle="All core services operational"
            icon={<Activity className="w-5 h-5 text-emerald-600" />}
            iconBgClass="bg-emerald-50 text-emerald-600"
          />
          <StatCard
            title="Storage Usage"
            label="Cloud Storage"
            value={data.storage_usage || 'Normal'}
            subtitle="Encrypted storage quota"
            icon={<HardDrive className="w-5 h-5 text-amber-600" />}
            iconBgClass="bg-amber-50 text-amber-600"
          />
        </div>

        {/* Quick Actions Card */}
        <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
              <Shield className="w-4 h-4 text-indigo-600" />
              <span>Admin Quick Actions</span>
            </h3>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/superadmin/schools/create')}
                className="w-full flex items-center gap-2.5 p-2.5 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold text-xs transition-all"
              >
                <Plus className="w-4 h-4" />
                <span>Onboard New School</span>
              </button>
              <button
                onClick={() => navigate('/superadmin/users')}
                className="w-full flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium text-xs transition-all"
              >
                <Users className="w-4 h-4 text-slate-500" />
                <span>Manage Users</span>
              </button>
              <button
                onClick={() => navigate('/superadmin/audit-logs')}
                className="w-full flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium text-xs transition-all"
              >
                <FileText className="w-4 h-4 text-slate-500" />
                <span>System Audit Logs</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SuperAdminDashboardPage;
