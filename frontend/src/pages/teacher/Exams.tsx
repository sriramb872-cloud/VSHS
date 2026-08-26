// src/pages/teacher/Exams.tsx
import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Edit } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { examService } from '../../services/exam';
import { Exam } from '../../types/exam';
import { ExamCard } from '../../components/exam';
import { ClipboardList } from 'lucide-react';
import { LoadingSkeleton, EmptyState, ConfirmDialog } from '../../components/shared';

export const TeacherExamsPage: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
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

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await examService.deleteExam(deleteId);
      setExams(prev => prev.filter(e => e.id !== deleteId));
    } catch (error) {
      console.error('Failed to delete exam', error);
    } finally {
      setDeleteId(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-slate-900">My Exams</h1>
          <p className="text-xs text-slate-500">Create and manage exam schedules</p>
        </div>
        <button
          onClick={() => navigate('/teacher/exams/create')}
          className="h-10 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
          Create
        </button>
      </div>

      {/* Exam Cards */}
      {loading ? (
        <LoadingSkeleton type="card" count={4} />
      ) : exams.length === 0 ? (
        <EmptyState
          title="No Exam Schedules"
          description="Create your first examination schedule."
          icon={<ClipboardList className="w-10 h-10 text-slate-300" />}
          action={{ label: 'Create Exam', onClick: () => navigate('/teacher/exams/create') }}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {exams.map(exam => (
            <div key={exam.id} className="relative">
              <ExamCard
                exam={exam}
                onClick={() => navigate(`/teacher/exams/${exam.id}`)}
                actions={
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/teacher/exams/edit/${exam.id}`); }}
                      className="p-2 text-slate-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
                      title="Edit"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteId(exam.id); }}
                      className="p-2 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                }
              />
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={deleteId !== null}
        title="Delete Exam?"
        message="This will permanently delete this exam schedule and all associated data."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
};

export default TeacherExamsPage;