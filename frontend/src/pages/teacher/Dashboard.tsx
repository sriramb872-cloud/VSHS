// src/pages/teacher/Dashboard.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardService } from '../../services/dashboard';
import { TeacherDashboard } from '../../types/dashboard';
import { Calendar, BookOpen, CheckCircle, Bell, Clock, ChevronRight } from 'lucide-react';
import { LoadingSkeleton } from '../../components/shared';

export const TeacherDashboardPage: React.FC = () => {
  const [data, setData] = useState<TeacherDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    dashboardService
      .getTeacherDashboard()
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-24 bg-gradient-to-r from-blue-500 to-sky-600 rounded-2xl animate-pulse" />
        <LoadingSkeleton type="metric" count={4} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-4">
        <div className="bg-white rounded-2xl border border-rose-200 p-6 text-center">
          <p className="text-sm font-semibold text-rose-600">Failed to load dashboard</p>
          <p className="text-xs text-slate-400 mt-1">Check your connection and try again.</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-3 h-9 px-4 rounded-xl bg-blue-600 text-white text-xs font-bold"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const metrics = [
    {
      icon: <Calendar className="w-5 h-5" />,
      label: "Today's Classes",
      value: data.todays_timetable.length,
      bg: 'bg-blue-50',
      color: 'text-blue-600',
      onClick: () => navigate('/teacher/timetable'),
    },
    {
      icon: <CheckCircle className="w-5 h-5" />,
      label: 'Attendance',
      value: data.attendance_pending ? 'Pending' : 'Done',
      bg: data.attendance_pending ? 'bg-amber-50' : 'bg-emerald-50',
      color: data.attendance_pending ? 'text-amber-600' : 'text-emerald-600',
      onClick: () => navigate('/teacher/attendance'),
    },
    {
      icon: <BookOpen className="w-5 h-5" />,
      label: 'Homework',
      value: data.homework_summary.length,
      bg: 'bg-sky-50',
      color: 'text-sky-600',
      onClick: () => navigate('/teacher/homework'),
    },
    {
      icon: <Bell className="w-5 h-5" />,
      label: 'Announcements',
      value: data.announcements.length,
      bg: 'bg-blue-50',
      color: 'text-blue-600',
      onClick: undefined,
    },
  ];

  return (
    <div className="space-y-4">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-600 to-sky-500 rounded-2xl p-5 text-white shadow-md">
        <div className="absolute top-0 right-0 w-24 h-24 bg-white/10 rounded-full -translate-y-8 translate-x-8" />
        <div className="absolute bottom-0 left-0 w-16 h-16 bg-white/10 rounded-full translate-y-6 -translate-x-6" />
        <p className="text-xs font-semibold text-blue-100 mb-0.5">Good Morning 👋</p>
        <h1 className="text-lg font-bold">Teacher Dashboard</h1>
        <p className="text-xs text-blue-100 mt-1">
          {data.todays_timetable.length} classes scheduled today
        </p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 gap-3">
        {metrics.map((m, i) => (
          <div
            key={i}
            onClick={m.onClick}
            className={`bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs transition-all ${
              m.onClick ? 'cursor-pointer hover:shadow-md hover:border-slate-300 active:scale-[0.98]' : ''
            }`}
          >
            <div className="flex items-center justify-between">
              <div className={`w-9 h-9 rounded-xl ${m.bg} ${m.color} flex items-center justify-center mb-2`}>
                {m.icon}
              </div>
              {m.onClick && <ChevronRight className="w-4 h-4 text-slate-300" />}
            </div>
            <p className="text-xs text-slate-500 font-medium">{m.label}</p>
            <p className="text-xl font-bold text-slate-900 mt-0.5">{m.value}</p>
          </div>
        ))}
      </div>

      {/* Today's Schedule */}
      {data.todays_timetable.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="flex items-center justify-between px-4 pt-4 pb-2">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Today's Schedule</h3>
          </div>
          <div className="divide-y divide-slate-100">
            {data.todays_timetable.slice(0, 5).map((slot: any, i: number) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3">
                <div className="w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                  <Clock className="w-4 h-4 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{slot.subject_name || 'Class'}</p>
                  <p className="text-xs text-slate-500">{slot.start_time} – {slot.end_time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Announcements */}
      {data.announcements.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="flex items-center justify-between px-4 pt-4 pb-2">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Announcements</h3>
          </div>
          <div className="divide-y divide-slate-100">
            {data.announcements.slice(0, 3).map((ann: any, i: number) => (
              <div key={i} className="flex items-start gap-3 px-4 py-3">
                <div className="w-9 h-9 rounded-xl bg-sky-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bell className="w-4 h-4 text-sky-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{ann.title}</p>
                  <p className="text-xs text-slate-500 line-clamp-1">{ann.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherDashboardPage;
