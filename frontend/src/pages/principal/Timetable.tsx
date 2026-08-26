// src/pages/principal/Timetable.tsx
import React, { useEffect, useState } from 'react';
import {
  CalendarDays,
  Plus,
  Trash2,
  Edit2,
  Clock,
  User,
  BookOpen,
  GraduationCap,
  X,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { LoadingSkeleton, EmptyState, ConfirmDialog } from '../../components/shared';
import { timetableService } from '../../services/timetable';
import { gradesService } from '../../services/grades';
import { subjectsService } from '../../services/subjects';
import { teachersService } from '../../services/teachers';
import { TimetableSlot, Grade, Subject, Teacher } from '../../types';

interface TimetableFormData {
  id?: number;
  subject_id: number | '';
  teacher_id: number | '';
  start_time: string;
  end_time: string;
  day_of_week?: string;
}

// Convert "09:00:00" or "09:00" or "09:00 AM" to "09:00 AM" format
const formatDisplayTime = (timeStr?: string): string => {
  if (!timeStr) return '';
  if (timeStr.includes('AM') || timeStr.includes('PM')) {
    return timeStr;
  }
  const parts = timeStr.split(':');
  if (parts.length >= 2) {
    let hours = parseInt(parts[0], 10);
    const minutes = parts[1].padStart(2, '0');
    if (isNaN(hours)) return timeStr;
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    const formattedHours = hours < 10 ? `0${hours}` : `${hours}`;
    return `${formattedHours}:${minutes} ${ampm}`;
  }
  return timeStr;
};

// Convert "09:00 AM" or "09:00:00" to "HH:mm" for <input type="time" />
const toInputTime = (timeStr?: string): string => {
  if (!timeStr) return '';
  if (timeStr.includes('AM') || timeStr.includes('PM')) {
    const isPM = timeStr.toUpperCase().includes('PM');
    const isAM = timeStr.toUpperCase().includes('AM');
    const clean = timeStr.replace(/AM|PM/gi, '').trim();
    const parts = clean.split(':');
    let hours = parseInt(parts[0], 10) || 0;
    const minutes = parts[1] || '00';
    if (isPM && hours < 12) hours += 12;
    if (isAM && hours === 12) hours = 0;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  }
  const parts = timeStr.split(':');
  if (parts.length >= 2) {
    return `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}`;
  }
  return timeStr;
};

export const PrincipalTimetablePage: React.FC = () => {
  // State for classes/grades
  const [classes, setClasses] = useState<Grade[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null);

  // State for subjects & teachers catalog
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);

  // State for timetable entries for selected class
  const [entries, setEntries] = useState<TimetableSlot[]>([]);
  const [loadingClasses, setLoadingClasses] = useState(true);
  const [loadingEntries, setLoadingEntries] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Modal State for Add / Edit
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [formData, setFormData] = useState<TimetableFormData>({
    subject_id: '',
    teacher_id: '',
    start_time: '09:00',
    end_time: '10:00',
    day_of_week: 'Monday',
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Delete State
  const [entryToDelete, setEntryToDelete] = useState<TimetableSlot | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // 1. Fetch all classes, subjects, and teachers on load
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoadingClasses(true);
        setError(null);

        const [fetchedGrades, fetchedSubjects, fetchedTeachers] = await Promise.all([
          gradesService.listGrades(),
          subjectsService.listSubjects().catch(() => []),
          teachersService.listTeachers().catch(() => []),
        ]);

        setClasses(fetchedGrades || []);
        setSubjects(fetchedSubjects || []);
        setTeachers(fetchedTeachers || []);

        if (fetchedGrades && fetchedGrades.length > 0) {
          setSelectedClassId(fetchedGrades[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load initial timetable data:', err);
        setError('Failed to load classes. Please try again.');
      } finally {
        setLoadingClasses(false);
      }
    };

    fetchInitialData();
  }, []);

  // 2. Fetch timetable entries whenever selectedClassId changes (Strict Class Isolation)
  useEffect(() => {
    if (!selectedClassId) {
      setEntries([]);
      return;
    }

    const fetchClassEntries = async () => {
      try {
        setLoadingEntries(true);
        setError(null);
        const res = await timetableService.listTimetables({ grade_id: selectedClassId });
        setEntries(res.items || []);
      } catch (err: any) {
        console.error('Failed to load timetable entries:', err);
        setError('Failed to load timetable entries for this class.');
      } finally {
        setLoadingEntries(false);
      }
    };

    fetchClassEntries();
  }, [selectedClassId]);

  // Selected Class details
  const selectedClass = classes.find(c => c.id === selectedClassId);

  // Clear toast notifications after 3 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Open Create Modal
  const handleOpenCreateModal = () => {
    setModalMode('create');
    setFormData({
      subject_id: subjects.length > 0 ? subjects[0].id : '',
      teacher_id: teachers.length > 0 ? teachers[0].id : '',
      start_time: '09:00',
      end_time: '10:00',
      day_of_week: 'Monday',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  // Open Edit Modal
  const handleOpenEditModal = (entry: TimetableSlot) => {
    setModalMode('edit');
    setFormData({
      id: entry.id,
      subject_id: entry.subject_id ?? '',
      teacher_id: entry.teacher_id ?? '',
      start_time: toInputTime(entry.start_time) || '09:00',
      end_time: toInputTime(entry.end_time) || '10:00',
      day_of_week: (entry.day_of_week as string) || 'Monday',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  // Form Submission (Create or Update)
  const handleSaveEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!selectedClassId) {
      setFormError('Please select a class first.');
      return;
    }

    if (!formData.subject_id) {
      setFormError('Subject is required.');
      return;
    }

    if (!formData.teacher_id) {
      setFormError('Teacher is required.');
      return;
    }

    if (!formData.start_time) {
      setFormError('Start time is required.');
      return;
    }

    if (!formData.end_time) {
      setFormError('End time is required.');
      return;
    }

    // Validate end_time > start_time
    const [startH, startM] = formData.start_time.split(':').map(Number);
    const [endH, endM] = formData.end_time.split(':').map(Number);
    const startMinutes = startH * 60 + startM;
    const endMinutes = endH * 60 + endM;

    if (endMinutes <= startMinutes) {
      setFormError('End time must be later than start time.');
      return;
    }

    try {
      setIsSubmitting(true);

      const formattedStart = formatDisplayTime(formData.start_time);
      const formattedEnd = formatDisplayTime(formData.end_time);

      if (modalMode === 'create') {
        const payload = {
          grade_id: selectedClassId,
          subject_id: Number(formData.subject_id),
          teacher_id: Number(formData.teacher_id),
          start_time: formattedStart,
          end_time: formattedEnd,
          day_of_week: formData.day_of_week || 'Monday',
        };

        const created = await timetableService.createTimetable(payload);
        setEntries(prev => [...prev, created]);
        setSuccessMessage('Timetable entry added successfully.');
      } else if (modalMode === 'edit' && formData.id) {
        const payload = {
          grade_id: selectedClassId,
          subject_id: Number(formData.subject_id),
          teacher_id: Number(formData.teacher_id),
          start_time: formattedStart,
          end_time: formattedEnd,
          day_of_week: formData.day_of_week || 'Monday',
        };

        const updated = await timetableService.updateTimetable(formData.id, payload);
        setEntries(prev => prev.map(item => (item.id === formData.id ? updated : item)));
        setSuccessMessage('Timetable entry updated successfully.');
      }

      setIsModalOpen(false);
    } catch (err: any) {
      console.error('Failed to save timetable entry:', err);
      setFormError(err.response?.data?.detail || 'Failed to save timetable entry. Please check the inputs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Timetable Entry
  const handleConfirmDelete = async () => {
    if (!entryToDelete) return;
    try {
      setIsDeleting(true);
      await timetableService.deleteTimetable(entryToDelete.id);
      setEntries(prev => prev.filter(e => e.id !== entryToDelete.id));
      setSuccessMessage('Timetable entry deleted successfully.');
    } catch (err: any) {
      console.error('Failed to delete timetable entry:', err);
      setError('Failed to delete timetable entry.');
    } finally {
      setIsDeleting(false);
      setEntryToDelete(null);
    }
  };

  // Helper to find teacher's full name
  const getTeacherFullName = (teacherId?: number, fallbackName?: string): string => {
    if (fallbackName && fallbackName !== 'Unassigned' && !fallbackName.startsWith('Teacher #')) {
      return fallbackName;
    }
    const found = teachers.find(t => t.id === teacherId);
    if (found) {
      return found.full_name || found.display_name || `Teacher #${found.id}`;
    }
    return fallbackName || (teacherId ? `Teacher #${teacherId}` : 'Unassigned');
  };

  // Helper to find subject name
  const getSubjectName = (subjectId?: number, fallbackName?: string): string => {
    if (fallbackName && !fallbackName.startsWith('Subject #')) {
      return fallbackName;
    }
    const found = subjects.find(s => s.id === subjectId);
    if (found) {
      return found.name;
    }
    return fallbackName || (subjectId ? `Subject #${subjectId}` : 'Subject');
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Principal → Timetable</h1>
          <p className="text-xs text-slate-500">Manage regular class schedules and teacher assignments</p>
        </div>
        {selectedClassId && (
          <button
            onClick={handleOpenCreateModal}
            className="h-10 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-1.5 self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>+ Add Subject / Timetable</span>
          </button>
        )}
      </div>

      {/* Toast Notifications */}
      {successMessage && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center gap-2 animate-in fade-in duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ─── 1. ALL EXISTING CLASSES LIST ────────────────────────────────────────── */}
      <div className="space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Select Class
        </h2>

        {loadingClasses ? (
          <div className="flex gap-2 overflow-x-auto pb-1">
            <LoadingSkeleton type="card" count={4} />
          </div>
        ) : classes.length === 0 ? (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs">
            No classes/grades found. Please configure classes in the Grade Management section first.
          </div>
        ) : (
          <div className="flex gap-2 overflow-x-auto pb-1.5 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-none">
            {classes.map(c => {
              const isSelected = selectedClassId === c.id;
              return (
                <button
                  key={c.id}
                  onClick={() => setSelectedClassId(c.id)}
                  className={`h-10 px-5 rounded-xl text-xs font-bold whitespace-nowrap transition-all flex items-center gap-2 flex-shrink-0 cursor-pointer ${
                    isSelected
                      ? 'bg-emerald-600 text-white shadow-sm ring-2 ring-emerald-600/20'
                      : 'bg-white border border-slate-200 text-slate-700 hover:border-emerald-300 hover:bg-slate-50'
                  }`}
                >
                  <GraduationCap className={`w-3.5 h-3.5 ${isSelected ? 'text-white' : 'text-slate-400'}`} />
                  <span>{c.name || `Class ${c.id}`}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ─── 2. CLASS TIMETABLE VIEW ────────────────────────────────────────────── */}
      {selectedClassId && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-slate-900">
                {selectedClass?.name || `Class ${selectedClassId}`} Timetable
              </h2>
              <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {entries.length} {entries.length === 1 ? 'subject' : 'subjects'}
              </span>
            </div>
          </div>

          {loadingEntries ? (
            <div className="space-y-3">
              <LoadingSkeleton type="card" count={3} />
            </div>
          ) : entries.length === 0 ? (
            /* ─── 3. EMPTY STATE ─────────────────────────────────────────────────── */
            <div className="bg-white rounded-2xl border border-slate-200/80 p-8 text-center shadow-2xs space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
                <CalendarDays className="w-6 h-6" />
              </div>
              <div className="space-y-1 max-w-sm mx-auto">
                <h3 className="text-sm font-bold text-slate-900">No Timetable Entries</h3>
                <p className="text-xs text-slate-500">
                  No subjects or timetable entries have been added for this class yet.
                </p>
              </div>
              <button
                onClick={handleOpenCreateModal}
                className="inline-flex items-center gap-1.5 h-10 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold text-xs shadow-xs transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>+ Add Subject / Timetable</span>
              </button>
            </div>
          ) : (
            /* ─── 4. ENTRIES LIST ───────────────────────────────────────────────── */
            <div className="space-y-3">
              {entries.map(entry => {
                const subjectName = getSubjectName(entry.subject_id, entry.subject_name);
                const teacherFullName = getTeacherFullName(entry.teacher_id, entry.teacher_name);
                const startTimeFormatted = formatDisplayTime(entry.start_time);
                const endTimeFormatted = formatDisplayTime(entry.end_time);

                return (
                  <div
                    key={entry.id}
                    className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs hover:border-emerald-200 transition-all space-y-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      {/* Subject info */}
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0 mt-0.5">
                          <BookOpen className="w-5 h-5" />
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-slate-900 leading-tight">
                            {subjectName}
                          </h3>
                          <div className="flex items-center gap-1.5 text-xs text-slate-600 mt-1">
                            <User className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                            <span>
                              Teacher: <strong className="text-slate-800 font-semibold">{teacherFullName}</strong>
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Timing badge */}
                      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-800 text-xs font-bold flex-shrink-0">
                        <Clock className="w-3.5 h-3.5 text-emerald-600" />
                        <span>
                          {startTimeFormatted} – {endTimeFormatted}
                        </span>
                      </div>
                    </div>

                    {/* Card Actions (Edit & Delete) */}
                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 text-xs">
                      <button
                        onClick={() => handleOpenEditModal(entry)}
                        className="h-8 px-3 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold flex items-center gap-1.5 active:scale-95 transition-all cursor-pointer"
                      >
                        <Edit2 className="w-3 h-3" />
                        <span>Edit</span>
                      </button>
                      <button
                        onClick={() => setEntryToDelete(entry)}
                        className="h-8 px-3 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 font-semibold flex items-center gap-1.5 active:scale-95 transition-all cursor-pointer"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ─── 5. ADD / EDIT TIMETABLE ENTRY MODAL ───────────────────────────────────── */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity"
            onClick={() => !isSubmitting && setIsModalOpen(false)}
          />

          {/* Modal Card */}
          <div className="relative z-50 w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  {modalMode === 'create' ? 'Add Timetable Entry' : 'Edit Timetable Entry'}
                </h3>
                <p className="text-xs text-slate-500">
                  {selectedClass?.name || `Class ${selectedClassId}`}
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                disabled={isSubmitting}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSaveEntry} className="space-y-4">
              {/* Field 1: Subject */}
              <div className="space-y-1.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                  Subject <span className="text-rose-500">*</span>
                </label>
                {subjects.length > 0 ? (
                  <select
                    value={formData.subject_id}
                    onChange={e => setFormData(prev => ({ ...prev, subject_id: Number(e.target.value) }))}
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    required
                  >
                    <option value="" disabled>Select Subject</option>
                    {subjects.map(s => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    value={formData.subject_id}
                    onChange={e => setFormData(prev => ({ ...prev, subject_id: Number(e.target.value) }))}
                    placeholder="Subject ID (e.g. 1)"
                    className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    required
                  />
                )}
              </div>

              {/* Field 2: Teacher */}
              <div className="space-y-1.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                  Teacher (Full Name) <span className="text-rose-500">*</span>
                </label>
                {teachers.length > 0 ? (
                  <select
                    value={formData.teacher_id}
                    onChange={e => setFormData(prev => ({ ...prev, teacher_id: Number(e.target.value) }))}
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    required
                  >
                    <option value="" disabled>Select Teacher</option>
                    {teachers.map(t => {
                      const fullName = t.full_name || t.display_name || `Teacher #${t.id}`;
                      return (
                        <option key={t.id} value={t.id}>
                          {fullName} {t.employee_id ? `(${t.employee_id})` : ''}
                        </option>
                      );
                    })}
                  </select>
                ) : (
                  <input
                    type="number"
                    value={formData.teacher_id}
                    onChange={e => setFormData(prev => ({ ...prev, teacher_id: Number(e.target.value) }))}
                    placeholder="Teacher ID (e.g. 1)"
                    className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    required
                  />
                )}
              </div>

              {/* Field 3 & 4: Start Time & End Time */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                    Start Time <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="time"
                    value={formData.start_time}
                    onChange={e => setFormData(prev => ({ ...prev, start_time: e.target.value }))}
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                    End Time <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="time"
                    value={formData.end_time}
                    onChange={e => setFormData(prev => ({ ...prev, end_time: e.target.value }))}
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    required
                  />
                </div>
              </div>

              {/* Modal Buttons */}
              <div className="flex items-center gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  disabled={isSubmitting}
                  className="flex-1 py-2.5 px-4 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-2.5 px-4 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-xs active:scale-98 transition-all cursor-pointer"
                >
                  {isSubmitting ? 'Saving...' : modalMode === 'create' ? 'Add Entry' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── 6. CONFIRM DELETE DIALOG ────────────────────────────────────────────── */}
      <ConfirmDialog
        isOpen={!!entryToDelete}
        title="Delete Timetable Entry?"
        message={`Are you sure you want to delete the timetable entry for ${getSubjectName(
          entryToDelete?.subject_id,
          entryToDelete?.subject_name
        )}? This action cannot be undone.`}
        confirmLabel="Delete Entry"
        cancelLabel="Cancel"
        isDanger={true}
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setEntryToDelete(null)}
      />
    </div>
  );
};

export const Timetable = PrincipalTimetablePage;
export const PrincipalTimetable = PrincipalTimetablePage;
export default PrincipalTimetablePage;

