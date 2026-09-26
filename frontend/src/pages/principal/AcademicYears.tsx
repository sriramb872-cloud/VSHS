// src/pages/principal/AcademicYears.tsx
import React, { useState, useEffect } from 'react';
import { CalendarDays, Plus } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton, StatusBadge } from '../../components/shared';
import { EditModal, ConfirmDialog } from '../../components/EditModal';
import { academicYearsService } from '../../services/academicYears';
import { AcademicYear } from '../../types';

export const AcademicYears: React.FC = () => {
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [editingYear, setEditingYear] = useState<AcademicYear | null>(null);
  const [deletingYear, setDeletingYear] = useState<AcademicYear | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
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
      .createAcademicYear({ name: name.trim(), start_date: startDate, end_date: endDate, is_active: true })
      .then(newYear => {
        setAcademicYears(prev => [...prev, newYear]);
        setName('');
      })
      .catch(() => setError('Failed to create academic year'))
      .finally(() => setIsCreating(false));
  };
  const updateYear = async (year: AcademicYear, payload: Partial<AcademicYear>) => {
    const updated = await academicYearsService.updateAcademicYear(year.id, payload);
    setAcademicYears(items => items.map(item => item.id === year.id ? updated : item));
  };
  const editYear = (year: AcademicYear) => {
    setEditingYear(year);
  };
  const deleteYear = (year: AcademicYear) => {
    setDeletingYear(year);
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
          <input
            aria-label="Start date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            required
          />
          <input
            aria-label="End date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
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
              actions={<div className="flex gap-1" onClick={event => event.stopPropagation()}><button type="button" className="text-xs text-indigo-700" onClick={() => editYear(ay)}>Edit</button><button type="button" className="text-xs text-emerald-700" onClick={() => updateYear(ay, { is_active: !ay.is_active })}>{ay.is_active ? 'Close' : 'Activate'}</button><button type="button" className="text-xs text-rose-700" onClick={() => deleteYear(ay)}>Archive</button></div>}
            />
          ))}
        </div>
      )}

      {editingYear && (
        <EditModal
          title="Edit Academic Year"
          fields={[
            { key: 'name', label: 'Academic Year Name', required: true },
            { key: 'start_date', label: 'Start Date', type: 'date' },
            { key: 'end_date', label: 'End Date', type: 'date' },
          ]}
          initialValues={{
            name: editingYear.name,
            start_date: editingYear.start_date ? String(editingYear.start_date).slice(0, 10) : '',
            end_date: editingYear.end_date ? String(editingYear.end_date).slice(0, 10) : '',
          }}
          onSubmit={async (values) => {
            await updateYear(editingYear, {
              name: values.name.trim(),
              start_date: values.start_date || undefined,
              end_date: values.end_date || undefined,
            });
            setEditingYear(null);
          }}
          onClose={() => setEditingYear(null)}
        />
      )}

      {deletingYear && (
        <ConfirmDialog
          title="Archive Academic Year"
          message={`Are you sure you want to archive ${deletingYear.name}? This is allowed only when it has no active dependencies.`}
          confirmLabel="Archive"
          confirmVariant="danger"
          onConfirm={async () => {
            await academicYearsService.deleteAcademicYear(deletingYear.id);
            setAcademicYears(items => items.filter(item => item.id !== deletingYear.id));
          }}
          onClose={() => setDeletingYear(null)}
        />
      )}
    </div>
  );
};

export default AcademicYears;
