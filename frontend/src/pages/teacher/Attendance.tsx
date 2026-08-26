import React, { useState, useEffect } from 'react';
import { ClipboardCheck, Save, Calendar, UserCheck } from 'lucide-react';
import { EmptyState, LoadingSkeleton } from '../../components/shared';
import { teachersService } from '../../services/teachers';
import { studentsService } from '../../services/students';
import { attendanceService } from '../../services/attendance';
import { Teacher } from '../../types';

export const TeacherAttendance: React.FC = () => {
  const [teacherProfile, setTeacherProfile] = useState<Teacher | null>(null);
  const [classSection, setClassSection] = useState<any | null>(null);
  const [students, setStudents] = useState<any[]>([]);
  const [attendanceMap, setAttendanceMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [saving, setSaving] = useState<boolean>(false);
  const [saved, setSaved] = useState<boolean>(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    teachersService
      .getMyTeacherProfile()
      .then(profile => {
        setTeacherProfile(profile);
        const section = profile.class_teacher_section;
        setClassSection(section || null);

        if (section) {
          return Promise.all([
            studentsService.listStudents({ section_id: section.id }),
            attendanceService.getAttendance({ section_id: section.id, attendance_date: selectedDate }),
          ]);
        }
        return [null, null];
      })
      .then(([stList, attRecords]: any) => {
        if (stList) {
          setStudents(stList);
          const map: Record<number, string> = {};
          stList.forEach((s: any) => {
            map[s.id] = 'PRESENT';
          });
          if (Array.isArray(attRecords)) {
            attRecords.forEach((r: any) => {
              if (r.student_id && r.status) {
                map[r.student_id] = r.status.toUpperCase();
              }
            });
          }
          setAttendanceMap(map);
        }
      })
      .catch(err => {
        console.error(err);
        setError('Failed to load class teacher attendance records.');
      })
      .finally(() => setLoading(false));
  }, [selectedDate]);

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
        status: (attendanceMap[st.id] || 'PRESENT') as any,
      }));

      await attendanceService.markBulkAttendance(records);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      console.error(err);
      setError('Failed to save attendance. Please try again.');
    } finally {
      setSaving(false);
    }
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
          <h1 className="text-xl font-bold text-slate-900">Mark Attendance</h1>
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
      <div>
        <h1 className="text-xl font-bold text-slate-900">Mark Attendance</h1>
        <p className="text-xs text-slate-500">
          Assigned Class: <span className="font-semibold text-slate-700">{classSection.grade_name || `Grade ${classSection.grade_id}`} - Section {classSection.name || classSection.section_name}</span>
        </p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}
      {saved && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-xs font-medium">
          ✓ Attendance saved successfully for {selectedDate}!
        </div>
      )}

      {/* Date Picker */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs">
        <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5 text-blue-600" /> Select Attendance Date
        </label>
        <input
          type="date"
          className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
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
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-bold text-blue-700">
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
                  </div>
                </div>
              );
            })}
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full h-12 rounded-2xl bg-blue-600 hover:bg-blue-700 active:scale-[0.98] text-white font-bold text-sm shadow-sm transition-all disabled:opacity-60 flex items-center justify-center gap-2"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving Attendance...' : 'Save Attendance'}
          </button>
        </form>
      )}
    </div>
  );
};

export default TeacherAttendance;