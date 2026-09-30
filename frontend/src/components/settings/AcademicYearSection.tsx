// src/components/settings/AcademicYearSection.tsx
/**
 * Academic Year management section (create / list / activate / view).
 *
 * One implementation shared by Settings → Academic Year and the Academic
 * Years page, so both always show the same catalogue, the same
 * "one ACTIVE year per school" rule and the same create/activate behaviour.
 *
 * Two distinct concepts are surfaced here:
 *
 *   ACTIVE year   – the school's single operational year (zero or one per
 *                   school). Changing it is a deliberate, confirmed action
 *                   that closes the previously active year.
 *   VIEWING year  – whichever year the signed-in user is currently looking
 *                   at. Switching it only re-scopes what THIS user reads;
 *                   it never touches the school's Active year.
 *
 * A school may legitimately own zero years (a freshly created one), so every
 * state renders a usable screen: the create form is always reachable.
 */
import React, { useState } from 'react';
import {
  Archive,
  CalendarDays,
  CheckCircle2,
  Eye,
  Pencil,
  Plus,
  Trash2,
} from 'lucide-react';
import { EmptyState, LoadingSkeleton, MobileListItem, StatusBadge } from '../shared';
import { ConfirmDialog, EditModal } from '../EditModal';
import { academicYearsService } from '../../services/academicYears';
import { useAcademicYear } from '../../contexts/AcademicYearContext';
import { AcademicYear, AcademicYearUpdatePayload } from '../../types';

/** Pull the server's `detail` out of an axios error so validation shows up. */
const errorDetail = (err: unknown, fallback: string): string => {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown };
    if (first && typeof first.msg === 'string') return first.msg;
  }
  return fallback;
};

const formatDate = (value?: string | null): string =>
  value ? String(value).slice(0, 10) : '—';

interface AcademicYearSectionProps {
  /**
   * Card heading. Defaults to `Academic Year` (Settings). Pass `null` when the
   * host page already renders its own page title (Academic Years page).
   */
  heading?: string | null;
}

