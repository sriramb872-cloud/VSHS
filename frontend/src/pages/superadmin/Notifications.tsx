// src/pages/superadmin/Notifications.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { Bell, CheckCheck } from 'lucide-react';
import { LoadingSkeleton, EmptyState, ErrorState } from '../../components/shared';
import { notificationService } from '../../services/notification';
import { Notification } from '../../types';

export const SuperAdminNotifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await notificationService.listNotifications();
      setNotifications(data.items);
      setUnreadCount(data.unread_count);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchNotifications(); }, [fetchNotifications]);

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await notificationService.markAllAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // silent
    } finally {
      setMarkingAll(false);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await notificationService.markAsRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      // silent
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Notifications</h1>
          {unreadCount > 0 && <p className="text-xs text-indigo-600 font-semibold">{unreadCount} unread</p>}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            disabled={markingAll}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-indigo-50 text-indigo-700 text-xs font-semibold hover:bg-indigo-100 disabled:opacity-60"
          >
            <CheckCheck className="w-4 h-4" />
            {markingAll ? 'Marking...' : 'Mark All Read'}
          </button>
        )}
      </div>

      {error && <ErrorState title="Load Error" message="Failed to load notifications" onRetry={fetchNotifications} />}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : notifications.length === 0 ? (
        <EmptyState
          title="No Notifications"
          description="You're all caught up!"
          icon={<Bell className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`bg-white rounded-xl border p-4 cursor-pointer transition-all ${
                n.is_read ? 'border-slate-200' : 'border-indigo-200 bg-indigo-50/30'
              }`}
              onClick={() => !n.is_read && handleMarkRead(n.id)}
            >
              <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${n.is_read ? 'bg-slate-100' : 'bg-indigo-100'}`}>
                  <Bell className={`w-4 h-4 ${n.is_read ? 'text-slate-400' : 'text-indigo-600'}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-semibold ${n.is_read ? 'text-slate-700' : 'text-slate-900'}`}>{n.title}</p>
                  {(n.message || n.body) && <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.message || n.body}</p>}
                  {n.created_at && <p className="text-xs text-slate-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>}
                </div>
                {!n.is_read && <div className="w-2 h-2 bg-indigo-500 rounded-full flex-shrink-0 mt-1" />}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminNotifications;