import React, { useEffect, useState } from 'react';
import { reportCardService } from '../../services/reportcard';
import { studentsService } from '../../services/students';
import { useAcademicYear } from '../../contexts/AcademicYearContext';
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
  // Which year is on screen comes from the global selector, so switching years
  // in the header re-scopes this page too (the header carries the id on every
  // request as well, so the backend agrees with what the UI shows).
  const { selectedYear, selectedYearId, loading: yearsLoading, isHistorical } = useAcademicYear();

  useEffect(() => {
    if (yearsLoading || !selectedYear) return;
    let cancelled = false;
    setLoading(true);
    setNotGenerated(false);
    setSelectedExam('');
    Promise.all([
      studentsService.getMyStudentProfile(),
      examService.listExams({ academic_year_id: selectedYear.id }),
    ])
      .then(([profile, examData]) => {
        if (cancelled) return;
        const published = examData.items.filter(
          (item) =>
            item.status === 'PUBLISHED' &&
            item.academic_year_id === selectedYear.id &&
            (!profile.section_id || item.section_id === profile.section_id)
        );
        setExams(published);
        const selected = published[0];
        setSelectedExam(selected ? String(selected.id) : '');
        return reportCardService.getReportCard(profile.id, selectedYear.id, selected?.id);
      })
      .then((card) => {
        if (!cancelled) setReportCard(card ?? null);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setReportCard(null);
        if (err?.response?.status === 404) setNotGenerated(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedYear?.id, yearsLoading]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Report Card</h1>
        <p className="text-sm text-gray-500 mt-1">
          Review your automated evaluation results and assessment breakdowns.
          {selectedYear ? ` Showing ${selectedYear.name}.` : ''}
        </p>
      </div>

      {isHistorical && (
        <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold">
          Historical record — you are viewing report cards from {selectedYear?.status} year{' '}
          {selectedYear?.name}.
        </div>
      )}

      {exams.length > 0 && (
        <div className="mb-4">
          <label
            className="block text-xs font-semibold text-slate-600 mb-1"
            htmlFor="student-report-exam"
          >
            Examination
          </label>
          <select
            id="student-report-exam"
            value={selectedExam}
            onChange={async (event) => {
              const value = event.target.value;
              setSelectedExam(value);
              if (!selectedYearId) return;
              setLoading(true);
              setNotGenerated(false);
              try {
                const profile = await studentsService.getMyStudentProfile();
                setReportCard(
                  await reportCardService.getReportCard(
                    profile.id,
                    selectedYearId,
                    Number(value)
                  )
                );
              } catch (err: any) {
                setReportCard(null);
                if (err?.response?.status === 404) setNotGenerated(true);
              } finally {
                setLoading(false);
              }
            }}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          >
            <option value="">Select examination</option>
            {exams.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
      )}

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
