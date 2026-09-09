import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardService } from '../../services/dashboard';
import { StudentDashboard } from '../../types/dashboard';
import { StatCard, LoadingSkeleton, ErrorState } from '../../components/shared';
import { Calendar, BookOpen, Award, Bell } from 'lucide-react';

export const StudentDashboardPage: React.FC = () => {
  const [data, setData] = useState<StudentDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const navigate = useNavigate();

  const fetchDashboard = () => {
    setLoading(true);
    setError(false);
    dashboardService.getStudentDashboard()
      .then(setData)
      .catch((err) => { console.error(err); setError(true); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchDashboard(); }, []);

  if (loading) return <LoadingSkeleton type="metrics" count={4} />;
  if (error || !data) return <ErrorState title="Dashboard Error" message="Unable to load your dashboard." onRetry={fetchDashboard} />;

  return (
    <div className="space-y-5">
      <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-indigo-900 via-violet-800 to-indigo-900 text-white shadow-md relative overflow-hidden">
        <div className="absolute right-0 top-0 translate-x-4 -translate-y-4 w-40 h-40 rounded-full bg-white/10 blur-2xl pointer-events-none" />
        <div className="relative z-10">
          <h1 className="text-lg sm:text-xl font-bold">My Dashboard</h1>
          <p className="text-xs sm:text-sm text-indigo-100 mt-1">Here's where things stand today.</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Attendance Rate" value={`${data.attendance_percentage}%`} icon={<Award className="w-5 h-5" />} iconBgClass="bg-emerald-50 text-emerald-600" onClick={() => navigate('/student/attendance')} />
        <StatCard label="Pending Homework" value={data.pending_homework.length} icon={<BookOpen className="w-5 h-5" />} iconBgClass="bg-amber-50 text-amber-600" onClick={() => navigate('/student/homework')} />
        <StatCard label="Upcoming Exams" value={data.upcoming_exams.length} icon={<Calendar className="w-5 h-5" />} iconBgClass="bg-rose-50 text-rose-600" onClick={() => navigate('/student/exams')} />
        <StatCard label="Announcements" value={data.announcements.length} icon={<Bell className="w-5 h-5" />} iconBgClass="bg-blue-50 text-blue-600" onClick={() => navigate('/student/announcements')} />
      </div>
    </div>
  );
};

export default StudentDashboardPage;
