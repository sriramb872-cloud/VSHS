// src/components/exam/index.tsx
import React from 'react';
import { Calendar, Clock, Award, BookOpen, Layers } from 'lucide-react';
import { Exam } from '../../types/exam';

interface ExamCardProps {
  exam: Exam;
  onClick?: () => void;
  actions?: React.ReactNode;
}

export const ExamCard: React.FC<ExamCardProps> = ({ exam, onClick, actions }) => {
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer flex flex-col justify-between"
    >
      <div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-1">{exam.name}</h3>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 shrink-0">
            {exam.exam_type}
          </span>
        </div>
        
        <div className="mt-3 space-y-1.5 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <span>Date: {exam.exam_date}</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <span>Time: {exam.start_time} - {exam.end_time}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Award className="w-3.5 h-3.5" /> Max: {exam.maximum_marks}
          </span>
          <span className="flex items-center gap-1">
            <Layers className="w-3.5 h-3.5" /> Grade/Sec: {exam.grade_id}-{exam.section_id}
          </span>
        </div>
        {actions && <div onClick={e => e.stopPropagation()} className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
};

export default ExamCard;