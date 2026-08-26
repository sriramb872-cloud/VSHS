// src/pages/principal/HomeworkDetails.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { BookOpen, Calendar, User, ChevronLeft, FileText } from 'lucide-react';
import { LoadingSkeleton, EmptyState } from '../../components/shared';
import { homeworkService } from '../../services/homework';
import { Homework } from '../../types';

export const HomeworkDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [homework, setHomework] = useState<Homework | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    homeworkService
      .getHomework(Number(id))
      .then(setHomework)
      .catch(() => setError('Failed to load homework details'))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="w-9 h-9 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-600 hover:bg-slate-50 active:scale-95 transition-all"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-900">Homework Details</h1>
          <p className="text-xs text-slate-500">Assignment #{id}</p>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loading ? (
        <LoadingSkeleton type="card" count={2} />
      ) : !homework ? (
        <EmptyState
          title="Homework Not Found"
          description="The homework assignment could not be located."
          icon={<BookOpen className="w-10 h-10 text-slate-300" />}
          action={{ label: 'Go Back', onClick: () => navigate(-1) }}
        />
      ) : (
        <div className="space-y-3">
          {/* Title Card */}
          <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-medium">Assignment Title</p>
                <p className="text-base font-bold text-slate-900">{homework.title}</p>
              </div>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">{homework.description}</p>
          </div>

          {/* Meta Details */}
          <div className="grid grid-cols-3 gap-2.5">
            <div className="bg-white rounded-xl p-3 border border-slate-200/80 text-center">
              <FileText className="w-4 h-4 text-emerald-600 mx-auto mb-1" />
              <p className="text-xs text-slate-500">Subject</p>
              <p className="text-xs font-semibold text-slate-900 mt-0.5">{homework.subject}</p>
            </div>
            <div className="bg-white rounded-xl p-3 border border-slate-200/80 text-center">
              <User className="w-4 h-4 text-emerald-600 mx-auto mb-1" />
              <p className="text-xs text-slate-500">Teacher</p>
              <p className="text-xs font-semibold text-slate-900 mt-0.5">{homework.teacher_name}</p>
            </div>
            <div className="bg-white rounded-xl p-3 border border-slate-200/80 text-center">
              <Calendar className="w-4 h-4 text-emerald-600 mx-auto mb-1" />
              <p className="text-xs text-slate-500">Due Date</p>
              <p className="text-xs font-semibold text-slate-900 mt-0.5">{homework.due_date}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomeworkDetails;