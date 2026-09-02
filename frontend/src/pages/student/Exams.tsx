// src/pages/student/Exams.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { examService } from '../../services/exam';
import { Exam } from '../../types/exam';
import { ExamCard } from '../../components/exam';
import { Award } from 'lucide-react';
import { LoadingSkeleton, EmptyState } from '../../components/shared';

export const StudentExamsPage: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    examService
      .listExams({ status: 'PUBLISHED' })
      .then(data => {
        // Double check filtering for published exams
        setExams(data.items.filter(e => (e.status || '').toUpperCase() === 'PUBLISHED'));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Published Examinations</h1>
        <p className="text-xs text-slate-500">View published exams and grades</p>
      </div>

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : exams.length === 0 ? (
        <EmptyState
          title="No Published Exams"
          description="Exam results and schedules will appear here once officially published by your school."
          icon={<Award className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {exams.map(exam => (
            <ExamCard
              key={exam.id}
              exam={exam}
              onClick={() => navigate('/student/marks')}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentExamsPage;
