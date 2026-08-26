// src/pages/principal/Attendance.tsx
import React, { useState, useEffect } from 'react';
import { ClipboardCheck } from 'lucide-react';
import { EmptyState, LoadingSkeleton, StatusBadge } from '../../components/shared';
import { attendanceService } from '../../services/attendance';
import { AttendanceRecord } from '../../types';

export const Attendance: React.FC = () => {
  const [attendanceList, setAttendanceList] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    attendanceService
      .getAttendance({ attendance_date: today })
      .then(setAttendanceList)
      .catch(() => setError('Failed to load attendance records'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Attendance Overview</h1>
        <p className="text-xs text-slate-500">Today's student attendance across all sections</p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loading ? (
        <LoadingSkeleton type="list" count={5} />
      ) : attendanceList.length === 0 ? (
        <EmptyState
          title="No Attendance Records"
          description="No attendance records have been marked for today."
          icon={<ClipboardCheck className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {attendanceList.map((record) => (
            <div
              key={record.id}
              className="flex items-center gap-3 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs"
            >
              <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-bold text-emerald-700">
                  {record.student_id}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-900 truncate">Student #{record.student_id}</p>
                <p className="text-xs text-slate-500">Section #{record.section_id} · {record.date}</p>
              </div>
              <StatusBadge status={record.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Attendance;