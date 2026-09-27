// src/pages/teacher/ReportCards.tsx
import React, { useEffect, useState } from 'react';
import { reportCardService } from '../../services/reportcard';
import { ReportCardResponse } from '../../types/reportcard';
import { ReportCardView } from '../../components/reportcard';
import { academicYearsService } from '../../services/academicYears';

export const TeacherReportCardsPage: React.FC = () => {
  const [reportCards, setReportCards] = useState<ReportCardResponse[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [currentRemarks, setCurrentRemarks] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [academicYearId, setAcademicYearId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // A student can have one report card per exam in a year, so the card must be
  // identified by student *and* exam - keying on student_id alone made the
  // second card unreachable and sent remarks to the wrong exam.
  const cardKey = (card: ReportCardResponse) => `${card.student_id}:${card.exam_id ?? 'year'}`;

  useEffect(() => {
    setLoading(true);
    academicYearsService.listAcademicYears()
      .then(years => {
        const activeYear = years.find(year => year.is_active) || years[0];
        setAcademicYearId(activeYear?.id ?? null);
        return activeYear ? reportCardService.listReportCards({ academic_year_id: activeYear.id }) : null;
      })
      .then(data => {
        if (!data) return;
        setReportCards(data.items);        if (data.items.length > 0) {
          setSelectedKey(cardKey(data.items[0]));
          setCurrentRemarks(data.items[0].teacher_remarks || '');
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const selectedReport = reportCards.find(r => cardKey(r) === selectedKey);

  const handleSaveRemarks = async () => {
    if (!selectedReport || !academicYearId) return;
    try {
      const updated = await reportCardService.updateRemarks(
        selectedReport.student_id,
        academicYearId,
        currentRemarks,
        selectedReport.exam_id ?? undefined
      );
      setReportCards(prev =>
        prev.map(r => (cardKey(r) === selectedKey ? { ...r, ...updated } : r))
      );
      setFeedback({ type: 'success', text: 'Teacher remarks updated successfully!' });
    } catch (error: any) {
      console.error('Failed to update remarks', error);
      setFeedback({
        type: 'error',
        text: error?.response?.data?.detail || 'Failed to update remarks',
      });
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Manage Report Cards</h1>
        <p className="text-sm text-gray-500 mt-1">Review system-generated report cards and update instructor remarks.</p>
      </div>

      {feedback && (
        <div
          className={`p-3 rounded-xl text-xs font-medium ${
            feedback.type === 'success'
              ? 'bg-blue-50 border border-blue-200 text-blue-800'
              : 'bg-rose-50 border border-rose-200 text-rose-700'
          }`}
        >
          {feedback.text}
        </div>
      )}

      <div className="flex gap-2 overflow-x-auto pb-2">
        {reportCards.map(rc => (
          <button
            key={cardKey(rc)}
            onClick={() => {
              setSelectedKey(cardKey(rc));
              setCurrentRemarks(rc.teacher_remarks || '');
            }}
            className={`px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap ${
              selectedKey === cardKey(rc)
                ? 'bg-indigo-600 text-white'
                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {rc.student_name || `Student #${rc.student_id}`}
            {rc.exam_name ? ` · ${rc.exam_name}` : ''}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading report cards...</div>
      ) : selectedReport ? (
        <ReportCardView
          reportCard={{ ...selectedReport, teacher_remarks: currentRemarks }}
          editableRemarks={true}
          onRemarksChange={setCurrentRemarks}
          onSaveRemarks={handleSaveRemarks}
        />
      ) : (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200 text-gray-500">
          No report cards available.
        </div>
      )}
    </div>
  );
};

export default TeacherReportCardsPage;
/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
