// src/pages/teacher/SlipTestList.tsx
// Page 2 of 2: the slip tests for one class + subject, plus the schedule /
// edit form and the cancel confirmation.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Plus, X, Check } from 'lucide-react';
import { slipTestsService } from '../../services/slipTests';
import {
  SlipTest,
  SLIP_TEST_MAX_DESCRIPTION,
  SLIP_TEST_MAX_DURATION,
  SLIP_TEST_MAX_MARKS,
  isSlipTestPast,
  todaySlipTestDate,
} from '../../types/slipTest';
import { SlipTestRow } from '../../components/slipTests';
import { ConfirmDialog, EmptyState, ErrorState, LoadingSkeleton } from '../../components/shared';
import { errorMessage } from '../../helpers/errorMessage';

type FormErrors = Partial<
  Record<'title' | 'scheduled_date' | 'max_marks' | 'duration_minutes' | 'description', string>
>;

type Tab = 'upcoming' | 'past';

const EMPTY_FORM = {
  title: '',
  scheduled_date: '',
  start_time: '',
  duration_minutes: '',
  max_marks: '',
  description: '',
};

/**
 * Split the list by date. String comparison on `YYYY-MM-DD` is exact and, unlike
 * `new Date(iso)`, cannot shift a day across a timezone boundary.
 */
function splitByWhen(items: SlipTest[]): { upcoming: SlipTest[]; past: SlipTest[] } {
  const today = todaySlipTestDate();
  const upcoming: SlipTest[] = [];
  const past: SlipTest[] = [];
  items.forEach((item) => {
    if (item.scheduled_date.slice(0, 10) < today) past.push(item);
    else upcoming.push(item);
  });
  return { upcoming, past };
}

