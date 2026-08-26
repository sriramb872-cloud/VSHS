// src/pages/teacher/ExamDetails.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock, Award, BookOpen, Layers } from 'lucide-react';
import { examService } from '../../services/exam';
import { Exam } from '../../types/exam';

export const TeacherExamDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [exam, setExam] = useState<Exam | null>(null);

  useEffect(() => {
    if (id) {
      examService.getExamById(Number(id)).then(setExam).catch(console.error);
    }
  }, [id]);

  if (!exam) {
    return <div className="text-center py-12 text-gray-500">Loading exam details...</div>;
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Exams
      </button>

      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{exam.name}</h1>
            <span className="inline-block mt-1 px-3 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
              {exam.exam_type}
            </span>
          </div>
          <div className="text-right">
            <span className="block text-xs text-gray-500">Max Marks</span>
            <span className="text-lg font-bold text-gray-900">{exam.maximum_marks}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 my-6 p-4 bg-gray-50 rounded-lg text-sm">
          <div>
            <span className="block text-gray-500 text-xs">Date</span>
            <span className="font-semibold text-gray-900">{exam.exam_date}</span>
          </div>
          <div>
            <span className="block text-gray-500 text-xs">Time</span>
            <span className="font-semibold text-gray-900">{exam.start_time} - {exam.end_time}</span>
          </div>
          <div>
            <span className="block text-gray-500 text-xs">Passing Marks</span>
            <span className="font-semibold text-gray-900">{exam.passing_marks}</span>
          </div>
          <div>
            <span className="block text-gray-500 text-xs">Grade / Sec</span>
            <span className="font-semibold text-gray-900">{exam.grade_id} - {exam.section_id}</span>
          </div>
        </div>

        {exam.instructions && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">Instructions</h2>
            <div className="text-gray-600 whitespace-pre-wrap leading-relaxed bg-amber-50/50 p-4 rounded-lg border border-amber-100">
              {exam.instructions}
            </div>
          </div>
        )}

        <div className="pt-4 border-t border-gray-100 text-xs text-gray-400">
          Subject ID: {exam.subject_id} | Academic Year ID: {exam.academic_year_id}
        </div>
      </div>
    </div>
  );
};

export default TeacherExamDetailsPage;