export const AcademicYearSection: React.FC<AcademicYearSectionProps> = ({
  heading = 'Academic Year',
}) => {
  const {
    academicYears,
    activeYear,
    selectedYear,
    selectedYearId,
    loading,
    refreshYears,
    selectYear,
    activateYear,
  } = useAcademicYear();

  const [editingYear, setEditingYear] = useState<AcademicYear | null>(null);
  const [deletingYear, setDeletingYear] = useState<AcademicYear | null>(null);
  const [archivingYear, setArchivingYear] = useState<AcademicYear | null>(null);
  const [activatingYear, setActivatingYear] = useState<AcademicYear | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [makeActive, setMakeActive] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const flashError = (err: unknown, fallback: string) => {
    setError(errorDetail(err, fallback));
    setNotice(null);
  };

  const reload = async () => refreshYears();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isCreating) return;

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError('Academic year name is required.');
      setNotice(null);
      return;
    }
    if (!startDate || !endDate) {
      setError('Start date and end date are both required.');
      setNotice(null);
      return;
    }
    // `YYYY-MM-DD` strings compare lexicographically in date order.
    if (endDate <= startDate) {
      setError('End date must be after the start date.');
      setNotice(null);
      return;
    }

    setIsCreating(true);
    setError(null);
    setNotice(null);
    try {
      await academicYearsService.createAcademicYear({
        name: trimmedName,
        start_date: startDate,
        end_date: endDate,
        // Creating an *active* year atomically closes the previous one, so it
        // is opt-in rather than the default: future years can be staged first.
        is_active: makeActive,
      });
      await reload();
      setName('');
      setStartDate('');
      setEndDate('');
      setMakeActive(false);
      setNotice(`Academic year "${trimmedName}" created.`);
    } catch (err) {
      flashError(err, 'Failed to create academic year');
    } finally {
      setIsCreating(false);
    }
  };

  const updateYear = async (year: AcademicYear, payload: AcademicYearUpdatePayload) => {
    setError(null);
    setNotice(null);
    try {
      await academicYearsService.updateAcademicYear(year.id, payload);
      await reload();
      setNotice(`${year.name} updated.`);
    } catch (err) {
      flashError(err, `Failed to update ${year.name}`);
    }
  };

  const doActivate = async (year: AcademicYear) => {
    setBusyId(year.id);
    setError(null);
    setNotice(null);
    try {
      await activateYear(year.id);
      await reload();
      setNotice(`${year.name} is now the active academic year.`);
    } catch (err) {
      flashError(err, `Failed to activate ${year.name}`);
    } finally {
      setBusyId(null);
      setActivatingYear(null);
    }
  };

  const doArchive = async (year: AcademicYear) => {
    setBusyId(year.id);
    setError(null);
    setNotice(null);
    try {
      await academicYearsService.archiveAcademicYear(year.id);
      await reload();
      setNotice(`${year.name} archived. Its data stays viewable.`);
    } catch (err) {
      flashError(err, `Failed to archive ${year.name}`);
    } finally {
      setBusyId(null);
      setArchivingYear(null);
    }
  };

  const doDelete = async (year: AcademicYear) => {
    setBusyId(year.id);
    setError(null);
    setNotice(null);
    try {
      await academicYearsService.deleteAcademicYear(year.id);
      const years = await reload();
      if (selectedYearId === year.id) {
        // The year being viewed just disappeared - fall back to the active one
        // rather than leaving the header pointing at a deleted id.
        const fallback = years.find((y) => y.is_active) ?? years[0];
        if (fallback) selectYear(fallback.id);
      }
      setNotice(`${year.name} deleted.`);
    } catch (err) {
      // 400 = active year, 409 = the year still holds data: both messages
      // tell the principal what to do instead (usually: archive it).
      flashError(err, `Failed to delete ${year.name}`);
    } finally {
      setBusyId(null);
      setDeletingYear(null);
    }
  };

  /** View-only switch: never changes which year is Active. */
  const doView = (year: AcademicYear) => {
    selectYear(year.id);
    setNotice(`Now viewing ${year.name}. The Active year is unchanged.`);
    setError(null);
  };

  const headingRow =
    heading === null ? null : (
      <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
        <CalendarDays className="w-4 h-4 text-emerald-600" />
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">{heading}</h3>
      </div>
    );

  if (loading && academicYears.length === 0) {
    return (
      <div className="space-y-3">
        {headingRow}
        <LoadingSkeleton type="list" count={3} />
      </div>
    );
  }

  const viewingAnother =
    !!selectedYear && !!activeYear && selectedYear.id !== activeYear.id;

  return (
    <div className="space-y-4">
      {notice && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-xs font-medium">
          ✓ {notice}
        </div>
      )}
      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">
          {error}
        </div>
      )}

      <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs space-y-3">
        {headingRow}

        {/* ── ACTIVE year: the school's single operational year ─────────── */}
        <div
          className={`rounded-xl border p-3 flex items-start gap-2.5 ${
            activeYear
              ? 'border-emerald-200 bg-emerald-50'
              : 'border-amber-200 bg-amber-50'
          }`}
        >
          {activeYear ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
          ) : (
            <CalendarDays className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
          )}
          <div className="min-w-0 flex-1">
            <p
              className={`text-[10px] font-bold uppercase tracking-wider ${
                activeYear ? 'text-emerald-600' : 'text-amber-600'
              }`}
            >
              Active Academic Year
            </p>
            <p
              className={`text-sm font-bold truncate ${
                activeYear ? 'text-emerald-900' : 'text-amber-800'
              }`}
            >
              {activeYear ? activeYear.name : academicYears.length === 0 ? 'None yet' : 'None'}
            </p>
            <p
              className={`text-[11px] mt-0.5 leading-relaxed ${
                activeYear ? 'text-emerald-700/90' : 'text-amber-700'
              }`}
            >
              {activeYear
                ? viewingAnother
                  ? `The school runs on ${activeYear.name}.`
                  : `The school runs on ${activeYear.name}. You are viewing this year.`
                : academicYears.length === 0
                  ? 'No Academic Year configured yet — create the first one below.'
                  : 'No year is marked Active — activate one below.'}
            </p>
          </div>
        </div>

        {/* ── VIEWING year: what THIS user reads (never the Active year) ── */}
        {viewingAnother && selectedYear && activeYear && (
          <div className="rounded-xl border border-[var(--brand-border)] bg-[var(--brand-light)] p-3 flex items-start gap-2.5">
            <Eye className="w-4 h-4 text-[var(--brand)] mt-0.5 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--brand)]">
                Viewing Academic Year
              </p>
              <p className="text-sm font-bold text-[var(--brand-strong)] truncate">{selectedYear.name}</p>
              <p className="text-[11px] text-[color-mix(in_srgb,var(--brand-strong)_90%,transparent)] mt-0.5 leading-relaxed">
                You are reading {selectedYear.name} data. The school's Active year stays{' '}
                <strong className="font-bold">{activeYear.name}</strong> — viewing another year
                never changes it.
              </p>
            </div>
            <button
              type="button"
              onClick={() => doView(activeYear)}
              className="flex-shrink-0 text-[11px] font-bold text-[var(--brand-strong)] hover:text-[var(--brand-strong)] underline underline-offset-2"
            >
              Back to Active
            </button>
          </div>
        )}

        {/* ── Create ────────────────────────────────────────────────────── */}
        <div className="pt-1 border-t border-slate-100">
          {heading === null && (
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider pt-3 pb-2">
              Add Academic Year
            </h3>
          )}
          <form onSubmit={handleCreate} className="space-y-2">
            <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2">
              <input
                type="text"
                aria-label="Academic year name"
                className="flex-1 min-w-[180px] h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. 2026-2027"
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
                className="h-11 px-5 shrink-0 sm:ml-auto rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-1.5 disabled:opacity-60"
              >
                <Plus className="w-4 h-4" />
                <span>{isCreating ? 'Creating...' : 'Create Academic Year'}</span>
              </button>
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={makeActive}
                onChange={(e) => setMakeActive(e.target.checked)}
                className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
              />
              Make Active
              <span className="text-slate-400">
                {academicYears.length > 0
                  ? '(closes the currently active year)'
                  : '(this becomes the school\'s Active year)'}
              </span>
            </label>
          </form>
        </div>
      </div>

      {/* ── Every year the school owns ──────────────────────────────────── */}
      {academicYears.length === 0 ? (
        <EmptyState
          title="No Academic Years"
          description="Create your first Academic Year above. A new school is allowed to start with none."
          icon={<CalendarDays className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {academicYears.map((ay) => {
            // `activeYear` is the single canonical "Active" row, so the UI can
            // never mark two years Active at the same time.
            const isActive = activeYear?.id === ay.id;
            const status = isActive ? 'ACTIVE' : ay.status === 'ACTIVE' ? 'CLOSED' : ay.status;
            const isArchived = status === 'ARCHIVED';
            const isSelected = selectedYearId === ay.id;
            return (
              <MobileListItem
                key={ay.id}
                title={ay.name}
                subtitle={`${formatDate(ay.start_date)} → ${formatDate(ay.end_date)}`}
                icon={<CalendarDays className="w-5 h-5 text-emerald-600" />}
                avatarBg={
                  isActive ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'
                }
                badge={
                  <span className="flex items-center gap-1.5">
                    <StatusBadge status={status} />
                    {isActive && (
                      <span className="text-[11px] font-semibold text-emerald-700">● Active</span>
                    )}
                    {isSelected && !isActive && (
                      <span className="text-[11px] font-semibold text-[var(--brand)]">Viewing</span>
                    )}
                  </span>
                }
                actions={
                  <div
                    className="flex flex-wrap justify-end gap-x-2.5 gap-y-1"
                    onClick={(event) => event.stopPropagation()}
                  >
                    {!isSelected && (
                      <button
                        type="button"
                        className="text-xs font-medium text-[var(--brand-strong)] flex items-center gap-1"
                        onClick={() => doView(ay)}
                        title="View this year's data without changing the Active year"
                      >
                        <Eye className="w-3 h-3" />
                        View
                      </button>
                    )}
                    {!isActive && !isArchived && (
                      <button
                        type="button"
                        className="text-xs font-medium text-emerald-700 disabled:opacity-50"
                        disabled={busyId === ay.id}
                        onClick={() => setActivatingYear(ay)}
                      >
                        Activate
                      </button>
                    )}
                    {!isArchived && (
                      <button
                        type="button"
                        className="text-xs font-medium text-[var(--brand-strong)]"
                        onClick={() => setEditingYear(ay)}
                      >
                        <Pencil className="w-3 h-3 inline -mt-0.5 mr-1" />
                        Edit
                      </button>
                    )}
                    {!isArchived && !isActive && (
                      <button
                        type="button"
                        className="text-xs font-medium text-amber-700 disabled:opacity-50"
                        disabled={busyId === ay.id}
                        onClick={() => setArchivingYear(ay)}
                      >
                        <Archive className="w-3 h-3 inline -mt-0.5 mr-1" />
                        Archive
                      </button>
                    )}
                    {!isActive && !isArchived && (
                      <button
                        type="button"
                        className="text-xs font-medium text-rose-700 disabled:opacity-50"
                        disabled={busyId === ay.id}
                        onClick={() => setDeletingYear(ay)}
                      >
                        <Trash2 className="w-3 h-3 inline -mt-0.5 mr-1" />
                        Delete
                      </button>
                    )}
                  </div>
                }
              />
            );
          })}
        </div>
      )}

      <p className="text-[11px] text-slate-400 leading-relaxed">
        Exactly one Academic Year is Active per school. Years that hold enrollments, exams, marks,
        attendance or any other records cannot be deleted — archive them instead; the history stays
        readable from the year selector.
      </p>

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
            // Date ordering / overlap is re-checked server-side; its `detail`
            // is surfaced by EditModal, so a bad range never saves silently.
            await updateYear(editingYear, {
              name: String(values.name || '').trim(),
              start_date: String(values.start_date || '').slice(0, 10) || undefined,
              end_date: String(values.end_date || '').slice(0, 10) || undefined,
            });
            setEditingYear(null);
          }}
          onClose={() => setEditingYear(null)}
        />
      )}

      {activatingYear && (
        <ConfirmDialog
          title="Activate Academic Year"
          message={`Activate ${activatingYear.name}? The currently active year will be closed at the same time, and every screen will switch to the new year. Only one year can be Active per school.`}
          confirmLabel="Activate"
          confirmVariant="primary"
          onConfirm={() => doActivate(activatingYear)}
          onClose={() => setActivatingYear(null)}
        />
      )}

      {archivingYear && (
        <ConfirmDialog
          title="Archive Academic Year"
          message={`Archive ${archivingYear.name}? It becomes read-only but all of its data stays viewable from the year selector.`}
          confirmLabel="Archive"
          confirmVariant="danger"
          onConfirm={() => doArchive(archivingYear)}
          onClose={() => setArchivingYear(null)}
        />
      )}

      {deletingYear && (
        <ConfirmDialog
          title="Delete Academic Year"
          message={`Delete ${deletingYear.name}? This only succeeds if the year holds no records - otherwise you'll be told to archive it instead.`}
          confirmLabel="Delete"
          confirmVariant="danger"
          onConfirm={() => doDelete(deletingYear)}
          onClose={() => setDeletingYear(null)}
        />
      )}
    </div>
  );
};

export default AcademicYearSection;
