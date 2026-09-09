import React, { useEffect, useState } from 'react';
import { reportCardService } from '../../services/reportcard';
import { studentsService } from '../../services/students';
import { academicYearsService } from '../../services/academicYears';
import { ReportCardResponse } from '../../types/reportcard';
import { ReportCardView } from '../../components/reportcard';

export const StudentReportCardPage: React.FC = () => {
  const [reportCard, setReportCard] = useState<ReportCardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [notGenerated, setNotGenerated] = useState(false);

  useEffect(() => {
    setLoading(true);
    setNotGenerated(false);
    Promise.all([studentsService.getMyStudentProfile(), academicYearsService.listAcademicYears()])
      .then(([profile, years]) => {
        const currentYear = years.find((y: any) => y.is_active) || years[0];
        if (!currentYear) throw new Error('No academic year configured');
        return reportCardService.getReportCard(profile.id, currentYear.id);
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
