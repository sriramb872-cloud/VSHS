// src/pages/teacher/HomeworkDetails.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Calendar, BookOpen, Layers, User } from 'lucide-react';
import { homeworkService } from '../../services/homework';
import { Homework } from '../../types/homework';

export const TeacherHomeworkDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [homework, setHomework] = useState<Homework | null>(null);

  useEffect(() => {
    if (id) {
      homeworkService.getHomeworkById(Number(id)).then(setHomework).catch(console.error);
    }
  }, [id]);

  if (!homework) {
    return <div className="text-center py-12 text-gray-500">Loading homework details...</div>;
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Homework
      </button>

      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <div className="flex items-start justify-between">
          <h1 className="text-2xl font-bold text-gray-900">{homework.title}</h1>
          <span className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-sm font-medium">
            Due: {homework.due_date}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 my-6 p-4 bg-gray-50 rounded-lg text-sm">
          <div>
            <span className="block text-gray-500 text-xs">Subject ID</span>
            <span className="font-semibold text-gray-900">{homework.subject_id}</span>
          </div>
          <div>
            <span className="block text-gray-500 text-xs">Grade ID</span>
            <span className="font-semibold text-gray-900">{homework.grade_id}</span>
          </div>
          <div>
            <span className="block text-gray-500 text-xs">Section ID</span>
            <span className="font-semibold text-gray-900">{homework.section_id}</span>
          </div>
          <div>
            <span className="block text-gray-500 text-xs">Academic Year</span>
            <span className="font-semibold text-gray-900">{homework.academic_year_id}</span>
          </div>
        </div>

        <div>
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">Instructions</h2>
          <div className="text-gray-600 whitespace-pre-wrap leading-relaxed">{homework.description}</div>
        </div>

        <div className="mt-8 pt-4 border-t border-gray-100 text-xs text-gray-400">
          Created on: {new Date(homework.created_at).toLocaleString()}
        </div>
      </div>
    </div>
  );
};

export default TeacherHomeworkDetailsPage;