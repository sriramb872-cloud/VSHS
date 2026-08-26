// src/components/reportcard/index.tsx
import React from 'react';
import { ReportCardResponse } from '../../types/reportcard';
import { Award, BookOpen, CheckCircle, AlertCircle } from 'lucide-react';

interface ReportCardViewProps {
  reportCard: ReportCardResponse;
  editableRemarks?: boolean;
  onRemarksChange?: (remarks: string) => void;
  onSaveRemarks?: () => void;
}

export const ReportCardView: React.FC<ReportCardViewProps> = ({
  reportCard,
  editableRemarks = false,
  onRemarksChange,
  onSaveRemarks,
}) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-4 border-b border-gray-200 gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Student Report Card</h2>
          <p className="text-sm text-gray-500">Student ID: {reportCard.student_id} | Grade: {reportCard.grade_id}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
            reportCard.overall_result === 'Pass' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            {reportCard.overall_result === 'Pass' ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
            {reportCard.overall_result} ({reportCard.overall_percentage}%) - {reportCard.overall_grade}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-md font-semibold text-gray-800 flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-indigo-600" /> Subject-wise Performance
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Subject</th>
                <th className="px-4 py-3 text-left font-semibold">Assessments Breakdown</th>
                <th className="px-4 py-3 text-center font-semibold">Total Obtained</th>
                <th className="px-4 py-3 text-center font-semibold">Percentage</th>
                <th className="px-4 py-3 text-center font-semibold">Grade</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {reportCard.subjects.map(subject => (
                <tr key={subject.subject_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{subject.subject_name}</td>
                  <td className="px-4 py-3 space-y-1">
                    {subject.assessments.map((ass, idx) => (
                      <div key={idx} className="text-xs text-gray-600">
                        <span className="font-semibold">{ass.assessment_name}:</span> {ass.total_obtained} / {ass.total_maximum}
                      </div>
                    ))}
                  </td>
                  <td className="px-4 py-3 text-center font-semibold text-gray-800">
                    {subject.subject_total_obtained} / {subject.subject_total_maximum}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-600">{subject.percentage}%</td>
                  <td className="px-4 py-3 text-center font-bold text-indigo-600">{subject.grade}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="pt-4 border-t border-gray-200">
        <h3 className="text-md font-semibold text-gray-800 mb-2">Teacher Remarks</h3>
        {editableRemarks ? (
          <div className="space-y-2">
            <textarea
              rows={3}
              value={reportCard.teacher_remarks || ''}
              onChange={e => onRemarksChange && onRemarksChange(e.target.value)}
              placeholder="Enter constructive remarks for the student..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
            />
            <button
              onClick={onSaveRemarks}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
            >
              Save Remarks
            </button>
          </div>
        ) : (
          <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-md border border-gray-100">
            {reportCard.teacher_remarks || 'No remarks provided.'}
          </p>
        )}
      </div>
    </div>
  );
};

export default ReportCardView;
/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
