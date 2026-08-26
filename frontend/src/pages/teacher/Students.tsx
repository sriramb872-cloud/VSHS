// src/pages/teacher/Students.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Users, ChevronRight, Phone } from 'lucide-react';
import { EmptyState, LoadingSkeleton } from '../../components/shared';

export const TeacherStudents: React.FC = () => {
  const [students, setStudents] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch assigned students using existing service
    setLoading(false);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">My Students</h1>
        <p className="text-xs text-slate-500">Students assigned to your classes</p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loading ? (
        <LoadingSkeleton type="list" count={5} />
      ) : students.length === 0 ? (
        <EmptyState
          title="No Students Assigned"
          description="No students have been assigned to your classes yet."
          icon={<Users className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {students.map((st) => (
            <Link
              key={st.id}
              to={`/teacher/students/${st.id}`}
              className="flex items-center gap-3 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs hover:shadow-md active:scale-[0.98] transition-all"
            >
              <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-bold text-blue-700">
                  {st.full_name?.charAt(0) ?? '?'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-900 truncate">{st.full_name}</p>
                <div className="flex items-center gap-3 mt-0.5">
                  {st.mobile_number && (
                    <span className="flex items-center gap-1 text-xs text-slate-500">
                      <Phone className="w-3 h-3" /> {st.mobile_number}
                    </span>
                  )}
                  {st.grade_section && (
                    <span className="text-xs text-slate-500">{st.grade_section}</span>
                  )}
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default TeacherStudents;