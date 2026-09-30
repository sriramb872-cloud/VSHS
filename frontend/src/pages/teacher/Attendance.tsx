import React, { useState, useEffect } from 'react';
import { ClipboardCheck, Save, Calendar, History, Edit3, Trash2, CheckCircle } from 'lucide-react';
import { EmptyState, LoadingSkeleton, StatusBadge } from '../../components/shared';
import { teachersService } from '../../services/teachers';
import { studentsService } from '../../services/students';
import { attendanceService } from '../../services/attendance';
import { Teacher, Student, AttendanceRecord, AttendanceStatus } from '../../types';
import { timetableService } from '../../services/timetable';
import errorMessage from '../../helpers/errorMessage';
import { WeekdayTabs } from '../../components/shared/WeekdayTabs';
import { useCurrentWeekday } from '../../hooks/useClock';
import { getLocalDateString } from '../../utils/date';
import { ConfirmDialog } from '../../components/EditModal';

export const TeacherAttendance: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'mark' | 'history'>('mark');
  const [teacherProfile, setTeacherProfile] = useState<Teacher | null>(null);
  const [classSection, setClassSection] = useState<any | null>(null);
  const [students, setStudents] = useState<any[]>([]);
  const [attendanceMap, setAttendanceMap] = useState<Record<number, string>>({});
  /** Per-student remarks entered while marking, sent with the create payload. */
  const [remarksMap, setRemarksMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  // Local calendar date (never UTC - `toISOString()` can be a day behind/ahead).
  const [selectedDate, setSelectedDate] = useState<string>(getLocalDateString());
  const [saving, setSaving] = useState<boolean>(false);
  const [saved, setSaved] = useState<boolean>(false);
  // Open on the real current day (and follow a day rollover) until the user picks a tab.
  const todayWeekday = useCurrentWeekday();
  const [pickedDay, setPickedDay] = useState<string | null>(null);
  const selectedDay = pickedDay ?? todayWeekday;
  const [timetable, setTimetable] = useState<any[]>([]);

  // History & Correction state
  const [historyDate, setHistoryDate] = useState<string>(getLocalDateString());
  const [historyRecords, setHistoryRecords] = useState<AttendanceRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editStatus, setEditStatus] = useState<string>('PRESENT');
  const [editRemarks, setEditRemarks] = useState<string>('');
  const [savingEdit, setSavingEdit] = useState<boolean>(false);
  const [voidTargetId, setVoidTargetId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    // Fetch the class-teacher section first, then the roster/attendance/timetable
    // for it. Written as a single async function so the tuple stays a concrete
    // type instead of a union with the "no section" fallback branch.
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const profile = await teachersService.getMyTeacherProfile();
        if (cancelled) return;
        setTeacherProfile(profile);

        const section = profile.class_teacher_section;
        setClassSection(section || null);

        if (!section) {
          // No class-teacher assignment: nothing to mark, and the schedule is
          // cleared (matches the previous no-section behaviour).
          setTimetable([]);
          return;
        }

        const [roster, attRecords, schedule] = await Promise.all([
          studentsService.listStudents({ section_id: section.id }),
          attendanceService.getAttendance({
            section_id: section.id,
            attendance_date: selectedDate,
          }),
          timetableService.listTimetables(),
        ]);
        if (cancelled) return;

        setTimetable(schedule?.items || []);
        setStudents(roster);
        const map: Record<number, string> = {};
        const remarks: Record<number, string> = {};
        roster.forEach((s: Student) => {
          map[s.id] = 'PRESENT';
        });
        if (Array.isArray(attRecords)) {
          attRecords.forEach((r: AttendanceRecord) => {
            if (r.student_id && r.status) {
              map[r.student_id] = r.status.toUpperCase();
            }
            // Seed the remarks inputs from what is already stored, so
            // re-marking a day does not silently wipe saved remarks.
            if (r.student_id && r.remarks) {
              remarks[r.student_id] = r.remarks;
            }
          });
        }
        setAttendanceMap(map);
        setRemarksMap(remarks);
        setHistoryRecords(Array.isArray(attRecords) ? attRecords : []);
      } catch (err) {
        console.error(err);
        setError('Failed to load class teacher attendance records.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [selectedDate]);

  const daySlots = timetable
    .filter(slot => String(slot.day_of_week).toLowerCase() === selectedDay.toLowerCase())
    .sort((a, b) => String(a.start_time).localeCompare(String(b.start_time)));

  const handleStatusChange = (studentId: number, status: string) => {
    setAttendanceMap(prev => ({
      ...prev,
      [studentId]: status,
    }));
  };

  const handleSaveAttendance = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!classSection) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const records = students.map(st => ({
        student_id: st.id,
        section_id: classSection.id,
        date: selectedDate,
        status: (attendanceMap[st.id] || 'PRESENT') as AttendanceStatus,
        // Remarks are part of the create payload. They used to be impossible
        // to set here even though the column exists and the correction dialog
        // could set them afterwards.
        remarks: remarksMap[st.id]?.trim() || null,
      }));

      const saved = await attendanceService.markBulkAttendance(records);
      // Adopt the server's view (ids + persisted remarks) so the list and the
      // correction dialog agree with the database.
      setHistoryRecords(saved);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: unknown) {
      console.error(err);
      setError(errorMessage(err, 'Failed to save attendance. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  const fetchHistory = async () => {
    if (!classSection) return;
    setHistoryLoading(true);
    setError(null);
    try {
      const records = await attendanceService.getAttendance({
        section_id: classSection.id,
        attendance_date: historyDate,
      });
      setHistoryRecords(records);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to fetch attendance history.');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleStartEdit = (record: AttendanceRecord) => {
    setEditingId(record.id);
    setEditStatus(record.status);
    setEditRemarks(record.remarks || '');
  };

  const handleSaveEdit = async (id: number) => {
    setSavingEdit(true);
    setError(null);
    try {
      const updated = await attendanceService.updateAttendance(id, {
        status: editStatus,
        remarks: editRemarks,
      });
      setHistoryRecords(prev =>
        prev.map(r => (r.id === id ? { ...r, status: updated.status, remarks: updated.remarks } : r))
      );
      setEditingId(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update attendance.');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleVoidRecord = async () => {
    if (!voidTargetId) return;
    const updated = await attendanceService.voidAttendance(voidTargetId);
    setHistoryRecords(prev =>
      prev.map(r => (r.id === voidTargetId ? { ...r, status: updated.status || 'VOID' } : r))
    );
    setVoidTargetId(null);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <LoadingSkeleton type="card" count={2} />
        <LoadingSkeleton type="list" count={5} />
      </div>
    );
  }

  if (!classSection) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Attendance</h1>
          <p className="text-xs text-slate-500">Record daily student attendance</p>
        </div>
        <EmptyState
          title="Not Assigned as Class Teacher"
          description="You are currently not assigned as a Class Teacher for any section. Attendance entry is restricted to assigned Class Teachers."
          icon={<ClipboardCheck className="w-10 h-10 text-slate-300" />}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Attendance</h1>
          <p className="text-xs text-slate-500">
            Assigned Class: <span className="font-semibold text-slate-700">{classSection.grade_name || `Grade ${classSection.grade_id}`} - Section {classSection.name || classSection.section_name}</span>
          </p>
        </div>
        <div className="flex gap-2 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('mark')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'mark' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Mark Daily
          </button>
          <button
            onClick={() => {
              setActiveTab('history');
              fetchHistory();
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'history' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            History & Corrections
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {activeTab === 'mark' ? (
        <>
          <WeekdayTabs selectedDay={selectedDay} onChange={setPickedDay} />
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-4 space-y-2">
            <p className="text-xs font-semibold text-slate-700">{selectedDay} attendance sessions</p>
            {daySlots.length === 0 ? (
              <p className="text-xs text-slate-500">No timetable period is scheduled for this day.</p>
            ) : daySlots.map(slot => (
              <div key={slot.id} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-xs">
                <span className="font-semibold text-slate-800">{slot.subject_name || `Subject #${slot.subject_id}`} · {slot.grade_name} - {slot.section_name}</span>
                <span className="text-slate-500">{slot.start_time} – {slot.end_time}</span>
              </div>
            ))}
          </div>
          {saved && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-xs font-medium">
              ✓ Attendance saved successfully for {selectedDate}!
            </div>
          )}

          {/* Date Picker */}
          <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs">
            <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-[var(--brand)]" /> Select Attendance Date
            </label>
            <input
              type="date"
              className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
              value={selectedDate}
              onChange={e => setSelectedDate(e.target.value)}
            />
          </div>

          {/* Student Attendance List */}
          {students.length === 0 ? (
            <EmptyState
              title="No Students Found"
              description="No students are enrolled in your assigned section."
              icon={<ClipboardCheck className="w-10 h-10 text-slate-300" />}
            />
          ) : (
            <form onSubmit={handleSaveAttendance} className="space-y-3">
              <div className="space-y-2.5">
                {students.map(st => {
                  const currentStatus = attendanceMap[st.id] || 'PRESENT';
                  return (
                    <div
                      key={st.id}
                      className="flex items-center gap-3 bg-white border border-slate-200/80 rounded-2xl p-3.5 shadow-xs"
                    >
                      <div className="w-10 h-10 rounded-xl bg-[var(--brand-light)] flex items-center justify-center flex-shrink-0">
                        <span className="text-sm font-bold text-[var(--brand-strong)]">
                          {(st.display_name || st.full_name || '?').charAt(0)}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-slate-900 truncate">
                          {st.display_name || st.full_name || `Student #${st.id}`}
                        </p>
                        {st.roll_number && (
                          <p className="text-xs text-slate-400">Roll No: {st.roll_number}</p>
                        )}
                        <input
                          type="text"
                          value={remarksMap[st.id] ?? ''}
                          onChange={(e) =>
                            setRemarksMap((prev) => ({ ...prev, [st.id]: e.target.value }))
                          }
                          placeholder="Remarks (optional)"
                          maxLength={255}
                          aria-label={`Remarks for ${st.display_name || st.full_name || st.id}`}
                          className="mt-1.5 w-full h-8 px-2 rounded-lg border border-slate-200 text-xs text-slate-800 placeholder:text-slate-400 focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
                        />
                      </div>
                      <div className="flex gap-1.5 flex-shrink-0">
                        <button
                          type="button"
                          onClick={() => handleStatusChange(st.id, 'PRESENT')}
                          className={`h-8 px-3 rounded-lg text-xs font-bold transition-all ${
                            currentStatus === 'PRESENT'
                              ? 'bg-emerald-600 text-white shadow-sm'
                              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                          }`}
                        >
                          Present
                        </button>
                        <button
                          type="button"
                          onClick={() => handleStatusChange(st.id, 'ABSENT')}
                          className={`h-8 px-3 rounded-lg text-xs font-bold transition-all ${
                            currentStatus === 'ABSENT'
                              ? 'bg-rose-600 text-white shadow-sm'
                              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                          }`}
                        >
                          Absent
                        </button>
                        <button
                          type="button"
                          onClick={() => handleStatusChange(st.id, 'LATE')}
                          className={`h-8 px-3 rounded-lg text-xs font-bold transition-all ${
                            currentStatus === 'LATE'
                              ? 'bg-amber-600 text-white shadow-sm'
                              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                          }`}
                        >
                          Late
                        </button>
                        <button
                          type="button"
                          onClick={() => handleStatusChange(st.id, 'LEAVE')}
                          className={`h-8 px-3 rounded-lg text-xs font-bold transition-all ${
                            currentStatus === 'LEAVE'
                              ? 'bg-[var(--brand)] text-white shadow-sm'
                              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                          }`}
                        >
                          Leave
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              <button
                type="submit"
                disabled={saving}
                className="w-full h-12 rounded-2xl bg-[var(--brand)] hover:bg-[var(--brand-hover)] active:scale-[0.98] text-white font-bold text-sm shadow-sm transition-all disabled:opacity-60 flex items-center justify-center gap-2"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving Attendance...' : 'Save Attendance'}
              </button>
            </form>
          )}
        </>
      ) : (
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col md:flex-row gap-3 items-end shadow-xs">
            <div className="flex-1">
              <label className="text-xs font-semibold text-slate-600">Select Date for History</label>
              <input
                type="date"
                value={historyDate}
                onChange={e => setHistoryDate(e.target.value)}
                className="w-full mt-1 rounded-lg border border-slate-200 p-2 text-xs"
              />
            </div>
            <button
              onClick={fetchHistory}
              disabled={historyLoading}
              className="px-4 py-2 bg-[var(--brand)] text-white rounded-lg text-xs font-bold hover:bg-[var(--brand-hover)] disabled:opacity-50"
            >
              {historyLoading ? 'Loading…' : 'Load History'}
            </button>
          </div>

          {historyLoading ? (
            <LoadingSkeleton type="list" count={5} />
          ) : historyRecords.length === 0 ? (
            <EmptyState
              title="No Attendance Records"
              description="No attendance records found for this section on the chosen date."
              icon={<History className="w-10 h-10 text-slate-300" />}
            />
          ) : (
            <div className="space-y-2.5">
              {historyRecords.map((record) => {
                const isEditing = editingId === record.id;
                const isVoid = record.status === 'VOID';
                // `GET /attendance` returns only student_id, but the roster for
                // this section is already loaded, so resolve the name locally
                // instead of showing a bare id.
                const rosterStudent = students.find(
                  (s: Student) => s.id === record.student_id
                ) as Student | undefined;
                const studentName =
                  rosterStudent?.display_name ||
                  rosterStudent?.full_name ||
                  `Student #${record.student_id}`;
                return (
                  <div
                    key={record.id}
                    className={`flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs ${
                      isVoid ? 'opacity-50 bg-slate-50' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-[var(--brand-light)] flex items-center justify-center flex-shrink-0">
                        <span className="text-sm font-bold text-[var(--brand-strong)]">
                          {studentName.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{studentName}</p>
                        <p className="text-xs text-slate-500">
                          Date: {record.date}
                          {record.remarks ? ` · Remarks: ${record.remarks}` : ''}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {isEditing ? (
                        <div className="flex items-center gap-2">
                          <select
                            value={editStatus}
                            onChange={e => setEditStatus(e.target.value)}
                            className="rounded-lg border border-slate-200 p-1.5 text-xs font-medium"
                          >
                            <option value="PRESENT">PRESENT</option>
                            <option value="ABSENT">ABSENT</option>
                            <option value="LATE">LATE</option>
                            <option value="LEAVE">LEAVE</option>
                          </select>
                          <input
                            type="text"
                            placeholder="Remarks"
                            value={editRemarks}
                            onChange={e => setEditRemarks(e.target.value)}
                            className="rounded-lg border border-slate-200 p-1.5 text-xs w-36"
                          />
                          <button
                            onClick={() => handleSaveEdit(record.id)}
                            disabled={savingEdit}
                            className="text-xs px-2.5 py-1.5 bg-emerald-600 text-white rounded-lg font-bold hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-1"
                          >
                            <CheckCircle className="w-3.5 h-3.5" /> Save
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="text-xs px-2.5 py-1.5 border border-slate-200 rounded-lg hover:bg-slate-50"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <StatusBadge status={record.status} />
                          {!isVoid && (
                            <>
                              <button
                                onClick={() => handleStartEdit(record)}
                                className="text-xs text-[var(--brand)] hover:text-[var(--brand-strong)] font-medium px-2.5 py-1.5 rounded-lg border border-[var(--brand-border)] hover:bg-[var(--brand-light)] flex items-center gap-1"
                              >
                                <Edit3 className="w-3.5 h-3.5" /> Edit
                              </button>
                              <button
                                onClick={() => setVoidTargetId(record.id)}
                                className="text-xs text-rose-600 hover:text-rose-800 font-medium px-2.5 py-1.5 rounded-lg border border-rose-200 hover:bg-rose-50 flex items-center gap-1"
                              >
                                <Trash2 className="w-3.5 h-3.5" /> Void
                              </button>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {voidTargetId && (
        <ConfirmDialog
          title="Void Attendance Record"
          message="Are you sure you want to void this attendance record? This will mark the record as VOID and retain it in the audit history."
          confirmLabel="Void Record"
          confirmVariant="danger"
          onConfirm={handleVoidRecord}
          onClose={() => setVoidTargetId(null)}
        />
      )}
    </div>
  );
};

export default TeacherAttendance;
