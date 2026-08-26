// src/pages/principal/AttendanceReports.tsx
import React, { useState, useEffect } from 'react';
import { BarChart2, Users, UserX } from 'lucide-react';
import { EmptyState, LoadingSkeleton } from '../../components/shared';
import { attendanceService } from '../../services/attendance';

interface DailySummary {
  period: string;
  present_count: number;
  absent_count: number;
  percentage: number;
}

export const AttendanceReports: React.FC = () => {
  const [reports, setReports] = useState<DailySummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    attendanceService
      .getAttendance()
      .then(records => {
        const byDate: Record<string, { present: number; absent: number; total: number }> = {};
        records.forEach(r => {
          if (!byDate[r.date]) byDate[r.date] = { present: 0, absent: 0, total: 0 };
          byDate[r.date].total += 1;
          if (r.status === 'PRESENT' || r.status === 'LATE') {
            byDate[r.date].present += 1;
          } else {
            byDate[r.date].absent += 1;
          }
        });
        const summaries: DailySummary[] = Object.entries(byDate)
          .sort(([a], [b]) => b.localeCompare(a))
          .slice(0, 10)
          .map(([date, stats]) => ({
            period: date,
            present_count: stats.present,
            absent_count: stats.absent,
            percentage: stats.total > 0 ? Math.round((stats.present / stats.total) * 100) : 0,
          }));
        setReports(summaries);
      })
      .catch(() => setError('Failed to load attendance reports'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Attendance Reports</h1>
        <p className="text-xs text-slate-500">School-wide attendance analytics and trends</p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : reports.length === 0 ? (
        <EmptyState
          title="No Reports Available"
          description="Attendance reports will appear here once data is collected."
          icon={<BarChart2 className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {reports.map((rep, idx) => {
            const pct = Number(rep.percentage ?? 0);
            const barColor = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-rose-500';
            return (
              <div key={idx} className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-semibold text-slate-900">{rep.period}</p>
                  <span className="text-sm font-bold text-emerald-700">{rep.percentage}%</span>
                </div>
                {/* Progress Bar */}
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden mb-3">
                  <div
                    className={`h-full rounded-full transition-all ${barColor}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="flex gap-4">
                  <span className="flex items-center gap-1.5 text-xs text-emerald-700">
                    <Users className="w-3.5 h-3.5" /> {rep.present_count} Present
                  </span>
                  <span className="flex items-center gap-1.5 text-xs text-rose-600">
                    <UserX className="w-3.5 h-3.5" /> {rep.absent_count} Absent
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AttendanceReports;