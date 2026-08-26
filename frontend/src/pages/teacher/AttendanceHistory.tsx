// src/pages/teacher/AttendanceHistory.tsx
import React, { useState, useEffect } from 'react';
import { History } from 'lucide-react';
import { EmptyState, LoadingSkeleton, StatusBadge } from '../../components/shared';

export const TeacherAttendanceHistory: React.FC = () => {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch attendance history using existing service
    setLoading(false);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Attendance History</h1>
        <p className="text-xs text-slate-500">Past attendance records you've submitted</p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loading ? (
        <LoadingSkeleton type="list" count={5} />
      ) : history.length === 0 ? (
        <EmptyState
          title="No History Found"
          description="No past attendance records have been submitted yet."
          icon={<History className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {history.map((record, index) => (
            <div
              key={index}
              className="flex items-center gap-3 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs"
            >
              <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-bold text-blue-700">
                  {record.student_name?.charAt(0) ?? '?'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-900 truncate">{record.student_name}</p>
                <p className="text-xs text-slate-500">{record.date}</p>
              </div>
              <StatusBadge status={record.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TeacherAttendanceHistory;