// src/components/shared/AcademicYearSelector.tsx
import React from 'react';
import { CalendarDays, ChevronDown } from 'lucide-react';
import { useAcademicYear } from '../../contexts/AcademicYearContext';

/**
 * Header control that switches the academic year every screen reads from.
 *
 * The choice is persisted (localStorage) and attached to every subsequent API
 * request as `X-Academic-Year-Id`, so changing it re-scopes rosters, exams,
 * marks, attendance, timetable, homework and assignments in one go.
 *
 * Renders nothing while the year list is still loading or when the school has
 * no year configured yet - never a dead control.
 */
export const AcademicYearSelector: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const { academicYears, selectedYear, selectYear, loading, error } = useAcademicYear();

  if (loading || error || academicYears.length === 0) return null;

  return (
    <label className="relative flex items-center gap-1.5 rounded-xl border border-slate-200/80 bg-white pl-2.5 pr-7 py-1.5 text-slate-700 hover:border-emerald-300 transition-colors max-w-[190px]">
      <CalendarDays className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" aria-hidden="true" />
      {!compact && (
        <span className="hidden sm:inline text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Year
        </span>
      )}
      <select
        aria-label="Academic year"
        value={selectedYear?.id ?? ''}
        onChange={(e) => {
          const id = Number(e.target.value);
          if (Number.isFinite(id) && id > 0) selectYear(id);
        }}
        className="appearance-none bg-transparent text-xs font-semibold text-slate-800 focus:outline-none cursor-pointer pr-1 truncate"
      >
        {academicYears.map((year) => (
          <option key={year.id} value={year.id}>
            {year.name}
            {year.is_active ? ' · Active' : ` · ${year.status}`}
          </option>
        ))}
      </select>
      <ChevronDown
        className="w-3.5 h-3.5 text-slate-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
        aria-hidden="true"
      />
    </label>
  );
};

export default AcademicYearSelector;
