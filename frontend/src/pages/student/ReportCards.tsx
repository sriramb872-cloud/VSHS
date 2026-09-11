import React, { useEffect, useState } from 'react';
import { reportCardService } from '../../services/reportcard';
import { studentsService } from '../../services/students';
import { academicYearsService } from '../../services/academicYears';
import { examService } from '../../services/exam';
import { ReportCardResponse } from '../../types/reportcard';
import { Exam } from '../../types/exam';
import { ReportCardView } from '../../components/reportcard';

export const StudentReportCardPage: React.FC = () => {
  const [reportCard, setReportCard] = useState<ReportCardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [notGenerated, setNotGenerated] = useState(false);
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExam, setSelectedExam] = useState('');

  useEffect(() => {
    setLoading(true);
    setNotGenerated(false);
    Promise.all([studentsService.getMyStudentProfile(), academicYearsService.listAcademicYears(), examService.listExams()])
      .then(([profile, years, examData]) => {
        const currentYear = years.find((y: any) => y.is_active) || years[0];
        if (!currentYear) throw new Error('No academic year configured');
        const published = examData.items.filter(item => item.status === 'PUBLISHED' && item.academic_year_id === currentYear.id && (!profile.section_id || item.section_id === profile.section_id));
        setExams(published);
        const selected = published[0];
        setSelectedExam(selected ? String(selected.id) : '');
        return reportCardService.getReportCard(profile.id, currentYear.id, selected?.id);
      })
      .then(setReportCard)
      .catch((err) => {
        console.error(err);
        if (err?.response?.status === 404) setNotGenerated(true);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Report Card</h1>
        <p className="text-sm text-gray-500 mt-1">Review your automated evaluation results and assessment breakdowns.</p>
      </div>

      {exams.length > 0 && <div className="mb-4"><label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="student-report-exam">Examination</label><select id="student-report-exam" value={selectedExam} onChange={async event => { const value = event.target.value; setSelectedExam(value); setLoading(true); setNotGenerated(false); try { const profile = await studentsService.getMyStudentProfile(); const years = await academicYearsService.listAcademicYears(); const currentYear = years.find((y: any) => y.is_active) || years[0]; setReportCard(await reportCardService.getReportCard(profile.id, currentYear.id, Number(value))); } catch (err: any) { if (err?.response?.status === 404) setNotGenerated(true); } finally { setLoading(false); } }} className="rounded-lg border border-slate-200 px-3 py-2 text-sm"><option value="">Select examination</option>{exams.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading report card...</div>
      ) : reportCard ? (
        <ReportCardView reportCard={reportCard} />
      ) : notGenerated ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200 text-gray-500">
          Your report card hasn't been published yet.
        </div>
      ) : (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200 text-gray-500">
          Report card not found.
        </div>
      )}
    </div>
  );
};

export default StudentReportCardPage;
/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
