// src/pages/principal/Attendance.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { ClipboardCheck, History, Edit3, Trash2, CheckCircle, GraduationCap, Users, CalendarDays } from 'lucide-react';
import { EmptyState, LoadingSkeleton, StatusBadge } from '../../components/shared';
import { attendanceService } from '../../services/attendance';
import { sectionsService } from '../../services/sections';
import { gradesService } from '../../services/grades';
import { AttendanceRecord, Grade, Section } from '../../types';
import { timetableService } from '../../services/timetable';
import { WeekdayTabs } from '../../components/shared/WeekdayTabs';
import { ConfirmDialog } from '../../components/EditModal';
import { useCurrentWeekday } from '../../hooks/useClock';
import { getDateForWeekday, getLocalDateString, isToday, sortByStartTime } from '../../utils/date';

const STATUS_COUNT_ORDER = ['PRESENT', 'ABSENT', 'LATE', 'LEAVE'] as const;

export const Attendance: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'today' | 'history'>('today');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Class picker (grade + section) for the Today view - no default class.
  const [grades, setGrades] = useState<Grade[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [gradeId, setGradeId] = useState<number | ''>('');
  const [sectionId, setSectionId] = useState<number | ''>('');

  // Open on the real current day (and follow a day rollover) until the user picks a tab.
  const todayWeekday = useCurrentWeekday();
  const [pickedDay, setPickedDay] = useState<string | null>(null);
  const selectedDay = pickedDay ?? todayWeekday;

  // Today-view data (only fetched once a class is chosen).
  const [timetable, setTimetable] = useState<any[]>([]);
  const [dayRecords, setDayRecords] = useState<AttendanceRecord[]>([]);
  const [dayLoading, setDayLoading] = useState<boolean>(false);

  // History / Corrections state
  const [historySectionId, setHistorySectionId] = useState<number | ''>('');
  const [historyDate, setHistoryDate] = useState<string>(getLocalDateString());
  const [historyStudentId, setHistoryStudentId] = useState<string>('');
  const [historyRecords, setHistoryRecords] = useState<AttendanceRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editStatus, setEditStatus] = useState<string>('PRESENT');
  const [editRemarks, setEditRemarks] = useState<string>('');
  const [savingEdit, setSavingEdit] = useState<boolean>(false);
  const [voidTargetId, setVoidTargetId] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([
      gradesService.listGrades().catch(() => [] as Grade[]),
      sectionsService.listSections().catch(() => [] as Section[]),
    ])
      .then(([gradeList, sectionList]) => {
        setGrades(gradeList);
        setSections(sectionList);
      })
      .catch(() => setError('Failed to load classes'))
      .finally(() => setLoading(false));
  }, []);

  const gradeSections = useMemo(
    () => (gradeId ? sections.filter(s => s.grade_id === Number(gradeId)) : []),
    [sections, gradeId]
  );

  const classSelected = gradeId !== '' && sectionId !== '';

  // The weekday tab maps to a concrete date inside the current week (Monday-first).
  const selectedDate = getDateForWeekday(selectedDay);
  const selectedDateString = getLocalDateString(selectedDate);
  const selectedIsToday = isToday(selectedDate);

  // Load this class's timetable once (it does not depend on the day) and that
  // day's attendance records whenever the class or weekday changes.
  useEffect(() => {
    if (!classSelected) {
      setTimetable([]);
      return;
    }
    let cancelled = false;
    timetableService
      .listTimetables({ grade_id: Number(gradeId), section_id: Number(sectionId), limit: 200 })
      .then(schedule => { if (!cancelled) setTimetable(schedule.items || []); })
      .catch(() => { if (!cancelled) setError('Failed to load the class timetable.'); });
    return () => { cancelled = true; };
  }, [classSelected, gradeId, sectionId]);

  useEffect(() => {
    if (!classSelected) {
      setDayRecords([]);
      return;
    }
    let cancelled = false;
    setDayLoading(true);
    attendanceService
      .getAttendance({ section_id: Number(sectionId), attendance_date: selectedDateString })
      .then(records => { if (!cancelled) setDayRecords(records || []); })
      .catch(() => { if (!cancelled) setError('Failed to load attendance for this class.'); })
      .finally(() => { if (!cancelled) setDayLoading(false); });
    return () => { cancelled = true; };
  }, [classSelected, sectionId, selectedDateString]);

  const daySlots = useMemo(
    () => timetable.filter(slot => String(slot.day_of_week).toLowerCase() === selectedDay.toLowerCase()),
    [timetable, selectedDay]
  );

  // Attendance is recorded per section/date (no subject link), so every session
  // of the section shares the same taken/not-taken state.
  const liveRecords = useMemo(() => dayRecords.filter(r => r.status !== 'VOID'), [dayRecords]);
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    liveRecords.forEach(r => { counts[r.status] = (counts[r.status] || 0) + 1; });
    return counts;
  }, [liveRecords]);

  const voidedCount = dayRecords.length - liveRecords.length;
  // A day where every record was voided counts as "not taken" - the voided rows
  // are still listed underneath so nothing disappears from the audit trail.
  const attendanceTaken = liveRecords.length > 0;
  const notTakenLabel = selectedIsToday
    ? 'Not taken today'
    : selectedDate.getTime() > new Date().setHours(0, 0, 0, 0)
      ? 'Not yet due'
      : `Not taken on ${selectedDateString}`;

  const handleGradeChange = (value: string) => {
    setGradeId(value ? Number(value) : '');
    setSectionId('');
    setTimetable([]);
    setDayRecords([]);
    setError(null);
  };

  const handleSectionChange = (value: string) => {
    setSectionId(value ? Number(value) : '');
    setTimetable([]);
    setDayRecords([]);
    setError(null);
  };

  const fetchHistory = async () => {
    setHistoryLoading(true);
    setError(null);
    try {
      if (historyStudentId.trim()) {
        const records = await attendanceService.getStudentAttendance(Number(historyStudentId.trim()));
        setHistoryRecords(records);
      } else {
        const params: any = {};
        if (historySectionId) params.section_id = Number(historySectionId);
        if (historyDate) params.attendance_date = historyDate;
        const records = await attendanceService.getAttendance(params);
        setHistoryRecords(records);
      }
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
      setDayRecords(prev =>
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
    setDayRecords(prev =>
      prev.map(r => (r.id === voidTargetId ? { ...r, status: updated.status || 'VOID' } : r))
    );
    setVoidTargetId(null);
  };

  const selectedGrade = grades.find(g => g.id === Number(gradeId));
  const selectedSection = gradeSections.find(s => s.id === Number(sectionId));
  const classLabel = [selectedGrade?.name, selectedSection?.name].filter(Boolean).join(' - ');

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Attendance Management</h1>
          <p className="text-xs text-slate-500">View daily status, history, corrections, and void records</p>
        </div>
        <div className="flex gap-2 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('today')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'today' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Today's Overview
          </button>
          <button
            onClick={() => {
              setActiveTab('history');
              if (historyRecords.length === 0) fetchHistory();
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

      {activeTab === 'today' ? (
        <>
          {/* Class selector scoped to the Today view */}
          <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs space-y-3">
            <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-emerald-600" /> Select Class
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-600 flex items-center gap-1">
                  <GraduationCap className="w-3.5 h-3.5" /> Grade
                </label>
                <select
                  value={gradeId}
                  onChange={e => handleGradeChange(e.target.value)}
                  disabled={loading}
                  className="w-full mt-1 rounded-lg border border-slate-200 p-2 text-xs bg-white"
                >
                  <option value="">Select grade</option>
                  {grades.map(g => (
                    <option key={g.id} value={g.id}>{g.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600 flex items-center gap-1">
                  <Users className="w-3.5 h-3.5" /> Section
                </label>
                <select
                  value={sectionId}
                  onChange={e => handleSectionChange(e.target.value)}
                  disabled={gradeId === '' || gradeSections.length === 0}
                  className="w-full mt-1 rounded-lg border border-slate-200 p-2 text-xs bg-white"
                >
                  <option value="">
                    {gradeId === '' ? 'Select a grade first' : gradeSections.length === 0 ? 'No sections for this grade' : 'Select section'}
                  </option>
                  {gradeSections.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <WeekdayTabs selectedDay={selectedDay} onChange={setPickedDay} id="principal-attendance" />

          {!classSelected ? (
            <EmptyState
              title="Select a Class"
              description="Choose a grade and section to see whether attendance was taken, session by session."
              icon={<ClipboardCheck className="w-10 h-10 text-slate-300" />}
            />
          ) : dayLoading ? (
            <LoadingSkeleton type="list" count={4} />
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-slate-500">
                  {classLabel} · {selectedDateString}
                  {daySlots.length > 0 ? ` · ${daySlots.length} scheduled session${daySlots.length === 1 ? '' : 's'}` : ' · no scheduled sessions'}
                </p>
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold ${
                    attendanceTaken
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : selectedIsToday
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-slate-100 text-slate-600 border border-slate-200'
                  }`}
                >
                  <CalendarDays className="w-3.5 h-3.5" />
                  {attendanceTaken ? 'Attendance Taken' : notTakenLabel}
                </span>
              </div>

              {attendanceTaken && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {STATUS_COUNT_ORDER.map(status => (
                    <div key={status} className="bg-white border border-slate-200/80 rounded-xl px-3 py-2 shadow-xs">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{status}</p>
                      <p className="text-lg font-extrabold text-slate-900">{statusCounts[status] || 0}</p>
                    </div>
                  ))}
                </div>
              )}

              {!attendanceTaken && (
                <EmptyState
                  title={notTakenLabel}
                  description={
                    selectedIsToday
                      ? `No attendance record exists for ${classLabel} on ${selectedDateString}.`
                      : selectedDate.getTime() > new Date().setHours(0, 0, 0, 0)
                        ? `${selectedDateString} is in the future - attendance cannot be marked yet.`
                        : `No attendance record was marked for ${classLabel} on ${selectedDateString}.`
                  }
                  icon={<ClipboardCheck className="w-10 h-10 text-slate-300" />}
                />
              )}

              {/* Scheduled sessions for this class/day share one taken/not-taken state */}
              {daySlots.length > 0 && (
                <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs space-y-2">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Scheduled Sessions</h3>
                  <div className="divide-y divide-slate-100">
                    {sortByStartTime(daySlots).map((slot, index) => (
                      <div key={slot.id ?? index} className="flex items-center justify-between gap-3 py-2.5">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-slate-900 truncate">{slot.subject_name || 'Session'}</p>
                          <p className="text-xs text-slate-500">
                            {slot.start_time} - {slot.end_time}
                            {slot.teacher_name ? ` · ${slot.teacher_name}` : ''}
                          </p>
                        </div>
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide flex-shrink-0 ${
                            attendanceTaken
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : selectedIsToday
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : 'bg-slate-100 text-slate-500 border border-slate-200'
                          }`}
                        >
                          {attendanceTaken ? 'Attendance Taken' : notTakenLabel}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Student-level records for the day (voided rows stay visible) */}
              {dayRecords.length > 0 && (
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Student Records ({dayRecords.length})
                    </h3>
                    {voidedCount > 0 && (
                      <span className="text-[11px] font-semibold text-slate-500">{voidedCount} voided</span>
                    )}
                  </div>
                  {dayRecords.map((record) => (
                    <div
                      key={record.id}
                      className={`flex items-center gap-3 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs ${
                        record.status === 'VOID' ? 'opacity-50 bg-slate-50' : ''
                      }`}
                    >
                      <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
                        <span className="text-sm font-bold text-emerald-700">{record.student_id}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-slate-900 truncate">Student #{record.student_id}</p>
                        <p className="text-xs text-slate-500">
                          {classLabel} · {record.date}
                          {record.remarks ? ` · ${record.remarks}` : ''}
                        </p>
                      </div>
                      <StatusBadge status={record.status} />
                      {record.status !== 'VOID' && (
                        <button
                          onClick={() => setVoidTargetId(record.id)}
                          className="text-xs text-rose-600 hover:text-rose-800 font-medium px-2 py-1 rounded hover:bg-rose-50 border border-rose-200"
                        >
                          Void
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      ) : (
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3 shadow-xs">
            <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <History className="w-4 h-4 text-emerald-600" /> Filter History
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-600">Section</label>
                <select
                  value={historySectionId}
                  onChange={e => setHistorySectionId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full mt-1 rounded-lg border border-slate-200 p-2 text-xs"
                >
                  <option value="">All Sections</option>
                  {sections.map(s => (
                    <option key={s.id} value={s.id}>
                      {s.name} (Grade {s.grade_id})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600">Date</label>
                <input
                  type="date"
                  value={historyDate}
                  onChange={e => setHistoryDate(e.target.value)}
                  className="w-full mt-1 rounded-lg border border-slate-200 p-2 text-xs"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600">Student ID (Optional)</label>
                <input
                  type="number"
                  placeholder="e.g. 101"
                  value={historyStudentId}
                  onChange={e => setHistoryStudentId(e.target.value)}
                  className="w-full mt-1 rounded-lg border border-slate-200 p-2 text-xs"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={fetchHistory}
                  disabled={historyLoading}
                  className="w-full px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs font-bold hover:bg-emerald-700 disabled:opacity-50"
                >
                  {historyLoading ? 'Loading…' : 'Filter Records'}
                </button>
              </div>
            </div>
          </div>

          {historyLoading ? (
            <LoadingSkeleton type="list" count={5} />
          ) : historyRecords.length === 0 ? (
            <EmptyState
              title="No Attendance Records"
              description="No attendance records match the specified filters."
              icon={<History className="w-10 h-10 text-slate-300" />}
            />
          ) : (
            <div className="space-y-2.5">
              {historyRecords.map((record) => {
                const isEditing = editingId === record.id;
                const isVoid = record.status === 'VOID';
                return (
                  <div
                    key={record.id}
                    className={`flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs ${
                      isVoid ? 'opacity-50 bg-slate-50' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
                        <span className="text-sm font-bold text-emerald-700">{record.student_id}</span>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-900">Student #{record.student_id}</p>
                        <p className="text-xs text-slate-500">
                          Section #{record.section_id} · Date: {record.date}
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
                                className="text-xs text-emerald-700 hover:text-emerald-800 font-medium px-2.5 py-1.5 rounded-lg border border-emerald-200 hover:bg-emerald-50 flex items-center gap-1"
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

export default Attendance;
