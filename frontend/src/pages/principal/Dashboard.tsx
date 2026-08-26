// src/pages/principal/Dashboard.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardService } from '../../services/dashboard';
import { PrincipalDashboard } from '../../types/dashboard';
import { StatCard, LoadingSkeleton, ErrorState, MobileListItem } from '../../components/shared';
import { Users, BookOpen, Bell, Calendar, Award, CheckCircle, ArrowRight, School } from 'lucide-react';

export const PrincipalDashboardPage: React.FC = () => {
  const [data, setData] = useState<PrincipalDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const navigate = useNavigate();

  const fetchDashboard = () => {
    setLoading(true);
    setError(false);
    dashboardService
      .getPrincipalDashboard()
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
  if (error || !data) return <ErrorState title="Dashboard Error" message="Unable to load school leadership dashboard." onRetry={fetchDashboard} />;

  return (
    <div className="space-y-5">
      {/* Welcome Banner */}
      <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-emerald-900 via-teal-800 to-emerald-900 text-white shadow-md relative overflow-hidden">
        <div className="absolute right-0 top-0 translate-x-4 -translate-y-4 w-40 h-40 rounded-full bg-white/10 blur-2xl pointer-events-none" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/15 backdrop-blur text-xs font-medium text-emerald-100 mb-2">
            <School className="w-3.5 h-3.5" />
            <span>School Leadership</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black tracking-tight text-white">Principal Overview</h1>
          <p className="text-xs sm:text-sm text-emerald-100/90 mt-1 max-w-md">Academic metrics, staff management, and school administration portal.</p>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StatCard
          label="Faculty"
          value={data.total_teachers}
          icon={<Users className="w-5 h-5 text-emerald-600" />}
          iconBgClass="bg-emerald-50 text-emerald-600"
          onClick={() => navigate('/principal/teachers')}
        />
        <StatCard
          label="Enrollment"
          value={data.total_students}
          icon={<Users className="w-5 h-5 text-teal-600" />}
          iconBgClass="bg-teal-50 text-teal-600"
          onClick={() => navigate('/principal/enrollments')}
        />
        <StatCard
          label="Exams"
          value={data.upcoming_exams?.length || 0}
          icon={<BookOpen className="w-5 h-5 text-cyan-600" />}
          iconBgClass="bg-cyan-50 text-cyan-600"
          onClick={() => navigate('/principal/exams')}
        />
        <StatCard
          label="Notices"
          value={data.announcements?.length || 0}
          icon={<Bell className="w-5 h-5 text-amber-600" />}
          iconBgClass="bg-amber-50 text-amber-600"
          onClick={() => navigate('/principal/announcements')}
        />
      </div>

      {/* Quick Action Shortcuts */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <button
          onClick={() => navigate('/principal/attendance')}
          className="p-3 bg-white rounded-xl border border-slate-200/80 shadow-2xs hover:border-emerald-300 text-left transition-all active:scale-98"
        >
          <CheckCircle className="w-5 h-5 text-emerald-600 mb-1.5" />
          <span className="text-xs font-bold text-slate-900 block">Attendance</span>
          <span className="text-[11px] text-slate-400">Track daily status</span>
        </button>
        <button
          onClick={() => navigate('/principal/report-cards')}
          className="p-3 bg-white rounded-xl border border-slate-200/80 shadow-2xs hover:border-emerald-300 text-left transition-all active:scale-98"
        >
          <Award className="w-5 h-5 text-teal-600 mb-1.5" />
          <span className="text-xs font-bold text-slate-900 block">Report Cards</span>
          <span className="text-[11px] text-slate-400">View performance</span>
        </button>
        <button
          onClick={() => navigate('/principal/timetable')}
          className="p-3 bg-white rounded-xl border border-slate-200/80 shadow-2xs hover:border-emerald-300 text-left transition-all active:scale-98"
        >
          <Calendar className="w-5 h-5 text-cyan-600 mb-1.5" />
          <span className="text-xs font-bold text-slate-900 block">Timetable</span>
          <span className="text-[11px] text-slate-400">School schedules</span>
        </button>
        <button
          onClick={() => navigate('/principal/grades')}
          className="p-3 bg-white rounded-xl border border-slate-200/80 shadow-2xs hover:border-emerald-300 text-left transition-all active:scale-98"
        >
          <School className="w-5 h-5 text-indigo-600 mb-1.5" />
          <span className="text-xs font-bold text-slate-900 block">Grades & Classes</span>
          <span className="text-[11px] text-slate-400">Class management</span>
        </button>
      </div>

      {/* Recent Announcements Feed */}
      {data.announcements && data.announcements.length > 0 && (
        <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Bell className="w-4 h-4 text-emerald-600" />
              <span>Recent Announcements</span>
            </h3>
            <button
              onClick={() => navigate('/principal/announcements')}
              className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2">
            {data.announcements.slice(0, 3).map((ann: any, idx: number) => (
              <MobileListItem
                key={ann.id || idx}
                title={ann.title}
                subtitle={ann.content || ann.message}
                icon={<Bell className="w-4 h-4 text-emerald-600" />}
                avatarBg="bg-emerald-50 text-emerald-600"
                metaText={ann.created_at || 'Notice'}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PrincipalDashboardPage;
