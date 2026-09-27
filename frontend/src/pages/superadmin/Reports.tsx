// src/pages/superadmin/Reports.tsx
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Download, FileText, RefreshCw, Building, Users, GraduationCap, BookOpen, ClipboardList } from 'lucide-react';
import { LoadingSkeleton, ErrorState, StatusBadge } from '../../components/shared';
import { reportsService } from '../../services/reports';
import { PlatformReport, SchoolRollup } from '../../types/reports';
import errorMessage from '../../helpers/errorMessage';

const isoDay = (d: Date) => d.toISOString().slice(0, 10);

function defaultWindow() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return { start: isoDay(start), end: isoDay(end) };
}

/** Escape a CSV cell and quote it. */
const csvCell = (value: unknown): string => {
  const s = value === null || value === undefined ? '' : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

const csvRow = (cells: unknown[]) => cells.map(csvCell).join(',');

function downloadCsv(filename: string, rows: unknown[][]) {
  const blob = new Blob([rows.map(csvRow).join('\r\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const Metric: React.FC<{ icon: React.ReactNode; label: string; value: string | number }> = ({
  icon,
  label,
  value,
}) => (
  <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs">
    <div className="flex items-center gap-2 mb-1.5">
      <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
        {icon}
      </div>
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</span>
    </div>
    <p className="text-2xl font-extrabold text-slate-900 tracking-tight">{value}</p>
  </div>
);

export const SuperAdminReports: React.FC = () => {
  const [report, setReport] = useState<PlatformReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const initial = useMemo(defaultWindow, []);
  const [startDate, setStartDate] = useState(initial.start);
  const [endDate, setEndDate] = useState(initial.end);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportsService.getPlatformReport({
        start_date: startDate,
        end_date: endDate,
      });
      setReport(data);
    } catch (err) {
      setError(errorMessage(err, 'Failed to load the platform report.'));
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    load();
  }, [load]);

  const exportCsv = () => {
    if (!report) return;
    const { summary, schools } = report;
    const rows: unknown[][] = [
      ['SCHOLARIS platform report'],
      ['Window', summary.window_start, 'to', summary.window_end],
      ['Generated', summary.generated_at],
      [],
      ['Metric', 'Value'],
      ['Schools', summary.school_count],
      ['Active schools', summary.active_school_count],
      ['Users', summary.user_count],
      ['Active users', summary.active_user_count],
      ['Inactive users', summary.inactive_user_count],
      ['Users attached to a school', summary.school_user_count],
      ['Platform-level users', summary.platform_user_count],
      ['Students', summary.student_count],
      ['Teachers', summary.teacher_count],
      ['Grades', summary.grade_count],
      ['Sections', summary.section_count],
      ['Subjects', summary.subject_count],
      ['Exams', summary.exam_count],
      ['Published exams', summary.published_exam_count],
      ['Marks records', summary.marks_record_count],
      ['Report cards', summary.report_card_count],
      ['Attendance records (window)', summary.attendance_record_count],
      ['Audit events (window)', summary.audit_event_count],
      [],
      [
        'School ID',
        'School',
        'Code',
        'Active',
        'Students',
        'Teachers',
        'Active staff',
        'Sections',
        'Exams',
        'Report cards',
        'Attendance records (window)',
        'Last audit',
      ],
      ...schools.map((s) => [
        s.school_id,
        s.school_name,
        s.school_code,
        s.is_active ? 'yes' : 'no',
        s.student_count,
        s.teacher_count,
        s.staff_count,
        s.section_count,
        s.exam_count,
        s.report_card_count,
        s.attendance_record_count,
        s.last_audit_at,
      ]),
    ];
    downloadCsv(`scholaris-platform-report-${summary.window_start}_${summary.window_end}.csv`, rows);
  };

  const schoolColumns: Array<{ key: keyof SchoolRollup; label: string }> = [
    { key: 'school_name', label: 'School' },
    { key: 'student_count', label: 'Students' },
    { key: 'teacher_count', label: 'Teachers' },
    { key: 'section_count', label: 'Sections' },
    { key: 'exam_count', label: 'Exams' },
    { key: 'report_card_count', label: 'Report cards' },
    { key: 'attendance_record_count', label: 'Attendance' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-slate-900">System Reports</h1>
          <p className="text-xs text-slate-500">
            Platform-wide totals and per-school rollup, counted live from the database
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
            className="flex items-center gap-1.5 h-9 px-3 rounded-xl bg-indigo-600 text-white text-xs font-bold hover:bg-indigo-700 active:scale-95 transition-all disabled:opacity-60"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-2 rounded-2xl border border-slate-200/80 bg-white p-3">
        <div>
          <label htmlFor="report-start" className="block text-[11px] font-semibold text-slate-600 mb-1">
            From
          </label>
          <input
            id="report-start"
            type="date"
            value={startDate}
            max={endDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 px-2 text-xs text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
        </div>
        <div>
          <label htmlFor="report-end" className="block text-[11px] font-semibold text-slate-600 mb-1">
            To
          </label>
          <input
            id="report-end"
            type="date"
            value={endDate}
            min={startDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 px-2 text-xs text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
        </div>
        <p className="text-[11px] text-slate-500 ml-auto">
          Window applies to attendance and audit counts; head counts are current totals.
        </p>
      </div>

      {error ? (
        <ErrorState title="Could not load the report" message={error} onRetry={load} />
      ) : loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : !report ? (
        <p className="text-xs text-slate-400">No report data.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            <Metric icon={<Building className="w-4 h-4" />} label="Schools" value={report.summary.school_count} />
            <Metric
              icon={<Users className="w-4 h-4" />}
              label="Users"
              value={`${report.summary.user_count} (${report.summary.platform_user_count} platform)`}
            />
            <Metric icon={<GraduationCap className="w-4 h-4" />} label="Students" value={report.summary.student_count} />
            <Metric icon={<BookOpen className="w-4 h-4" />} label="Teachers" value={report.summary.teacher_count} />
            <Metric icon={<ClipboardList className="w-4 h-4" />} label="Sections" value={report.summary.section_count} />
            <Metric icon={<FileText className="w-4 h-4" />} label="Exams" value={report.summary.exam_count} />
            <Metric icon={<FileText className="w-4 h-4" />} label="Marks" value={report.summary.marks_record_count} />
            <Metric icon={<FileText className="w-4 h-4" />} label="Report cards" value={report.summary.report_card_count} />
          </div>

          <div className="rounded-2xl border border-slate-200/80 bg-white overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900">Per-school rollup</h2>
              <p className="text-[11px] text-slate-500">
                Generated {report.summary.generated_at}
              </p>
            </div>
            {report.schools.length === 0 ? (
              <p className="p-4 text-xs text-slate-400">No schools on the platform.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-slate-50 text-slate-500">
                      {schoolColumns.map((c) => (
                        <th key={String(c.key)} className="text-left font-semibold px-3 py-2 whitespace-nowrap">
                          {c.label}
                        </th>
                      ))}
                      <th className="text-left font-semibold px-3 py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.schools.map((s) => (
                      <tr key={s.school_id} className="border-t border-slate-100">
                        <td className="px-3 py-2 text-slate-900 font-medium whitespace-nowrap">
                          {s.school_name}
                          {s.school_code ? (
                            <span className="text-slate-400 font-normal"> · {s.school_code}</span>
                          ) : null}
                        </td>
                        {schoolColumns.slice(1).map((c) => (
                          <td key={String(c.key)} className="px-3 py-2 text-slate-700">
                            {String(s[c.key] ?? 0)}
                          </td>
                        ))}
                        <td className="px-3 py-2">
                          <StatusBadge status={s.is_active ? 'ACTIVE' : 'INACTIVE'} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default SuperAdminReports;
