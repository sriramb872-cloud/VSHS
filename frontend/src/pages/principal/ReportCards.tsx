import React, { useEffect, useMemo, useState } from 'react';
import { FileText, Download, RefreshCw } from 'lucide-react';
import { reportCardService } from '../../services/reportcard';
import { examService } from '../../services/exam';
import { ReportCardResponse } from '../../types/reportcard';
import { Exam } from '../../types/exam';
import { LoadingSkeleton, EmptyState } from '../../components/shared';

export const PrincipalReportCardsPage: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [cards, setCards] = useState<ReportCardResponse[]>([]);
  const [year, setYear] = useState('');
  const [section, setSection] = useState('');
  const [exam, setExam] = useState('');
  const [student, setStudent] = useState('');
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    Promise.all([examService.listExams(), reportCardService.listReportCards({ limit: 100 })])
      .then(([examData, cardData]) => { setExams(examData.items); setCards(cardData.items as unknown as ReportCardResponse[]); })
      .catch(err => setMessage(err?.response?.data?.detail || 'Unable to load report-card data.'))
      .finally(() => setLoading(false));
  }, []);

  const contexts = useMemo(() => {
    const map = new Map<string, { year: number; section: number; label: string }>();
    exams.forEach(exam => map.set(`${exam.academic_year_id}-${exam.section_id}`, { year: exam.academic_year_id, section: exam.section_id, label: `${exam.grade_name || `Grade ${exam.grade_id}`} - ${exam.section_name || `Section ${exam.section_id}`} · ${exam.academic_year_id === 2 ? '2026-2027' : `Year ${exam.academic_year_id}`}` }));
    return [...map.values()];
  }, [exams]);
  const selectedCard = cards.find(card => String(card.student_id) === student) || cards[0];
  const selectedContext = contexts.find(ctx => String(ctx.year) === year && String(ctx.section) === section);
  const availableExams = exams.filter(item => String(item.academic_year_id) === year && String(item.section_id) === section && item.status === 'PUBLISHED');

  // Once an examination is selected, reload only that examination's cards.
  // This prevents legacy cards (created before exam-aware report cards) from
  // being shown after a refresh and makes the selected context persistent.
  useEffect(() => {
    if (!selectedContext || !exam) return;
    reportCardService.listReportCards({
      academic_year_id: selectedContext.year,
      section_id: selectedContext.section,
      exam_id: Number(exam),
      limit: 100,
    }).then(response => {
      setCards(response.items as unknown as ReportCardResponse[]);
      if (response.items.length) setStudent(String(response.items[0].student_id));
    }).catch(err => setMessage(err?.response?.data?.detail || 'Unable to load the selected report cards.'));
  }, [exam, selectedContext]);

  const generate = async () => {
    if (!selectedContext) return;
    setGenerating(true); setMessage('');
    try {
      const response = await reportCardService.generateReportCards(selectedContext.year, selectedContext.section, exam ? Number(exam) : undefined);
      setCards(response.items as unknown as ReportCardResponse[]);
      if (response.items.length) setStudent(String(response.items[0].student_id));
      setMessage(`Generated ${response.items.length} report card${response.items.length === 1 ? '' : 's'} from published examination results.`);
    } catch (err: any) { setMessage(err?.response?.data?.detail || 'Report-card generation failed.'); }
    finally { setGenerating(false); }
  };

  return <div className="space-y-4">
    <div className="flex items-start justify-between gap-2"><div><h1 className="text-xl font-bold text-slate-900">Report Cards</h1><p className="text-xs text-slate-500">Generate and review student performance from published marks</p></div><button className="h-10 px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5" />Export</button></div>
    <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-xs grid grid-cols-1 sm:grid-cols-3 gap-2">
      <select aria-label="Academic Year" value={year} onChange={e => { setYear(e.target.value); setSection(''); }} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">Select Academic Year</option>{[...new Set(contexts.map(ctx => ctx.year))].map(value => <option key={value} value={value}>{value === 2 ? '2026-2027' : `Year ${value}`}</option>)}</select>
      <select aria-label="Class and Section" value={section} onChange={e => { setSection(e.target.value); setExam(''); }} disabled={!year} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">Select Class / Section</option>{contexts.filter(ctx => String(ctx.year) === year).map(ctx => <option key={ctx.section} value={ctx.section}>{ctx.label.split(' · ')[0]}</option>)}</select>
      <select aria-label="Examination" value={exam} onChange={e => setExam(e.target.value)} disabled={!section} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><option value="">Select Published Examination</option>{availableExams.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <button onClick={generate} disabled={!selectedContext || !exam || generating} className="rounded-xl bg-emerald-600 text-white text-xs font-bold px-4 py-2 disabled:opacity-50 flex items-center justify-center gap-2"><RefreshCw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />{generating ? 'Generating…' : 'Generate / Refresh Report Cards'}</button>
    </div>
    {message && <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-800 text-xs font-medium">{message}</div>}
    {loading ? <LoadingSkeleton type="card" count={3} /> : cards.length === 0 ? <EmptyState title="No Report Cards" description="Select an academic year and class/section, then generate cards after marks are published." icon={<FileText className="w-10 h-10 text-slate-300" />} /> : <>
      <div className="flex gap-2 overflow-x-auto pb-1">{cards.map(card => <button key={card.student_id} onClick={() => setStudent(String(card.student_id))} className={`h-9 px-4 rounded-full text-xs font-semibold whitespace-nowrap ${String(card.student_id) === String(selectedCard?.student_id) ? 'bg-emerald-600 text-white' : 'bg-white border border-slate-200 text-slate-600'}`}>{card.student_name || `Student #${card.student_id}`}</button>)}</div>
      {selectedCard && <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-5 space-y-4"><div><h2 className="text-lg font-bold text-slate-900">{selectedCard.student_name}</h2><p className="text-xs text-slate-500">Class/Section ID: {selectedCard.grade_id} / {selectedCard.section_id} · Academic year: {selectedCard.academic_year_id === 2 ? '2026-2027' : selectedCard.academic_year_id}</p></div><div className="overflow-x-auto"><table className="w-full text-xs"><thead><tr className="border-b border-slate-100 text-slate-500"><th className="text-left py-2">Subject</th><th className="text-right py-2">Maximum</th><th className="text-right py-2">Obtained</th><th className="text-right py-2">Percentage</th><th className="text-right py-2">Grade</th><th className="text-right py-2">Result</th></tr></thead><tbody>{selectedCard.subjects.map(subject => <tr key={subject.subject_id} className="border-b border-slate-50"><td className="py-2 font-semibold text-slate-700">{subject.subject_name}</td><td className="py-2 text-right">{subject.subject_total_maximum}</td><td className="py-2 text-right">{subject.subject_total_obtained}</td><td className="py-2 text-right">{subject.percentage}%</td><td className="py-2 text-right">{subject.grade}</td><td className="py-2 text-right">{subject.percentage >= 40 ? 'Pass' : 'Fail'}</td></tr>)}</tbody></table></div><div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs"><div><span className="text-slate-500 block">Total Maximum</span><strong>{selectedCard.grand_total_maximum}</strong></div><div><span className="text-slate-500 block">Total Obtained</span><strong>{selectedCard.grand_total_obtained}</strong></div><div><span className="text-slate-500 block">Overall</span><strong>{selectedCard.overall_percentage}%</strong></div><div><span className="text-slate-500 block">Result</span><strong>{selectedCard.overall_grade} · {selectedCard.overall_result}</strong></div></div></div>}
    </>}
  </div>;
};

export default PrincipalReportCardsPage;
