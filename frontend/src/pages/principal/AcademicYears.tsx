// src/pages/principal/AcademicYears.tsx
import React, { useState, useEffect } from 'react';
import { CalendarDays, Plus } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton, StatusBadge } from '../../components/shared';
import { academicYearsService } from '../../services/academicYears';
import { AcademicYear } from '../../types';

export const AcademicYears: React.FC = () => {
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    academicYearsService
      .listAcademicYears()
      .then(setAcademicYears)
      .catch(() => setError('Failed to load academic years'))
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsCreating(true);
    academicYearsService
      .createAcademicYear({ name: name.trim() })
      .then(newYear => {
        setAcademicYears(prev => [...prev, newYear]);
        setName('');
      })
      .catch(() => setError('Failed to create academic year'))
      .finally(() => setIsCreating(false));
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Academic Years</h1>
        <p className="text-xs text-slate-500">School term and calendar years</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Add Academic Session</h3>
        <form onSubmit={handleCreate} className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            className="flex-1 h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. 2026 - 2027"
            required
          />
          <button
            type="submit"
            disabled={isCreating}
            className="h-11 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-1.5 disabled:opacity-60"
          >
            <Plus className="w-4 h-4" />
            <span>{isCreating ? 'Creating...' : 'Add Session'}</span>
          </button>
        </form>
      </div>

      {loading ? (
        <LoadingSkeleton type="list" count={3} />
      ) : academicYears.length === 0 ? (
        <EmptyState
          title="No Academic Sessions"
          description="Create your first academic year above."
          icon={<CalendarDays className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {academicYears.map((ay) => (
            <MobileListItem
              key={ay.id}
              title={ay.name}
              icon={<CalendarDays className="w-5 h-5 text-emerald-600" />}
              avatarBg="bg-emerald-50 text-emerald-600"
              badge={<StatusBadge status={ay.is_active ? 'ACTIVE' : 'INACTIVE'} />}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default AcademicYears;