export const TeacherSlipTestListPage: React.FC = () => {
  const params = useParams();
  const navigate = useNavigate();

  const gradeId = Number(params.gradeId);
  const sectionId = Number(params.sectionId);
  const subjectId = Number(params.subjectId);
  const routeIdsAreValid =
    Number.isInteger(gradeId) && Number.isInteger(sectionId) && Number.isInteger(subjectId);

  const [items, setItems] = useState<SlipTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('upcoming');

  // Form / dialog state
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const [cancelId, setCancelId] = useState<number | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const fetchList = useCallback(async () => {
    if (!routeIdsAreValid) return;
    setLoading(true);
    setError(null);
    try {
      const data = await slipTestsService.listMine({
        class: sectionId,
        subject: subjectId,
      });
      setItems(data.items || []);
    } catch (err) {
      console.error('Failed to load slip tests', err);
      setError(errorMessage(err, 'Unable to load slip tests. Please try again.'));
    } finally {
      setLoading(false);
    }
  }, [routeIdsAreValid, sectionId, subjectId]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const { upcoming, past } = useMemo(() => splitByWhen(items), [items]);
  const visible = tab === 'upcoming' ? upcoming : past;

  // -------------------------------------------------------------------------
  // Form
  // -------------------------------------------------------------------------

  const openCreateForm = () => {
    setEditingId(null);
    setForm({ ...EMPTY_FORM, scheduled_date: todaySlipTestDate(), max_marks: '20' });
    setFormErrors({});
    setFormError(null);
    setFormOpen(true);
  };

  const openEditForm = (slipTest: SlipTest) => {
    setEditingId(slipTest.id);
    setForm({
      title: slipTest.title,
      scheduled_date: slipTest.scheduled_date.slice(0, 10),
      start_time: slipTest.start_time ? String(slipTest.start_time).slice(0, 5) : '',
      duration_minutes: slipTest.duration_minutes != null ? String(slipTest.duration_minutes) : '',
      max_marks: String(slipTest.max_marks),
      description: slipTest.description ?? '',
    });
    setFormErrors({});
    setFormError(null);
    setFormOpen(true);
  };

  /** Inline validation, mirroring the backend bounds exactly. */
  const validate = (): boolean => {
    const errors: FormErrors = {};
    const title = form.title.trim();
    if (!title) errors.title = 'Enter a title for this slip test.';
    else if (title.length > 150) errors.title = 'Title must be 150 characters or fewer.';

    const date = form.scheduled_date;
    if (!date) errors.scheduled_date = 'Choose the date the test is held.';
    else if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) errors.scheduled_date = 'Enter a valid date.';
    else if (isSlipTestPast(date)) errors.scheduled_date = 'The date cannot be in the past.';

    const marks = form.max_marks.trim();
    if (!marks) errors.max_marks = 'Enter the maximum marks.';
    else if (!/^\d+$/.test(marks)) errors.max_marks = 'Marks must be a whole number.';
    else if (Number(marks) < 1) errors.max_marks = 'Marks must be greater than 0.';
    else if (Number(marks) > SLIP_TEST_MAX_MARKS)
      errors.max_marks = `Marks must be ${SLIP_TEST_MAX_MARKS} or fewer.`;

    const duration = form.duration_minutes.trim();
    if (duration) {
      if (!/^\d+$/.test(duration)) errors.duration_minutes = 'Duration must be a whole number.';
      else if (Number(duration) < 1) errors.duration_minutes = 'Duration must be at least 1 minute.';
      else if (Number(duration) > SLIP_TEST_MAX_DURATION)
        errors.duration_minutes = `Duration must be ${SLIP_TEST_MAX_DURATION} minutes or fewer.`;
    }

    if (form.description.length > SLIP_TEST_MAX_DESCRIPTION)
      errors.description = `Topics must be ${SLIP_TEST_MAX_DESCRIPTION} characters or fewer.`;

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!validate()) return;

    setSaving(true);
    try {
      const base = {
        title: form.title.trim(),
        scheduled_date: form.scheduled_date,
        start_time: form.start_time ? form.start_time : null,
        duration_minutes: form.duration_minutes ? Number(form.duration_minutes) : null,
        max_marks: Number(form.max_marks.trim()),
      };

      if (editingId !== null) {
        await slipTestsService.update(editingId, {
          ...base,
          description: form.description.trim() ? form.description.trim() : null,
        });
        setToast('Slip test updated.');
      } else {
        const created = await slipTestsService.create({
          ...base,
          description: form.description.trim() ? form.description.trim() : null,
          grade_id: gradeId,
          section_id: sectionId,
          subject_id: subjectId,
        });
        setToast(created.duplicate_warning ? 'Slip test scheduled (with a warning).' : 'Slip test scheduled.');
      }

      setFormOpen(false);
      setEditingId(null);
      await fetchList();
    } catch (err) {
      console.error('Failed to save slip test', err);
      setFormError(errorMessage(err, 'Could not save the slip test. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  const handleCancelConfirm = async () => {
    if (cancelId === null) return;
    setCancelling(true);
    try {
      await slipTestsService.cancel(cancelId);
      setCancelId(null);
      setToast('Slip test cancelled.');
      await fetchList();
    } catch (err) {
      console.error('Failed to cancel slip test', err);
      setToast(errorMessage(err, 'Could not cancel the slip test.'));
    } finally {
      setCancelling(false);
    }
  };

  // Success toast auto-dismisses.
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(timer);
  }, [toast]);

  if (!routeIdsAreValid) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/teacher/slip-tests')}
          className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Slip Tests
        </button>
        <ErrorState title="Unknown class" message="That class link is not valid." />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <button
          onClick={() => navigate('/teacher/slip-tests')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 min-h-[44px] flex-shrink-0"
        >
          <ArrowLeft className="w-4 h-4" />
          All classes
        </button>
        <button
          onClick={openCreateForm}
          className="h-10 px-4 rounded-xl bg-[var(--brand)] hover:bg-[var(--brand-hover)] active:scale-95
                     text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
          Schedule slip test
        </button>
      </div>

      {/* Success toast */}
      {toast && (
        <div
          role="status"
          className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs font-semibold"
        >
          <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span className="flex-1">{toast}</span>
          <button onClick={() => setToast(null)} className="p-1 -m-1 text-emerald-600" aria-label="Dismiss">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setTab('upcoming')}
          className={`flex-1 sm:flex-none min-h-[40px] px-4 rounded-xl text-xs font-bold transition-all ${
            tab === 'upcoming'
              ? 'bg-[var(--brand)] text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Upcoming ({upcoming.length})
        </button>
        <button
          onClick={() => setTab('past')}
          className={`flex-1 sm:flex-none min-h-[40px] px-4 rounded-xl text-xs font-bold transition-all ${
            tab === 'past'
              ? 'bg-[var(--brand)] text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Past ({past.length})
        </button>
      </div>

      {/* List */}
      {loading ? (
        <LoadingSkeleton type="list" count={3} />
      ) : error ? (
        <ErrorState title="Could not load slip tests" message={error} onRetry={fetchList} />
      ) : visible.length === 0 ? (
        <EmptyState
          title={tab === 'upcoming' ? 'Nothing scheduled' : 'No past slip tests'}
          description={
            tab === 'upcoming'
              ? 'Schedule the first slip test for this class and subject.'
              : 'Slip tests move here automatically once their date has passed.'
          }
          action={
            tab === 'upcoming'
              ? { label: 'Schedule slip test', onClick: openCreateForm }
              : undefined
          }
        />
      ) : (
        <div className="space-y-2.5">
          {visible.map((slipTest) => (
            <SlipTestRow
              key={slipTest.id}
              slipTest={slipTest}
              onEdit={() => openEditForm(slipTest)}
              onCancel={() => setCancelId(slipTest.id)}
              cancelling={cancelling && cancelId === slipTest.id}
            />
          ))}
        </div>
      )}

      {/* Schedule / edit sheet. Full-width bottom sheet on mobile so it fits a
          360px screen without a horizontal scrollbar. */}
      {formOpen && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs" onClick={() => !saving && setFormOpen(false)} />
          <div className="relative z-50 w-full sm:max-w-lg bg-white rounded-t-3xl sm:rounded-2xl shadow-xl max-h-[92vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-slate-100 px-5 py-4 flex items-center justify-between gap-2">
              <h2 className="text-base font-bold text-slate-900">
                {editingId !== null ? 'Edit slip test' : 'Schedule slip test'}
              </h2>
              <button
                onClick={() => !saving && setFormOpen(false)}
                disabled={saving}
                className="p-2 -m-1 text-slate-400 hover:text-slate-700 rounded-lg disabled:opacity-50"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-5 space-y-4" noValidate>
              {formError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">
                  {formError}
                </div>
              )}

              <div>
                <label htmlFor="slip-title" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Title <span className="text-rose-500">*</span>
                </label>
                <input
                  id="slip-title"
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g. Unit 3 Quiz"
                  maxLength={150}
                  aria-invalid={!!formErrors.title}
                  className={`w-full h-11 px-4 rounded-xl border bg-white text-slate-900 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none ${
                    formErrors.title ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {formErrors.title && <p className="mt-1 text-[11px] text-rose-600">{formErrors.title}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="slip-date" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Date <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="slip-date"
                    type="date"
                    value={form.scheduled_date}
                    onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })}
                    min={todaySlipTestDate()}
                    aria-invalid={!!formErrors.scheduled_date}
                    className={`w-full h-11 px-4 rounded-xl border bg-white text-slate-900 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none ${
                      formErrors.scheduled_date ? 'border-rose-400' : 'border-slate-300'
                    }`}
                  />
                  {formErrors.scheduled_date && (
                    <p className="mt-1 text-[11px] text-rose-600">{formErrors.scheduled_date}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="slip-marks" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Max marks <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="slip-marks"
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={SLIP_TEST_MAX_MARKS}
                    value={form.max_marks}
                    onChange={(e) => setForm({ ...form, max_marks: e.target.value })}
                    aria-invalid={!!formErrors.max_marks}
                    className={`w-full h-11 px-4 rounded-xl border bg-white text-slate-900 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none ${
                      formErrors.max_marks ? 'border-rose-400' : 'border-slate-300'
                    }`}
                  />
                  {formErrors.max_marks && <p className="mt-1 text-[11px] text-rose-600">{formErrors.max_marks}</p>}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="slip-time" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Start time <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    id="slip-time"
                    type="time"
                    value={form.start_time}
                    onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                    className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
                  />
                </div>

                <div>
                  <label htmlFor="slip-duration" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Duration <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    id="slip-duration"
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={SLIP_TEST_MAX_DURATION}
                    value={form.duration_minutes}
                    onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })}
                    placeholder="minutes"
                    aria-invalid={!!formErrors.duration_minutes}
                    className={`w-full h-11 px-4 rounded-xl border bg-white text-slate-900 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none ${
                      formErrors.duration_minutes ? 'border-rose-400' : 'border-slate-300'
                    }`}
                  />
                  {formErrors.duration_minutes && (
                    <p className="mt-1 text-[11px] text-rose-600">{formErrors.duration_minutes}</p>
                  )}
                </div>
              </div>

              <div>
                <div className="flex items-baseline justify-between mb-1.5">
                  <label htmlFor="slip-desc" className="block text-xs font-semibold text-slate-700">
                    Syllabus / topics <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <span className={`text-[10px] tabular-nums ${form.description.length > SLIP_TEST_MAX_DESCRIPTION ? 'text-rose-600' : 'text-slate-400'}`}>
                    {form.description.length}/{SLIP_TEST_MAX_DESCRIPTION}
                  </span>
                </div>
                <textarea
                  id="slip-desc"
                  rows={3}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Chapters covered, revision notes..."
                  aria-invalid={!!formErrors.description}
                  className={`w-full p-4 rounded-xl border bg-white text-slate-900 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none ${
                    formErrors.description ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {formErrors.description && (
                  <p className="mt-1 text-[11px] text-rose-600">{formErrors.description}</p>
                )}
              </div>

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => !saving && setFormOpen(false)}
                  disabled={saving}
                  className="flex-1 h-11 px-4 rounded-xl border border-slate-300 text-slate-700 text-xs font-bold hover:bg-slate-50 transition-all disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 h-11 px-4 rounded-xl bg-[var(--brand)] hover:bg-[var(--brand-hover)] text-white text-xs font-bold shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Saving...' : editingId !== null ? 'Save changes' : 'Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={cancelId !== null}
        title="Cancel this slip test?"
        message={
          cancelId !== null
            ? `"${items.find((i) => i.id === cancelId)?.title ?? 'This slip test'}" will be marked as cancelled. Students are notified and can still see it marked as cancelled - it is never deleted.`
            : ''
        }
        confirmLabel="Cancel slip test"
        isDanger
        isLoading={cancelling}
        onConfirm={handleCancelConfirm}
        onCancel={() => !cancelling && setCancelId(null)}
      />
    </div>
  );
};

export default TeacherSlipTestListPage;