// src/pages/student/ReportCard.tsx
import React, { useEffect, useState } from 'react';
import { reportCardService } from '../../services/reportcard';
import { ReportCardResponse } from '../../types/reportcard';
import { ReportCardView } from '../../components/reportcard';

export const StudentReportCardPage: React.FC = () => {
  const [reportCard, setReportCard] = useState<ReportCardResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    // Assuming student ID 101 for current session context
    reportCardService
      .getReportCard(101, 1)
      .then(setReportCard)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Report Card</h1>
        <p className="text-sm text-gray-500 mt-1">Review your automated evaluation results and assessment breakdowns.</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading report card...</div>
      ) : reportCard ? (
        <ReportCardView reportCard={reportCard} />
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
