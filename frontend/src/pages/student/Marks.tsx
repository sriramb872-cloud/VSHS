// src/pages/student/Marks.tsx
import React, { useEffect, useState } from 'react';
import { marksService } from '../../services/marks';
import { examService } from '../../services/exam';
import { Mark } from '../../types/marks';
import { Exam } from '../../types/exam';
import { MarkCard } from '../../components/marks';

export const StudentMarksPage: React.FC = () => {
  const [marks, setMarks] = useState<Mark[]>([]);
  const [exams, setExams] = useState<Record<number, Exam>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([marksService.listMarks(), examService.listExams()])
      .then(([marksData, examsData]) => {
        setMarks(marksData.items);
        const examMap: Record<number, Exam> = {};
        examsData.items.forEach(ex => {
          examMap[ex.id] = ex;
        });
        setExams(examMap);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Exam Marks</h1>
        <p className="text-sm text-gray-500 mt-1">View your evaluated marks across examinations.</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading your marks...</div>
      ) : marks.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No marks records available yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {marks.map(mark => {
            const exam = exams[mark.exam_id];
            return (
              <MarkCard
                key={mark.id}
                mark={mark}
                examName={exam?.name}
                maximumMarks={exam?.maximum_marks}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};

export default StudentMarksPage;
/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
