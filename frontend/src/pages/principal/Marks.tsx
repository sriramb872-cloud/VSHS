import React, { useEffect, useMemo, useState } from 'react';
import { BarChart2, Download, UserRound } from 'lucide-react';
import { marksService } from '../../services/marks';
import { examService } from '../../services/exam';
import { Mark } from '../../types';
import { Exam } from '../../types/exam';
import { LoadingSkeleton, EmptyState } from '../../components/shared';

export const PrincipalMarksPage: React.FC = () => {
  const [marks, setMarks] = useState<Mark[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ academicYear: '', grade: '', section: '', exam: '', subject: '' });
  const [selectedStudent, setSelectedStudent] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([marksService.listMarks({ limit: 100 }), examService.listExams()])
      .then(([markData, examData]) => { setMarks(markData.items); setExams(examData.items); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const examMap = useMemo(() => new Map(exams.map(exam => [exam.id, exam])), [exams]);
  const filteredMarks = useMemo(() => marks.filter(mark =>
    (!filters.academicYear || String(mark.academic_year_id) === filters.academicYear) &&
    (!filters.grade || String(mark.grade_id) === filters.grade) &&
    (!filters.section || String(mark.section_id) === filters.section) &&
    (!filters.exam || String(mark.exam_id) === filters.exam) &&
    (!filters.subject || String(mark.subject_id) === filters.subject)
  ), [marks, filters]);
  const groups = useMemo(() => {
    const grouped = new Map<number, Mark[]>();
    filteredMarks.forEach(mark => grouped.set(mark.student_id, [...(grouped.get(mark.student_id) || []), mark]));
    return [...grouped.entries()];
  }, [filteredMarks]);
  const selectedRows = selectedStudent === null ? [] : (groups.find(([id]) => id === selectedStudent)?.[1] || []);
  const unique = (key: keyof Mark) => [...new Set(marks.map(mark => mark[key]).filter(value => value !== undefined && value !== null))];
  const examLabel = (id: number) => examMap.get(id)?.name || marks.find(mark => mark.exam_id === id)?.exam_name || `Exam #${id}`;
  const classLabel = (mark: Mark) => { const exam = mark.exam_id ? examMap.get(mark.exam_id) : undefined; return `${exam?.grade_name || `Grade ${mark.grade_id}`} - ${exam?.section_name || `Section ${mark.section_id}`}`; };
  const setFilter = (name: keyof typeof filters, value: string) => setFilters(prev => ({ ...prev, [name]: value }));

  return <div className="space-y-4">
    <div className="flex items-start justify-between gap-2"><div><h1 className="text-xl font-bold text-slate-900">Marks Monitor</h1><p className="text-xs text-slate-500">Review examination marks within your school</p></div><button className="h-10 px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5" />Export</button></div>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
      <select aria-label="Academic Year" value={filters.academicYear} onChange={e => setFilter('academicYear', e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">All Academic Years</option>{unique('academic_year_id').map(id => <option key={String(id)} value={String(id)}>{id === 2 ? '2026-2027' : `Year ${id}`}</option>)}</select>
      <select aria-label="Class" value={filters.grade} onChange={e => setFilter('grade', e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">All Classes</option>{unique('grade_id').map(id => <option key={String(id)} value={String(id)}>{exams.find(e => e.grade_id === id)?.grade_name || `Grade ${id}`}</option>)}</select>
      <select aria-label="Section" value={filters.section} onChange={e => setFilter('section', e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">All Sections</option>{unique('section_id').map(id => <option key={String(id)} value={String(id)}>{exams.find(e => e.section_id === id)?.section_name || `Section ${id}`}</option>)}</select>
      <select aria-label="Examination" value={filters.exam} onChange={e => setFilter('exam', e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">All Examinations</option>{unique('exam_id').map(id => <option key={String(id)} value={String(id)}>{examLabel(Number(id))}</option>)}</select>
      <select aria-label="Subject" value={filters.subject} onChange={e => setFilter('subject', e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">All Subjects</option>{unique('subject_id').map(id => <option key={String(id)} value={String(id)}>{marks.find(mark => mark.subject_id === id)?.subject_name || `Subject ${id}`}</option>)}</select>
    </div>
    {loading ? <LoadingSkeleton type="card" count={3} /> : groups.length === 0 ? <EmptyState title="No Marks Recorded" description="No marks match the selected filters." icon={<BarChart2 className="w-10 h-10 text-slate-300" />} /> : <div className="space-y-3">{groups.map(([studentId, rows]) => { const total = rows.reduce((sum, row) => sum + Number(row.marks_obtained || 0), 0); const max = rows.reduce((sum, row) => sum + Number(row.max_marks || 0), 0); const percentage = max ? Math.round((total / max) * 10000) / 100 : 0; return <button key={studentId} onClick={() => setSelectedStudent(studentId)} className="w-full text-left bg-white rounded-2xl border border-slate-200/80 shadow-xs p-4 hover:border-emerald-300"><div className="flex items-start justify-between gap-3"><div><h3 className="text-sm font-semibold text-slate-900">{rows[0].student_name || `Student #${studentId}`}</h3><p className="text-xs text-slate-500">{classLabel(rows[0])} · {rows[0].roll_number ? `Roll ${rows[0].roll_number}` : 'Roll not recorded'}</p></div><span className="text-xs font-bold text-emerald-700">{total} / {max} · {percentage}%</span></div><div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2">{rows.map(row => <div key={row.id} className="rounded-lg bg-slate-50 px-3 py-2 text-xs"><div className="font-semibold text-slate-700">{row.subject_name || `Subject ${row.subject_id}`}</div><div className="text-slate-500">{row.marks_obtained} / {row.max_marks}</div></div>)}</div></button>; })}</div>}
    {selectedStudent !== null && <div className="bg-white rounded-2xl border border-emerald-200 p-5 shadow-xs"><div className="flex items-center gap-2 mb-3"><UserRound className="w-4 h-4 text-emerald-600" /><h2 className="text-sm font-bold text-slate-900">Student Marks Detail</h2></div><p className="text-sm font-semibold text-slate-800">{selectedRows[0]?.student_name || `Student #${selectedStudent}`}</p><p className="text-xs text-slate-500 mb-3">{selectedRows[0] ? classLabel(selectedRows[0]) : ''} · Academic year {selectedRows[0]?.academic_year_id === 2 ? '2026-2027' : selectedRows[0]?.academic_year_id}</p>{selectedRows.map(row => <div key={row.id} className="flex justify-between border-t border-slate-100 py-2 text-xs"><span>{examLabel(row.exam_id || 0)} · {row.subject_name}</span><strong>{row.marks_obtained} / {row.max_marks}</strong></div>)}</div>}
  </div>;
};

export default PrincipalMarksPage;
