// src/pages/student/Notifications.tsx
import React, { useState, useEffect } from 'react';
import { Bell, Globe, School, UserCheck } from 'lucide-react';
import { EmptyState, LoadingSkeleton } from '../../components/shared';
import { notificationService } from '../../services/notification';
import { Notification, NotificationCategory } from '../../types/notification';

export const StudentNotifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<NotificationCategory>('PUBLIC');

  const fetchNotifications = (cat: NotificationCategory) => {
    setLoading(true);
    setError(null);
    notificationService
      .listNotifications({ category: cat })
      .then((data) => setNotifications(data.items || []))
      .catch(() => setError('Failed to load notifications'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchNotifications(activeCategory);
  }, [activeCategory]);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'PUBLIC':
        return <Globe className="w-4 h-4 text-emerald-600" />;
      case 'CLASS':
        return <School className="w-4 h-4 text-purple-600" />;
      case 'CLASS_TEACHER':
        return <UserCheck className="w-4 h-4 text-orange-600" />;
      default:
        return <Bell className="w-4 h-4 text-slate-500" />;
    }
  };

  const getCategoryBadge = (category: string, type: string) => {
    if (category === 'PUBLIC' || type === 'PUBLIC') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <Globe className="w-3 h-3" /> Public
        </span>
      );
    }
    if (category === 'CLASS' || type === 'CLASS_ONLY') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
          <School className="w-3 h-3" /> Class
        </span>
      );
    }
    if (category === 'CLASS_TEACHER' || type === 'ONLY_FOR_CLASS' || type === 'ONLY_FOR_STUDENT') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-50 text-orange-700 border border-orange-200">
          <UserCheck className="w-3 h-3" /> Class Teacher
        </span>
      );
    }
    return null;
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Notifications & Announcements</h1>
        <p className="text-xs text-slate-500">Read school alerts, class notices, and updates from your class teacher</p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {/* Exactly 3 categories for Student Portal */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveCategory('PUBLIC')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeCategory === 'PUBLIC'
              ? 'bg-orange-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Globe className="w-3.5 h-3.5" />
          Public
        </button>

        <button
          onClick={() => setActiveCategory('CLASS')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeCategory === 'CLASS'
              ? 'bg-orange-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <School className="w-3.5 h-3.5" />
          Class
        </button>

        <button
          onClick={() => setActiveCategory('CLASS_TEACHER')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeCategory === 'CLASS_TEACHER'
              ? 'bg-orange-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <UserCheck className="w-3.5 h-3.5" />
          Class Teacher
        </button>
      </div>

      {/* Content list */}
      {loading ? (
        <LoadingSkeleton type="list" count={3} />
      ) : notifications.length === 0 ? (
        <EmptyState
          title={`No ${
            activeCategory === 'PUBLIC'
              ? 'Public'
              : activeCategory === 'CLASS'
              ? 'Class'
              : 'Class Teacher'
          } Notifications`}
          description="You're all caught up! There are no notifications in this category."
          icon={<Bell className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((notif) => (
            <div
              key={notif.id}
              className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs hover:border-orange-200 transition-all flex items-start gap-3.5"
            >
              <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                {getCategoryIcon(notif.category || notif.notification_type)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  {getCategoryBadge(notif.category || '', notif.notification_type)}
                  {notif.target_class_name && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
                      Class: {notif.target_class_name}
                    </span>
                  )}
                  {notif.target_student_name && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                      Personal to You
                    </span>
                  )}
                </div>
                <h3 className="text-sm font-bold text-slate-900">{notif.title}</h3>
                <p className="text-xs text-slate-600 mt-1 whitespace-pre-line leading-relaxed">
                  {notif.message}
                </p>
                <div className="flex items-center gap-3 mt-2.5 text-[11px] text-slate-400">
                  <span>From: {notif.sender_name || notif.sender_role || 'School'}</span>
                  <span>•</span>
                  <span>{new Date(notif.created_at).toLocaleString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentNotifications;