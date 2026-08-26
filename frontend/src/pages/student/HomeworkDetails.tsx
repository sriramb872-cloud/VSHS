// src/pages/student/HomeworkDetails.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, BookOpen, Calendar, Layers, Clock } from 'lucide-react';
import { homeworkService } from '../../services/homework';
import { Homework } from '../../types/homework';
import { LoadingSkeleton, ErrorState } from '../../components/shared';

export const StudentHomeworkDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [homework, setHomework] = useState<Homework | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      setLoading(true);
      setError(null);
      homeworkService
        .getHomeworkById(Number(id))
        .then(setHomework)
        .catch(err => {
          console.error('Failed to load homework details', err);
          setError('Failed to load homework details.');
        })
        .finally(() => setLoading(false));
    }
  }, [id]);

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Homework
      </button>

      {loading ? (
        <LoadingSkeleton type="card" count={1} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => window.location.reload()} />
      ) : !homework ? (
        <div className="p-4 bg-white rounded-2xl border border-slate-200 text-center text-slate-500 text-sm">
          Homework not found.
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-5 space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-100">
            <h1 className="text-lg font-bold text-slate-900">{homework.title}</h1>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-orange-50 text-orange-700 rounded-full text-xs font-semibold w-fit">
              <Calendar className="w-3.5 h-3.5" /> Due: {homework.due_date}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] text-slate-500 block">Subject ID</span>
              <span className="text-sm font-semibold text-slate-900">{homework.subject_id}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] text-slate-500 block">Grade ID</span>
              <span className="text-sm font-semibold text-slate-900">{homework.grade_id}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 col-span-2 sm:col-span-1">
              <span className="text-[11px] text-slate-500 block">Section ID</span>
              <span className="text-sm font-semibold text-slate-900">{homework.section_id}</span>
            </div>
          </div>

          <div>
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Instructions</h2>
            <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed bg-slate-50/50 p-4 rounded-xl border border-slate-100">
              {homework.description}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentHomeworkDetailsPage;