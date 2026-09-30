// src/pages/student/Exams.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { examService } from '../../services/exam';
import { Exam } from '../../types/exam';
import { ExamCard } from '../../components/exam';
import { CalendarClock } from 'lucide-react';
import { LoadingSkeleton, EmptyState } from '../../components/shared';

export const StudentExamsPage: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    examService
      .listExams({ limit: 100 })
      .then(data => {
        // Schedule visibility only. The backend already scopes this list to
        // the student's own class/section and academic year, and only drops
        // ARCHIVED exams — publication is NOT a condition for seeing the
        // schedule. Marks/results come from /marks/my-marks, which stays
        // empty until the Principal publishes.
        setExams(data.items.filter(e => (e.status || '').toUpperCase() !== 'ARCHIVED'));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const isPublished = (exam: Exam) => (exam.status || '').toUpperCase() === 'PUBLISHED';

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Scheduled Examinations</h1>
        <p className="text-xs text-slate-500">
          Your class exam schedule. Results appear here once they are published.
        </p>
      </div>

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : exams.length === 0 ? (
        <EmptyState
          title="No Exams Scheduled"
          description="Your school has not scheduled any examinations for your class yet."
          icon={<CalendarClock className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {exams.map(exam => (
            <ExamCard
              key={exam.id}
              exam={exam}
              onClick={isPublished(exam) ? () => navigate('/student/marks') : undefined}
              actions={
                isPublished(exam) ? (
                  <button
                    type="button"
                    className="px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold"
                    onClick={() => navigate('/student/marks')}
                  >
                    View Results
                  </button>
                ) : (
                  <span className="px-3 py-1.5 rounded-lg bg-slate-50 text-slate-500 border border-slate-200 text-xs font-semibold">
                    Awaiting Results
                  </span>
                )
              }
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentExamsPage;
