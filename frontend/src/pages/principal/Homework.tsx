// src/pages/principal/Homework.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, ChevronRight, Calendar, User } from 'lucide-react';
import { EmptyState, LoadingSkeleton } from '../../components/shared';
import { homeworkService } from '../../services/homework';
import { Homework as HomeworkType } from '../../types';

export const Homework: React.FC = () => {
  const [homeworkList, setHomeworkList] = useState<HomeworkType[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    homeworkService
      .listHomework()
      .then(data => setHomeworkList(data.items))
      .catch(() => setError('Failed to load homework'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Homework Overview</h1>
        <p className="text-xs text-slate-500">Published assignments across all classes</p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : homeworkList.length === 0 ? (
        <EmptyState
          title="No Homework Published"
          description="No homework assignments have been published yet."
          icon={<BookOpen className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {homeworkList.map((hw) => (
            <Link
              key={hw.id}
              to={`/principal/homework/${hw.id}`}
              className="flex items-center gap-3 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs hover:shadow-md active:scale-[0.98] transition-all"
            >
              <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
                <BookOpen className="w-5 h-5 text-emerald-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-900 truncate">{hw.title}</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="flex items-center gap-1 text-xs text-slate-500">
                    <User className="w-3 h-3" /> {hw.teacher_name}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-slate-500">
                    <Calendar className="w-3 h-3" /> {hw.due_date}
                  </span>
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

export default Homework;