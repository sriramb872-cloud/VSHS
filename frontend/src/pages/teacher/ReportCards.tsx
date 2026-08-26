// src/pages/teacher/ReportCards.tsx
import React, { useEffect, useState } from 'react';
import { reportCardService } from '../../services/reportcard';
import { ReportCardResponse } from '../../types/reportcard';
import { ReportCardView } from '../../components/reportcard';

export const TeacherReportCardsPage: React.FC = () => {
  const [reportCards, setReportCards] = useState<ReportCardResponse[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [currentRemarks, setCurrentRemarks] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    reportCardService
      .listReportCards({ academic_year_id: 1 })
      .then(data => {
        setReportCards(data.items);
        if (data.items.length > 0) {
          setSelectedStudentId(data.items[0].student_id);
          setCurrentRemarks(data.items[0].teacher_remarks || '');
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const selectedReport = reportCards.find(r => r.student_id === selectedStudentId);

  const handleSaveRemarks = async () => {
    if (!selectedStudentId) return;
    try {
      const updated = await reportCardService.updateRemarks(selectedStudentId, 1, currentRemarks);
      setReportCards(prev => prev.map(r => (r.student_id === selectedStudentId ? updated : r)));
      alert('Teacher remarks updated successfully!');
    } catch (error) {
      console.error('Failed to update remarks', error);
      alert('Failed to update remarks');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Manage Report Cards</h1>
        <p className="text-sm text-gray-500 mt-1">Review system-generated report cards and update instructor remarks.</p>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-2">
        {reportCards.map(rc => (
          <button
            key={rc.student_id}
            onClick={() => {
              setSelectedStudentId(rc.student_id);
              setCurrentRemarks(rc.teacher_remarks || '');
            }}
            className={`px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap ${
              selectedStudentId === rc.student_id
                ? 'bg-indigo-600 text-white'
                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            Student #{rc.student_id}
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
