// src/pages/principal/AttendanceReports.tsx
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BarChart2, Users, UserX, Clock, CalendarDays, Download, RefreshCw, Ban } from 'lucide-react';
import { EmptyState, LoadingSkeleton, ErrorState } from '../../components/shared';
import { attendanceService } from '../../services/attendance';
import { gradesService } from '../../services/grades';
import { sectionsService } from '../../services/sections';
import { Grade, Section } from '../../types';
import {
  AttendanceReport,
  AttendanceReportSectionRow,
  AttendanceReportStudentRow,
} from '../../types/attendance-report';
import errorMessage from '../../helpers/errorMessage';

const isoDay = (d: Date) => d.toISOString().slice(0, 10);

function defaultWindow() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return { start: isoDay(start), end: isoDay(end) };
}

const STATUS_TILES = [
  { key: 'PRESENT', label: 'Present', icon: Users, tone: 'text-emerald-600', chip: 'bg-emerald-50 text-emerald-700' },
  { key: 'ABSENT', label: 'Absent', icon: UserX, tone: 'text-rose-600', chip: 'bg-rose-50 text-rose-700' },
  { key: 'LATE', label: 'Late', icon: Clock, tone: 'text-amber-600', chip: 'bg-amber-50 text-amber-700' },
  { key: 'LEAVE', label: 'Leave', icon: CalendarDays, tone: 'text-sky-600', chip: 'bg-sky-50 text-sky-700' },
  { key: 'VOID', label: 'Void', icon: Ban, tone: 'text-slate-500', chip: 'bg-slate-100 text-slate-600' },
] as const;

