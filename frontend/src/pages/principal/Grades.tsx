// src/pages/principal/Grades.tsx
import React, { useState, useEffect } from 'react';
import { Award, Plus } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton } from '../../components/shared';
import { gradesService } from '../../services/grades';
import { Grade } from '../../types';

export const Grades: React.FC = () => {
  const [grades, setGrades] = useState<Grade[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [gradeName, setGradeName] = useState('');

  useEffect(() => {
    gradesService
      .listGrades()
      .then(setGrades)
      .catch(() => setError('Failed to load grades'))
      .finally(() => setLoading(false));
  }, []);

  const handleCreateGrade = (e: React.FormEvent) => {
    e.preventDefault();
    if (!gradeName.trim()) return;
    gradesService
      .createGrade({ name: gradeName.trim() })
      .then(newGrade => {
        setGrades(prev => [...prev, newGrade]);
        setGradeName('');
      })
      .catch(() => setError('Failed to create grade'));
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Grade Management</h1>
        <p className="text-xs text-slate-500">Configure academic grades & levels</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Add Grade Level</h3>
        <form onSubmit={handleCreateGrade} className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            className="flex-1 h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            value={gradeName}
            onChange={(e) => setGradeName(e.target.value)}
            placeholder="e.g. Grade 10"
            required
          />
          <button
            type="submit"
            className="h-11 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Create Grade</span>
          </button>
        </form>
      </div>

      {loading ? (
        <LoadingSkeleton type="list" count={3} />
      ) : grades.length === 0 ? (
        <EmptyState
          title="No Grades Configured"
          description="Create your first grade level above."
          icon={<Award className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {grades.map((g) => (
            <MobileListItem
              key={g.id}
              title={g.name}
              icon={<Award className="w-5 h-5 text-emerald-600" />}
              avatarBg="bg-emerald-50 text-emerald-600"
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default Grades;