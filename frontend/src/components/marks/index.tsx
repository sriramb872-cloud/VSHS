// src/components/marks/index.tsx
import React from 'react';
import { Award, BookOpen, User } from 'lucide-react';
import { Mark } from '../../types/marks';

interface MarkCardProps {
  mark: Mark;
  examName?: string;
  maximumMarks?: number;
}

export const MarkCard: React.FC<MarkCardProps> = ({ mark, examName, maximumMarks }) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-base font-semibold text-gray-900">{examName || `Exam ID: ${mark.exam_id}`}</h3>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 shrink-0">
            Score: {mark.marks_obtained} {maximumMarks ? `/ ${maximumMarks}` : ''}
          </span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500 flex items-center justify-between">
        <span>Student ID: {mark.student_id}</span>
        <span>Recorded: {new Date(mark.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  );
};

export default MarkCard;