// src/pages/student/Dashboard.tsx
import React, { useEffect, useState } from 'react';
import { dashboardService } from '../../services/dashboard';
import { StudentDashboard } from '../../types/dashboard';
import { StatCard } from '../../components/dashboard';
import { Calendar, BookOpen, Award, Bell } from 'lucide-react';

export const StudentDashboardPage: React.FC = () => {
  const [data, setData] = useState<StudentDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardService
      .getStudentDashboard()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-12 text-gray-500">Loading dashboard...</div>;
  if (!data) return <div className="text-center py-12 text-red-500">Failed to load dashboard.</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Student Dashboard</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Attendance Rate" value={`${data.attendance_percentage}%`} icon={<Award className="w-5 h-5" />} />
        <StatCard title="Pending Homework" value={data.pending_homework.length} icon={<BookOpen className="w-5 h-5" />} />
        <StatCard title="Upcoming Exams" value={data.upcoming_exams.length} icon={<Calendar className="w-5 h-5" />} />
        <StatCard title="Announcements" value={data.announcements.length} icon={<Bell className="w-5 h-5" />} />
      </div>
    </div>
  );
};

export default StudentDashboardPage;
/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
