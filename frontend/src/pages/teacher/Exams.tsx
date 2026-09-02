// src/pages/teacher/Exams.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { examService } from '../../services/exam';
import { Exam } from '../../types/exam';
import { ExamCard } from '../../components/exam';
import { ClipboardList } from 'lucide-react';
import { LoadingSkeleton, EmptyState } from '../../components/shared';

export const TeacherExamsPage: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const fetchExams = async () => {
    try {
      setLoading(true);
      const data = await examService.listExams();
      setExams(data.items);
    } catch (error) {
      console.error('Failed to load exams', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExams();
  }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-slate-900">My Class Exams</h1>
          <p className="text-xs text-slate-500">Exams scheduled for your assigned classes and subjects</p>
        </div>
      </div>

      {/* Exam Cards */}
      {loading ? (
        <LoadingSkeleton type="card" count={4} />
      ) : exams.length === 0 ? (
        <EmptyState
          title="No Scheduled Exams"
          description="There are currently no examinations scheduled for your classes."
          icon={<ClipboardList className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {exams.map(exam => (
            <div key={exam.id} className="relative">
              <ExamCard
                exam={exam}
                onClick={() => navigate(`/teacher/exams/${exam.id}`)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TeacherExamsPage;