// src/pages/student/Exams.tsx
import React, { useEffect, useState } from 'react';
import { examService } from '../../services/exam';
import { Exam } from '../../types/exam';
import { ExamCard } from '../../components/exam';

export const StudentExamsPage: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    examService
      .listExams()
      .then(data => setExams(data.items))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Exam Schedule</h1>
        <p className="text-sm text-gray-500 mt-1">View upcoming physical examination timetables and schedules.</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading exam schedule...</div>
      ) : exams.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No exam schedules published yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {exams.map(exam => (
            <ExamCard key={exam.id} exam={exam} />
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentExamsPage;/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
