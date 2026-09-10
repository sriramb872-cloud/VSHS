// src/pages/principal/Analytics.tsx
import React, { useState, useEffect } from 'react';
import { TrendingUp, Users, UserCheck, ClipboardCheck, BarChart2 } from 'lucide-react';
import { LoadingSkeleton, StatCard } from '../../components/shared';
import { dashboardService } from '../../services/dashboard';

export const Analytics: React.FC = () => {
  const [analyticsData, setAnalyticsData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    dashboardService.getPrincipalDashboard()
      .then((dashboard) => {
        if (cancelled) return;
        const attendance = dashboard.todays_attendance || {};
        const present = Number(attendance.present ?? 0);
        const total = Number(attendance.total ?? attendance.expected ?? 0);
        setAnalyticsData({
          student_count: dashboard.total_students,
          teacher_count: dashboard.total_teachers,
          attendance_rate: total > 0 ? Math.round((present / total) * 1000) / 10 : 0,
          average_score: '—',
        });
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setError('Unable to load school analytics right now.');
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">School Analytics</h1>
        <p className="text-xs text-slate-500">Performance metrics and institutional insights</p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loading ? (
        <LoadingSkeleton type="metrics" count={4} />
      ) : !analyticsData ? (
        <div className="space-y-4">
          {/* Placeholder metrics with skeleton-style appearance */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { icon: <Users className="w-5 h-5" />, label: 'Total Students', value: '—', color: 'bg-emerald-50 text-emerald-600' },
              { icon: <UserCheck className="w-5 h-5" />, label: 'Total Teachers', value: '—', color: 'bg-teal-50 text-teal-600' },
              { icon: <ClipboardCheck className="w-5 h-5" />, label: 'Attendance Rate', value: '—', color: 'bg-emerald-50 text-emerald-600' },
              { icon: <TrendingUp className="w-5 h-5" />, label: 'Avg. Grade Score', value: '—', color: 'bg-teal-50 text-teal-600' },
            ].map((item, i) => (
              <div key={i} className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs">
                <div className={`w-9 h-9 rounded-xl ${item.color} flex items-center justify-center mb-2`}>
                  {item.icon}
                </div>
                <p className="text-xs text-slate-500 font-medium">{item.label}</p>
                <p className="text-2xl font-bold text-slate-400 mt-0.5">{item.value}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 text-center">
            <BarChart2 className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">Analytics data currently unavailable</p>
            <p className="text-xs text-slate-400 mt-1">Connect to backend API to load real-time school metrics.</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            label="Total Students"
            value={analyticsData.student_count ?? 0}
            icon={<Users className="w-5 h-5" />}
          />
          <StatCard
            label="Total Teachers"
            value={analyticsData.teacher_count ?? 0}
            icon={<UserCheck className="w-5 h-5" />}
          />
          <StatCard
            label="Attendance Rate"
            value={`${analyticsData.attendance_rate ?? 0}%`}
            icon={<ClipboardCheck className="w-5 h-5" />}
          />
          <StatCard
            label="Avg. Score"
            value={analyticsData.average_score ?? '—'}
            icon={<TrendingUp className="w-5 h-5" />}
          />
        </div>
      )}
    </div>
  );
};

export default Analytics;
