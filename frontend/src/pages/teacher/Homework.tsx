// src/pages/teacher/Homework.tsx
import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Edit } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { homeworkService } from '../../services/homework';
import { Homework } from '../../types/homework';
import { HomeworkCard } from '../../components/homework';
import { BookOpen } from 'lucide-react';
import { LoadingSkeleton, EmptyState, ConfirmDialog, ErrorState } from '../../components/shared';

export const TeacherHomeworkPage: React.FC = () => {
  const [homeworkList, setHomeworkList] = useState<Homework[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const navigate = useNavigate();

  const fetchHomework = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await homeworkService.listHomework();
      setHomeworkList(data?.items || []);
    } catch (err) {
      console.error('Failed to load homework', err);
      setError('Unable to load homework. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHomework();
  }, []);

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await homeworkService.deleteHomework(deleteId);
      setHomeworkList(prev => prev.filter(h => h.id !== deleteId));
    } catch (err) {
      console.error('Failed to delete homework', err);
    } finally {
      setDeleteId(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-slate-900">My Homework</h1>
          <p className="text-xs text-slate-500">Create and monitor assignments</p>
        </div>
        <button
          onClick={() => navigate('/teacher/homework/create')}
          className="h-10 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
          Create
        </button>
      </div>

      {/* Homework Cards */}
      {loading ? (
        <LoadingSkeleton type="card" count={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchHomework} />
      ) : homeworkList.length === 0 ? (
        <EmptyState
          title="No Homework Created"
          description="Create your first homework assignment for your students."
          icon={<BookOpen className="w-10 h-10 text-slate-300" />}
          action={{ label: 'Create Homework', onClick: () => navigate('/teacher/homework/create') }}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {homeworkList.map(hw => (
            <div key={hw.id} className="relative">
              <HomeworkCard
                homework={hw}
                onClick={() => navigate(`/teacher/homework/${hw.id}`)}
                actions={
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/teacher/homework/edit/${hw.id}`); }}
                      className="p-2 text-slate-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
                      title="Edit"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteId(hw.id); }}
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
        title="Delete Homework?"
        message="This will permanently delete this homework assignment."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
};

export default TeacherHomeworkPage;