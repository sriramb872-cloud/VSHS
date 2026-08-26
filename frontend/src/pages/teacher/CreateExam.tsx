// src/pages/teacher/Exams.tsx
import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Edit } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { examService } from '../../services/exam';
import { Exam } from '../../types/exam';
import { ExamCard } from '../../components/exam';

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

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this exam schedule?')) {
      try {
        await examService.deleteExam(id);
        setExams(prev => prev.filter(e => e.id !== id));
      } catch (error) {
        console.error('Failed to delete exam', error);
      }
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Examination Schedules</h1>
          <p className="text-sm text-gray-500 mt-1">Manage physical offline exam timetables and details.</p>
        </div>
        <button
          onClick={() => navigate('/teacher/exams/create')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          <Plus className="w-4 h-4" /> Create Exam Schedule
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading exams...</div>
      ) : exams.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No exam schedules found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {exams.map(exam => (
            <ExamCard
              key={exam.id}
              exam={exam}
              onClick={() => navigate(`/teacher/exams/${exam.id}`)}
              actions={
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => navigate(`/teacher/exams/edit/${exam.id}`)}
                    className="p-1.5 text-gray-500 hover:text-indigo-600 rounded"
                    title="Edit"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(exam.id)}
                    className="p-1.5 text-gray-500 hover:text-red-600 rounded"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              }
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default TeacherExamsPage;/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
