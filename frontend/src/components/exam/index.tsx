// src/components/exam/index.tsx
import React from 'react';
import { Calendar, Award, Layers } from 'lucide-react';
import { Exam } from '../../types/exam';

interface ExamCardProps {
  exam: Exam;
  onClick?: () => void;
  actions?: React.ReactNode;
}

export const ExamCard: React.FC<ExamCardProps> = ({ exam, onClick, actions }) => {
  const getStatusBadge = (status?: string) => {
    switch ((status || '').toUpperCase()) {
      case 'PUBLISHED':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">Published</span>;
      case 'MARKS_IN_PROGRESS':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">In Progress</span>;
      case 'SCHEDULED':
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">Scheduled</span>;
    }
  };

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
    >
      <div>
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-base font-bold text-slate-900 line-clamp-1">{exam.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700">
                {exam.exam_type}
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-purple-50 text-purple-700">
                {exam.assessment_mode}
              </span>
            </div>
          </div>
          {getStatusBadge(exam.status)}
        </div>

        <div className="mt-4 space-y-1.5 text-xs text-slate-600">
          <div className="flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>Window: {exam.start_date} to {exam.end_date}</span>
          </div>
          <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span>Class: {exam.grade_name || `Grade ${exam.grade_id}`} - {exam.section_name || `Sec ${exam.section_id}`}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Award className="w-3.5 h-3.5 text-slate-400" />
          <span>{exam.exam_subjects?.length || 0} Subjects</span>
        </div>
        {actions && <div onClick={e => e.stopPropagation()} className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
};

export default ExamCard;