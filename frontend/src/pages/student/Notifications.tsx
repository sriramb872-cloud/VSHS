// src/pages/student/Notifications.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Globe, School, UserCheck, CheckCheck, ClipboardCheck } from 'lucide-react';
import { EmptyState, LoadingSkeleton } from '../../components/shared';
import { notificationService } from '../../services/notification';
import { Notification, NotificationCategory } from '../../types/notification';

/**
 * `SLIP_TEST` is a fourth, feature-specific category (see
 * `app/services/slip_test.py`). Rows tagged with it carry the slip test id in
 * `reference_id`, which is what makes the deep link unambiguous - no guessing
 * about what an id refers to.
 */
const SLIP_TEST_CATEGORY = 'SLIP_TEST';

type StudentCategory = Extract<NotificationCategory, 'PUBLIC' | 'CLASS' | 'CLASS_TEACHER'> | typeof SLIP_TEST_CATEGORY;

const CATEGORY_LABELS: Record<StudentCategory, string> = {
  PUBLIC: 'Public',
  CLASS: 'Class',
  CLASS_TEACHER: 'Class Teacher',
  SLIP_TEST: 'Slip Tests',
};

export const StudentNotifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<StudentCategory>('PUBLIC');
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [markingAll, setMarkingAll] = useState<boolean>(false);
  const navigate = useNavigate();

  const isSlipTestNotification = (notif: Notification): boolean =>
    notif.category === SLIP_TEST_CATEGORY || notif.notification_type === SLIP_TEST_CATEGORY;

  const fetchNotifications = (cat: StudentCategory) => {
    setLoading(true);
    setError(null);
    notificationService
      .listNotifications({ category: cat })
      .then((data) => {
        // The server narrows this category exactly (crud/notification.py has a
        // dedicated SLIP_TEST branch); the extra filter is belt-and-braces for
        // the uncategorised path, not a security boundary.
        const items = (data.items || []).filter(
          (n) => (cat === SLIP_TEST_CATEGORY) === isSlipTestNotification(n),
        );
        setNotifications(items);
        setUnreadCount(data.unread_count ?? 0);
      })
      .catch(() => setError('Failed to load notifications'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchNotifications(activeCategory);
  }, [activeCategory]);

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await notificationService.markAllAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      setError('Failed to mark notifications as read');
    } finally {
      setMarkingAll(false);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await notificationService.markAsRead(id);
      setNotifications(prev => prev.map(n => (n.id === id ? { ...n, is_read: true } : n)));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      setError('Failed to mark notification as read');
    }
  };

  /** Tapping a slip test notice marks it read, then opens the detail screen. */
  const handleSlipTestClick = async (notif: Notification) => {
    if (!notif.is_read) await handleMarkRead(notif.id);
    if (notif.reference_id != null) navigate(`/student/slip-tests/${notif.reference_id}`);
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'PUBLIC':
        return <Globe className="w-4 h-4 text-emerald-600" />;
      case 'CLASS':
        return <School className="w-4 h-4 text-[var(--brand)]" />;
      case 'CLASS_TEACHER':
        return <UserCheck className="w-4 h-4 text-[var(--brand)]" />;
      case SLIP_TEST_CATEGORY:
        return <ClipboardCheck className="w-4 h-4 text-[var(--brand)]" />;
      default:
        return <Bell className="w-4 h-4 text-slate-500" />;
    }
  };

  const getCategoryBadge = (category: string, type: string) => {
    if (category === SLIP_TEST_CATEGORY || type === SLIP_TEST_CATEGORY) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-50 text-sky-700 border border-sky-200">
          <ClipboardCheck className="w-3 h-3" /> Slip Test
        </span>
      );
    }
    if (category === 'PUBLIC' || type === 'PUBLIC') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <Globe className="w-3 h-3" /> Public
        </span>
      );
    }
    if (category === 'CLASS' || type === 'CLASS_ONLY') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[var(--brand-light)] text-[var(--brand-strong)] border border-[var(--brand-border)]">
          <School className="w-3 h-3" /> Class
        </span>
      );
    }
    if (category === 'CLASS_TEACHER' || type === 'ONLY_FOR_CLASS' || type === 'ONLY_FOR_STUDENT') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[var(--brand-light)] text-[var(--brand-strong)] border border-[var(--brand-border)]">
          <UserCheck className="w-3 h-3" /> Class Teacher
        </span>
      );
    }
    return null;
  };

  const categories: StudentCategory[] = ['PUBLIC', 'CLASS', 'CLASS_TEACHER', SLIP_TEST_CATEGORY];
  const CategoryIcon: Record<string, React.ReactNode> = {
    PUBLIC: <Globe className="w-3.5 h-3.5" />,
    CLASS: <School className="w-3.5 h-3.5" />,
    CLASS_TEACHER: <UserCheck className="w-3.5 h-3.5" />,
    [SLIP_TEST_CATEGORY]: <ClipboardCheck className="w-3.5 h-3.5" />,
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Notifications & Announcements</h1>
          <p className="text-xs text-slate-500">Read school alerts, class notices, and updates from your class teacher</p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            disabled={markingAll}
            className="self-start flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[var(--brand-light)] text-[var(--brand-strong)] text-xs font-semibold hover:bg-[var(--brand-light)] disabled:opacity-60"
          >
            <CheckCheck className="w-4 h-4" />
            {markingAll ? 'Marking...' : 'Mark All Read'}
          </button>
        )}
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {/* 4 categories for the Student Portal. Scrollable so all four fit at
          360px without a page-level horizontal scrollbar. */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 overflow-x-auto no-scrollbar">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`flex items-center gap-1.5 px-3 sm:px-4 py-2 rounded-xl text-xs font-bold whitespace-nowrap flex-shrink-0 transition-all ${
              activeCategory === cat
                ? 'bg-[var(--brand)] text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {CategoryIcon[cat]}
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Content list */}
      {loading ? (
        <LoadingSkeleton type="list" count={3} />
      ) : notifications.length === 0 ? (
        <EmptyState
          title={`No ${CATEGORY_LABELS[activeCategory]} Notifications`}
          description="You're all caught up! There are no notifications in this category."
          icon={<Bell className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((notif) => {
            const isSlipTest = isSlipTestNotification(notif);
            return (
              <div
                key={notif.id}
                role={isSlipTest && notif.reference_id != null ? 'button' : undefined}
                tabIndex={isSlipTest && notif.reference_id != null ? 0 : undefined}
                onClick={() => (isSlipTest ? handleSlipTestClick(notif) : !notif.is_read && handleMarkRead(notif.id))}
                onKeyDown={
                  isSlipTest && notif.reference_id != null
                    ? (e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          handleSlipTestClick(notif);
                        }
                      }
                    : undefined
                }
                className={`bg-white border rounded-2xl p-4 shadow-xs transition-all flex items-start gap-3.5 ${
                  notif.is_read
                    ? 'border-slate-200/80 hover:border-[var(--brand-border)]'
                    : 'border-[var(--brand-border)] bg-[var(--brand-light)]/30 hover:border-[var(--brand-border)]'
                } ${isSlipTest ? 'cursor-pointer' : !notif.is_read ? 'cursor-pointer' : ''}`}
              >
                <div className="w-10 h-10 rounded-xl bg-[var(--brand-light)] flex items-center justify-center flex-shrink-0 mt-0.5">
                  {getCategoryIcon(notif.category || notif.notification_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    {getCategoryBadge(notif.category || '', notif.notification_type)}
                    {notif.target_class_name && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-[var(--brand-light)] text-[var(--brand-strong)] border border-[var(--brand-border)]">
                        Class: {notif.target_class_name}
                      </span>
                    )}
                    {isSlipTest && (
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                        Tap to open
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
            );
          })}
        </div>
      )}
    </div>
  );
};

export default StudentNotifications;