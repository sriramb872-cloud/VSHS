// src/components/homework/index.tsx
import React from 'react';
import { Calendar, BookOpen, Layers, Award } from 'lucide-react';
import { Homework } from '../../types/homework';

interface HomeworkCardProps {
  homework: Homework;
  onClick?: () => void;
  actions?: React.ReactNode;
}

export const HomeworkCard: React.FC<HomeworkCardProps> = ({ homework, onClick, actions }) => {
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer flex flex-col justify-between"
    >
      <div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-1">{homework.title}</h3>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 shrink-0">
            Due: {homework.due_date}
          </span>
        </div>
        <p className="text-sm text-gray-600 mt-2 line-clamp-2">{homework.description}</p>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <BookOpen className="w-3.5 h-3.5" /> Subject ID: {homework.subject_id}
          </span>
          <span className="flex items-center gap-1">
            <Layers className="w-3.5 h-3.5" /> Grade/Sec: {homework.grade_id}-{homework.section_id}
          </span>
        </div>
        {actions && <div onClick={e => e.stopPropagation()} className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
};

export default HomeworkCard;