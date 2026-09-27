// src/pages/teacher/AttendanceHistory.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { History, CheckCircle, RefreshCw } from 'lucide-react';
import { attendanceService } from '../../services/attendance';
import { teachersService } from '../../services/teachers';
import { studentsService } from '../../services/students';
import { errorMessage } from '../../helpers/errorMessage';
import { EmptyState, LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';
import { AttendanceRecord, Student } from '../../types';

interface HistoryRow extends AttendanceRecord {
  student_name?: string;
}

export const TeacherAttendanceHistory: React.FC = () => {
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [loadFailed, setLoadFailed] = useState<boolean>(false);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editStatus, setEditStatus] = useState<string>('PRESENT');
  const [editRemarks, setEditRemarks] = useState<string>('');
  const [savingEdit, setSavingEdit] = useState<boolean>(false);

  const [voidTargetId, setVoidTargetId] = useState<number | null>(null);
  const [voiding, setVoiding] = useState<boolean>(false);

  /**
   * Load every attendance record for the sections this teacher is assigned to,
   * together with the student roster so the list shows real names instead of
   * bare ids. Previously this page made no API call at all and always rendered
   * the "No History Found" empty state, so a teacher could never see or correct
   * what they had already submitted.
   */
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setLoadFailed(false);
    try {
      const profile: any = await teachersService.getMyTeacherProfile();
      const section = profile?.class_teacher_section;
      if (!section) {
        setHistory([]);
        return;
      }
      const [records, students] = await Promise.all([
        attendanceService.getAttendance({ section_id: section.id, limit: 200 }),
        studentsService.listStudents({ section_id: section.id }),
      ]);
      const nameById = new Map<number, string>(
        (students as Student[]).map(s => [
          s.id,
          s.full_name || s.display_name || `Student #${s.id}`,
        ])
      );
      setHistory(
        (records as AttendanceRecord[]).map(r => ({
          ...r,
          student_name: nameById.get(r.student_id),
        }))
      );
    } catch (err) {
      setLoadFailed(true);
      setError(errorMessage(err, 'Failed to load attendance history.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleStartEdit = (record: HistoryRow) => {
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
      setHistory(prev =>
        prev.map(r => (r.id === id ? { ...r, status: updated.status, remarks: updated.remarks } : r))
      );
      setEditingId(null);
    } catch (err) {
      setError(errorMessage(err, 'Failed to update attendance.'));
    } finally {
      setSavingEdit(false);
    }
  };

  const handleVoidRecord = async () => {
    if (voidTargetId === null) return;
    setVoiding(true);
    setError(null);
    try {
      const updated = await attendanceService.voidAttendance(voidTargetId);
      setHistory(prev =>
        prev.map(r => (r.id === voidTargetId ? { ...r, status: updated.status || 'VOID' } : r))
      );
      setVoidTargetId(null);
    } catch (err) {
      setError(errorMessage(err, 'Failed to void attendance record.'));
    } finally {
      setVoiding(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Attendance History</h1>
          <p className="text-xs text-slate-500">Past attendance records you've submitted</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="h-9 px-3 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && !loadFailed && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loadFailed ? (
        <ErrorState title="Load Error" message={error || 'Failed to load attendance history.'} onRetry={load} />
      ) : loading ? (
        <LoadingSkeleton type="list" count={5} />
      ) : history.length === 0 ? (
        <EmptyState
          title="No History Found"
          description="No past attendance records have been submitted yet."
          icon={<History className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {history.map((record) => {
            const isEditing = editingId === record.id;
            const isVoid = record.status === 'VOID';
            return (
              <div
                key={record.id}
                className={`flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs ${
                  isVoid ? 'opacity-60 bg-slate-50' : ''
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-bold text-blue-700">
                      {record.student_name?.charAt(0) ?? record.student_id}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {record.student_name || `Student #${record.student_id}`}
                    </p>
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
                        aria-label="Correction status"
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
                            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium px-2.5 py-1.5 rounded-lg border border-indigo-200 hover:bg-indigo-50"
                          >
                            Correct
                          </button>
                          <button
                            onClick={() => setVoidTargetId(record.id)}
                            className="text-xs text-rose-600 hover:text-rose-800 font-medium px-2.5 py-1.5 rounded-lg border border-rose-200 hover:bg-rose-50"
                          >
                            Void
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

      {voidTargetId !== null && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <h2 className="text-base font-bold text-slate-900">Void Attendance Record?</h2>
            <p className="text-sm text-slate-600">
              The record stays in the ledger for audit purposes but is marked VOID and excluded from
              attendance statistics.
            </p>
            {error && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setVoidTargetId(null)}
                className="h-10 px-4 rounded-xl border border-slate-200 text-slate-700 text-xs font-bold"
              >
                Cancel
              </button>
              <button
                onClick={handleVoidRecord}
                disabled={voiding}
                className="h-10 px-4 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold disabled:opacity-50"
              >
                {voiding ? 'Voiding...' : 'Confirm Void'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherAttendanceHistory;
