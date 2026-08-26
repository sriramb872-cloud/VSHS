// src/components/announcement/index.tsx
import React from 'react';
import { Announcement } from '../../types/announcement';
import { Bell, Calendar, Shield, AlertCircle } from 'lucide-react';

interface AnnouncementCardProps {
  announcement: Announcement;
  onRead?: (id: number) => void;
  onPublish?: (id: number) => void;
  onDelete?: (id: number) => void;
  isPrincipalOrAuthor?: boolean;
}

export const AnnouncementCard: React.FC<AnnouncementCardProps> = ({
  announcement,
  onRead,
  onPublish,
  onDelete,
  isPrincipalOrAuthor,
}) => {
  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'Urgent':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'High':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'Normal':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm space-y-4">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 text-indigo-700">
              {announcement.audience}
            </span>
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${getPriorityBadge(announcement.priority)}`}>
              {announcement.priority}
            </span>
            <span className="text-xs text-gray-400">• Status: {announcement.status}</span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 pt-1">{announcement.title}</h3>
        </div>
      </div>

      <p className="text-sm text-gray-600 whitespace-pre-line">{announcement.description}</p>

      <div className="flex flex-wrap items-center justify-between text-xs text-gray-500 pt-4 border-t border-gray-100 gap-2">
        <span className="flex items-center gap-1">
          <Calendar className="w-3.5 h-3.5 text-gray-400" /> Published: {new Date(announcement.publish_date).toLocaleDateString()}
        </span>

        <div className="flex items-center gap-2">
          {onPublish && announcement.status === 'Draft' && (
            <button
              onClick={() => onPublish(announcement.id)}
              className="px-3 py-1 bg-indigo-600 text-white rounded text-xs font-medium hover:bg-indigo-700"
            >
              Publish
            </button>
          )}
          {onRead && (
            <button
              onClick={() => onRead(announcement.id)}
              className="px-3 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium hover:bg-gray-200"
            >
              Mark as Read
            </button>
          )}
          {isPrincipalOrAuthor && onDelete && (
            <button
              onClick={() => onDelete(announcement.id)}
              className="px-3 py-1 bg-red-50 text-red-600 rounded text-xs font-medium hover:bg-red-100"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnnouncementCard;