// src/pages/teacher/ReportCards.tsx
import React, { useEffect, useState } from 'react';
import { reportCardService } from '../../services/reportcard';
import { ReportCardResponse } from '../../types/reportcard';
import { ReportCardView } from '../../components/reportcard';
import { useAcademicYear } from '../../contexts/AcademicYearContext';

export const TeacherReportCardsPage: React.FC = () => {
  const [reportCards, setReportCards] = useState<ReportCardResponse[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [currentRemarks, setCurrentRemarks] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  // The header selector is the single source of truth for which year is on
  // screen - no more "first active year we happen to receive" guessing.
  const { selectedYear, selectedYearId, loading: yearsLoading, isHistorical } = useAcademicYear();

  // A student can have one report card per exam in a year, so the card must be
  // identified by student *and* exam - keying on student_id alone made the
  // second card unreachable and sent remarks to the wrong exam.
  const cardKey = (card: ReportCardResponse) => `${card.student_id}:${card.exam_id ?? 'year'}`;

  useEffect(() => {
    if (yearsLoading || !selectedYear) return;
    let cancelled = false;
    setLoading(true);
    setSelectedKey(null);
    reportCardService
      .listReportCards({ academic_year_id: selectedYear.id })
      .then((data) => {
        if (cancelled) return;
        setReportCards(data.items);
        if (data.items.length > 0) {
          setSelectedKey(cardKey(data.items[0]));
          setCurrentRemarks(data.items[0].teacher_remarks || '');
        } else {
          setCurrentRemarks('');
        }
      })
      .catch((err) => {
        if (!cancelled) setReportCards([]);
        console.error(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedYear?.id, yearsLoading]);

  const selectedReport = reportCards.find(r => cardKey(r) === selectedKey);

  const handleSaveRemarks = async () => {
    if (!selectedReport || !selectedYearId || isHistorical) return;
    try {
      const updated = await reportCardService.updateRemarks(
        selectedReport.student_id,
        selectedYearId,
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
        <p className="text-sm text-gray-500 mt-1">
          Review system-generated report cards and update instructor remarks.
          {selectedYear ? ` Showing ${selectedYear.name}.` : ''}
        </p>
      </div>

      {isHistorical && (
        <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold">
          You are viewing a {selectedYear?.status.toLowerCase()} academic year — report cards are
          read-only.
        </div>
      )}

      {feedback && (
        <div
          className={`p-3 rounded-xl text-xs font-medium ${
            feedback.type === 'success'
              ? 'bg-[var(--brand-light)] border border-[var(--brand-border)] text-[var(--brand-strong)]'
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
                ? 'bg-[var(--brand)] text-white'
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
          editableRemarks={!isHistorical}
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
