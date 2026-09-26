// src/pages/principal/Attendance.tsx
import React, { useState, useEffect } from 'react';
import { ClipboardCheck, History, Edit3, Trash2, CheckCircle } from 'lucide-react';
import { EmptyState, LoadingSkeleton, StatusBadge } from '../../components/shared';
import { attendanceService } from '../../services/attendance';
import { sectionsService } from '../../services/sections';
import { AttendanceRecord, Section } from '../../types';
import { timetableService } from '../../services/timetable';
import { WeekdayTabs } from '../../components/shared/WeekdayTabs';
import { ConfirmDialog } from '../../components/EditModal';

export const Attendance: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'today' | 'history'>('today');
  const [attendanceList, setAttendanceList] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState('Monday');
  const [timetable, setTimetable] = useState<any[]>([]);

  // History / Corrections state
  const [sections, setSections] = useState<Section[]>([]);
  const [historySectionId, setHistorySectionId] = useState<number | ''>('');
  const [historyDate, setHistoryDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [historyStudentId, setHistoryStudentId] = useState<string>('');
  const [historyRecords, setHistoryRecords] = useState<AttendanceRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editStatus, setEditStatus] = useState<string>('PRESENT');
  const [editRemarks, setEditRemarks] = useState<string>('');
  const [savingEdit, setSavingEdit] = useState<boolean>(false);
  const [voidTargetId, setVoidTargetId] = useState<number | null>(null);

  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    Promise.all([
      attendanceService.getAttendance({ attendance_date: today }),
      timetableService.listTimetables(),
      sectionsService.listSections().catch(() => []),
    ])
      .then(([records, schedule, secList]) => {
        setAttendanceList(records);
        setTimetable(schedule.items || []);
        setSections(secList);
        if (secList.length > 0) {
          setHistorySectionId(secList[0].id);
        }
      })
      .catch(() => setError('Failed to load attendance records'))
      .finally(() => setLoading(false));
  }, []);

  const daySlots = timetable.filter(slot => String(slot.day_of_week).toLowerCase() === selectedDay.toLowerCase());

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
    setEditRemarks((record as any).remarks || '');
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
        prev.map(r => (r.id === id ? { ...r, status: updated.status, remarks: (updated as any).remarks } : r))
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
    setAttendanceList(prev =>
      prev.map(r => (r.id === voidTargetId ? { ...r, status: updated.status || 'VOID' } : r))
    );
    setVoidTargetId(null);
  };

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
          <WeekdayTabs selectedDay={selectedDay} onChange={setSelectedDay} />
          <p className="text-xs text-slate-500">{daySlots.length} scheduled session{daySlots.length === 1 ? '' : 's'} on {selectedDay}; attendance records remain date-based.</p>

          {loading ? (
            <LoadingSkeleton type="list" count={5} />
          ) : attendanceList.length === 0 ? (
            <EmptyState
              title="No Attendance Records"
              description="No attendance records have been marked for today."
              icon={<ClipboardCheck className="w-10 h-10 text-slate-300" />}
            />
          ) : (
            <div className="space-y-2.5">
              {attendanceList.map((record) => (
                <div
                  key={record.id}
                  className={`flex items-center gap-3 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs ${
                    record.status === 'VOID' ? 'opacity-50 bg-slate-50' : ''
                  }`}
                >
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-bold text-emerald-700">
                      {record.student_id}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">Student #{record.student_id}</p>
                    <p className="text-xs text-slate-500">Section #{record.section_id} · {record.date}</p>
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
      ) : (
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3 shadow-xs">
            <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <History className="w-4 h-4 text-indigo-600" /> Filter History
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
                  className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700 disabled:opacity-50"
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
                      <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center flex-shrink-0">
                        <span className="text-sm font-bold text-indigo-700">{record.student_id}</span>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-900">Student #{record.student_id}</p>
                        <p className="text-xs text-slate-500">
                          Section #{record.section_id} · Date: {record.date}
                          {(record as any).remarks ? ` · Remarks: ${(record as any).remarks}` : ''}
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
                                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium px-2.5 py-1.5 rounded-lg border border-indigo-200 hover:bg-indigo-50 flex items-center gap-1"
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
