// src/pages/principal/ReportCards.tsx
import React, { useEffect, useState } from 'react';
import { reportCardService } from '../../services/reportcard';
import { ReportCard } from '../../types';
import { FileText, Download } from 'lucide-react';
import { LoadingSkeleton, EmptyState } from '../../components/shared';

export const PrincipalReportCardsPage: React.FC = () => {
  const [reportCards, setReportCards] = useState<ReportCard[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    reportCardService
      .listReportCards({ academic_year_id: 1 })
      .then(data => {
        setReportCards(data.items);
        if (data.items.length > 0) {
          setSelectedStudentId(data.items[0].student_id);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const selectedReport = reportCards.find(r => r.student_id === selectedStudentId);

  const handleExport = () => {
    console.log('Preparing institutional report cards data structure for export...');
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Report Cards</h1>
          <p className="text-xs text-slate-500">Student performance summary and grades</p>
        </div>
        <button
          onClick={handleExport}
          className="h-10 px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-1.5 hover:bg-slate-50 active:scale-95 transition-all flex-shrink-0"
        >
          <Download className="w-3.5 h-3.5" />
          Export
        </button>
      </div>

      {/* Student Tabs */}
      {reportCards.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4">
          {reportCards.map(rc => (
            <button
              key={rc.student_id}
              onClick={() => setSelectedStudentId(rc.student_id)}
              className={`h-9 px-4 rounded-full text-xs font-semibold whitespace-nowrap flex-shrink-0 transition-all ${
                selectedStudentId === rc.student_id
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-white border border-slate-200 text-slate-600'
              }`}
            >
              Student #{rc.student_id}
            </button>
          ))}
        </div>
      )}

      {/* Report Card View */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-4">
            <LoadingSkeleton type="card" count={3} />
          </div>
        ) : selectedReport ? (
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Student #{selectedReport.student_id}</h3>
                <p className="text-xs text-slate-500">Academic Year ID: {selectedReport.academic_year_id}</p>
              </div>
              {selectedReport.grade && (
                <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700">
                  Grade: {selectedReport.grade}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs text-slate-600">
              {selectedReport.percentage !== undefined && (
                <div><span className="font-medium text-slate-700">Percentage:</span> {selectedReport.percentage}%</div>
              )}
              {selectedReport.obtained_marks !== undefined && (
                <div><span className="font-medium text-slate-700">Marks:</span> {selectedReport.obtained_marks} / {selectedReport.total_marks}</div>
              )}
              {selectedReport.rank !== undefined && (
                <div><span className="font-medium text-slate-700">Rank:</span> {selectedReport.rank}</div>
              )}
              {selectedReport.attendance_percentage !== undefined && (
                <div><span className="font-medium text-slate-700">Attendance:</span> {selectedReport.attendance_percentage}%</div>
              )}
            </div>
            {selectedReport.teacher_remarks && (
              <p className="text-xs text-slate-500 border-t border-slate-100 pt-3">{selectedReport.teacher_remarks}</p>
            )}
          </div>
        ) : (
          <EmptyState
            title="No Report Cards"
            description="No report cards are available for this academic year."
            icon={<FileText className="w-10 h-10 text-slate-300" />}
          />
        )}
      </div>
    </div>
  );
};

export default PrincipalReportCardsPage;