const csvCell = (value: unknown): string => {
  const s = value === null || value === undefined ? '' : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export const AttendanceReports: React.FC = () => {
  const initial = useMemo(defaultWindow, []);
  const [startDate, setStartDate] = useState(initial.start);
  const [endDate, setEndDate] = useState(initial.end);
  const [gradeId, setGradeId] = useState<string>('');
  const [sectionId, setSectionId] = useState<string>('');

  const [grades, setGrades] = useState<Grade[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [report, setReport] = useState<AttendanceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'sections' | 'students' | 'daily'>('sections');

  useEffect(() => {
    let cancelled = false;
    gradesService
      .listGrades({ limit: 200 })
      .then((g) => { if (!cancelled) setGrades(g); })
      .catch(() => { /* filters are optional; the report still works unfiltered */ });
    return () => { cancelled = true; };
  }, [gradeId]);

  useEffect(() => {
    let cancelled = false;
    sectionsService
      .listSections({ grade_id: gradeId ? Number(gradeId) : undefined, limit: 200 })
      .then((s) => { if (!cancelled) setSections(s); })
      .catch(() => { if (!cancelled) setSections([]); });
    return () => { cancelled = true; };
  }, [gradeId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await attendanceService.getAttendanceReport({
        start_date: startDate,
        end_date: endDate,
        grade_id: gradeId ? Number(gradeId) : undefined,
        section_id: sectionId ? Number(sectionId) : undefined,
      });
      setReport(data);
    } catch (err) {
      setError(errorMessage(err, 'Failed to load the attendance report.'));
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, gradeId, sectionId]);

  useEffect(() => {
    load();
  }, [load]);

  // Changing the grade invalidates the chosen section (a section belongs to one grade).
  const onGradeChange = (value: string) => {
    setGradeId(value);
    setSectionId('');
  };

  const exportCsv = () => {
    if (!report) return;
    const header = [
      'Section', 'Grade', 'Enrolled', 'Students with records',
      'Present', 'Absent', 'Late', 'Leave', 'Void', 'Marked', 'Attendance rate %',
    ];
    const sectionRows = report.sections.map((s: AttendanceReportSectionRow) => [
      s.section_name ?? '', s.grade_name ?? '', s.enrolled_students, s.students_with_records,
      s.PRESENT, s.ABSENT, s.LATE, s.LEAVE, s.VOID, s.marked, s.attendance_rate,
    ]);
    const studentHeader = [
      'Student', 'Admission no', 'Roll', 'Section', 'Grade',
      'Present', 'Absent', 'Late', 'Leave', 'Void', 'Marked', 'Attendance rate %',
    ];
    const studentRows = report.students.map((s: AttendanceReportStudentRow) => [
      s.student_name ?? '', s.admission_number ?? '', s.roll_number ?? '',
      s.section_name ?? '', s.grade_name ?? '',
      s.PRESENT, s.ABSENT, s.LATE, s.LEAVE, s.VOID, s.marked, s.attendance_rate,
    ]);
    const dailyHeader = ['Date', 'Present', 'Absent', 'Late', 'Leave', 'Void', 'Marked', 'Attendance rate %'];
    const dailyRows = report.daily.map((d) => [
      d.date, d.PRESENT, d.ABSENT, d.LATE, d.LEAVE, d.VOID, d.marked, d.attendance_rate,
    ]);

    const all = [
      [`Attendance report ${report.filters.start_date} to ${report.filters.end_date}`],
      [],
      ['Totals', 'Present', 'Absent', 'Late', 'Leave', 'Void', 'Marked', 'Students', 'Attendance rate %'],
      [
        '', report.totals.PRESENT, report.totals.ABSENT, report.totals.LATE,
        report.totals.LEAVE, report.totals.VOID, report.totals.marked,
        report.totals.students, report.totals.attendance_rate,
      ],
      [],
      ['By section'], header, ...sectionRows,
      [],
      ['By student'], studentHeader, ...studentRows,
      [],
      ['By day'], dailyHeader, ...dailyRows,
    ];
    const csv = all
      .map((row) => row.map((c) => (Array.isArray(c) ? '' : csvCell(c))).join(','))
      .join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attendance-report_${report.filters.start_date}_${report.filters.end_date}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const rateBar = (pct: number) => {
    const clamped = Math.max(0, Math.min(100, pct));
    const bar = clamped >= 80 ? 'bg-emerald-500' : clamped >= 60 ? 'bg-amber-500' : 'bg-rose-500';
    return (
      <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${clamped}%` }} />
      </div>
    );
  };

  const tabs = [
    { key: 'sections' as const, label: 'By section' },
    { key: 'students' as const, label: 'By student' },
    { key: 'daily' as const, label: 'By day' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Attendance Reports</h1>
          <p className="text-xs text-slate-500">
            Attendance rate = present / marked, where marked excludes voided records
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="p-2 rounded-xl border border-slate-200 bg-white text-slate-500 hover:text-slate-800 hover:border-slate-300 active:scale-95 transition-all disabled:opacity-60"
            aria-label="Refresh report"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={exportCsv}
            disabled={!report || loading}
            className="flex items-center gap-1.5 h-9 px-3 rounded-xl bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-60"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 rounded-2xl border border-slate-200/80 bg-white p-3">
        <div>
          <label htmlFor="att-start" className="block text-[11px] font-semibold text-slate-600 mb-1">From</label>
          <input
            id="att-start"
            type="date"
            value={startDate}
            max={endDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full h-9 rounded-lg border border-slate-300 px-2 text-xs text-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
        </div>
        <div>
          <label htmlFor="att-end" className="block text-[11px] font-semibold text-slate-600 mb-1">To</label>
          <input
            id="att-end"
            type="date"
            value={endDate}
            min={startDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full h-9 rounded-lg border border-slate-300 px-2 text-xs text-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
        </div>
        <div>
          <label htmlFor="att-grade" className="block text-[11px] font-semibold text-slate-600 mb-1">Grade</label>
          <select
            id="att-grade"
            value={gradeId}
            onChange={(e) => onGradeChange(e.target.value)}
            className="w-full h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs text-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          >
            <option value="">All grades</option>
            {grades.map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="att-section" className="block text-[11px] font-semibold text-slate-600 mb-1">Section</label>
          <select
            id="att-section"
            value={sectionId}
            onChange={(e) => setSectionId(e.target.value)}
            disabled={sections.length === 0}
            className="w-full h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs text-slate-800 focus:ring-2 focus:ring-emerald-500 focus:outline-none disabled:opacity-60"
          >
            <option value="">All sections</option>
            {sections.map((s) => (
              <option key={s.id} value={s.id}>
                {s.grade_name ? `${s.grade_name} - ` : ''}{s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error ? (
        <ErrorState title="Could not load the report" message={error} onRetry={load} />
      ) : loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : !report ? null : report.totals.marked === 0 ? (
        <EmptyState
          title="No Attendance Recorded"
          description={`No attendance records exist between ${report.filters.start_date} and ${report.filters.end_date} for the selected filters. Attendance appears here once a teacher marks a class.`}
          icon={<BarChart2 className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <>
          {/* Totals */}
          <div className="rounded-2xl border border-slate-200/80 bg-white p-4">
            <div className="flex items-baseline justify-between gap-2 mb-3">
              <h2 className="text-sm font-bold text-slate-900">Overall</h2>
              <p className="text-2xl font-extrabold text-slate-900 tracking-tight">
                {report.totals.attendance_rate}%
              </p>
            </div>
            {rateBar(report.totals.attendance_rate)}
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 mt-3">
              {STATUS_TILES.map((tile) => {
                const Icon = tile.icon;
                const value = report.totals[tile.key];
                return (
                  <div key={tile.key} className="rounded-xl bg-slate-50 px-2.5 py-2 text-center">
                    <Icon className={`w-4 h-4 mx-auto ${tile.tone}`} />
                    <p className="text-base font-extrabold text-slate-900 mt-0.5">{value}</p>
                    <p className={`text-[10px] font-bold uppercase tracking-wide ${tile.tone}`}>{tile.label}</p>
                  </div>
                );
              })}
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              {report.totals.marked} marked record{report.totals.marked === 1 ? '' : 's'} across{' '}
              {report.totals.students} student{report.totals.students === 1 ? '' : 's'}.
              {report.totals.VOID > 0 && ` ${report.totals.VOID} voided record(s) are excluded from the rate.`}
            </p>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 rounded-xl bg-slate-100 p-1">
            {tabs.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className={`flex-1 h-8 rounded-lg text-xs font-bold transition-all ${
                  tab === t.key ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-500'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === 'sections' && (
            <div className="space-y-2.5">
              {report.sections.length === 0 ? (
                <EmptyState
                  title="No Sections"
                  description="No sections match the selected filters."
                  icon={<BarChart2 className="w-10 h-10 text-slate-300" />}
                />
              ) : (
                report.sections.map((s) => (
                  <div key={s.section_id} className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs">
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-slate-900 truncate">
                          {s.grade_name ? `${s.grade_name} - ` : ''}{s.section_name}
                        </p>
                        <p className="text-[11px] text-slate-500">
                          {s.enrolled_students} enrolled · {s.students_with_records} with records
                        </p>
                      </div>
                      <span className="text-sm font-bold text-slate-900 shrink-0">{s.attendance_rate}%</span>
                    </div>
                    {rateBar(s.attendance_rate)}
                    <div className="flex flex-wrap gap-1.5 mt-2.5">
                      {STATUS_TILES.map((tile) => (
                        <span
                          key={tile.key}
                          className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${tile.chip}`}
                        >
                          {tile.label} {s[tile.key]}
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === 'students' && (
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden">
              {report.students.length === 0 ? (
                <p className="p-4 text-xs text-slate-400">No students have records in this window.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-slate-50 text-slate-500">
                        <th className="text-left font-semibold px-3 py-2">Student</th>
                        <th className="text-left font-semibold px-3 py-2">Section</th>
                        <th className="text-right font-semibold px-3 py-2">P</th>
                        <th className="text-right font-semibold px-3 py-2">A</th>
                        <th className="text-right font-semibold px-3 py-2">L</th>
                        <th className="text-right font-semibold px-3 py-2">Lv</th>
                        <th className="text-right font-semibold px-3 py-2">Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.students.map((s) => (
                        <tr key={`${s.student_id}-${s.section_id}`} className="border-t border-slate-100">
                          <td className="px-3 py-2 text-slate-900 font-medium">
                            {s.student_name || `Student #${s.student_id}`}
                            {s.admission_number ? (
                              <span className="text-slate-400 font-normal"> · {s.admission_number}</span>
                            ) : null}
                          </td>
                          <td className="px-3 py-2 text-slate-600 whitespace-nowrap">
                            {s.grade_name ? `${s.grade_name} - ` : ''}{s.section_name}
                          </td>
                          <td className="px-3 py-2 text-right text-emerald-700">{s.PRESENT}</td>
                          <td className="px-3 py-2 text-right text-rose-600">{s.ABSENT}</td>
                          <td className="px-3 py-2 text-right text-amber-600">{s.LATE}</td>
                          <td className="px-3 py-2 text-right text-sky-600">{s.LEAVE}</td>
                          <td className="px-3 py-2 text-right font-bold text-slate-900">{s.attendance_rate}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {tab === 'daily' && (
            <div className="space-y-2.5">
              {report.daily.length === 0 ? (
                <EmptyState
                  title="No Daily Data"
                  description="No attendance was recorded on any day in this window."
                  icon={<BarChart2 className="w-10 h-10 text-slate-300" />}
                />
              ) : (
                report.daily.map((d) => (
                  <div key={d.date} className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs">
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <p className="text-sm font-semibold text-slate-900">{d.date}</p>
                      <span className="text-sm font-bold text-slate-900">{d.attendance_rate}%</span>
                    </div>
                    {rateBar(d.attendance_rate)}
                    <div className="flex flex-wrap gap-1.5 mt-2.5">
                      {STATUS_TILES.map((tile) => (
                        <span
                          key={tile.key}
                          className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${tile.chip}`}
                        >
                          {tile.label} {d[tile.key]}
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AttendanceReports;
