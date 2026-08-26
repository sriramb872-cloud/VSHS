// src/pages/teacher/Notifications.tsx
import React, { useState, useEffect } from 'react';
import { Bell, Plus, Trash2, Users, School, Globe, CheckCircle, AlertCircle, UserCheck } from 'lucide-react';
import { EmptyState, LoadingSkeleton } from '../../components/shared';
import { notificationService } from '../../services/notification';
import { Notification, NotificationType, TeacherClassInfo } from '../../types/notification';

export const TeacherNotifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('ALL');

  // Teacher Class Info
  const [classInfo, setClassInfo] = useState<TeacherClassInfo>({
    is_class_teacher: false,
    students: [],
  });

  // Modal State
  const [showModal, setShowModal] = useState<boolean>(false);
  const [creating, setCreating] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [title, setTitle] = useState<string>('');
  const [message, setMessage] = useState<string>('');
  const [notificationType, setNotificationType] = useState<NotificationType>('PUBLIC');
  const [targetStudentId, setTargetStudentId] = useState<string>('');

  const fetchNotifications = () => {
    setLoading(true);
    const params = activeTab !== 'ALL' ? { category: activeTab } : undefined;
    notificationService
      .listNotifications(params)
      .then((data) => setNotifications(data.items))
      .catch(() => setError('Failed to load notifications'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchNotifications();
  }, [activeTab]);

  useEffect(() => {
    notificationService
      .getTeacherClassInfo()
      .then((info) => {
        setClassInfo(info);
        if (info.is_class_teacher) {
          setNotificationType('ONLY_FOR_CLASS');
        } else {
          setNotificationType('PUBLIC');
        }
      })
      .catch((err) => console.error('Failed to load teacher class info', err));
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!title.trim() || !message.trim()) {
      setFormError('Title and message are required.');
      return;
    }

    if (notificationType === 'ONLY_FOR_CLASS' && !classInfo.is_class_teacher) {
      setFormError('You are not assigned as a Class Teacher.');
      return;
    }

    if (notificationType === 'ONLY_FOR_STUDENT') {
      if (!classInfo.is_class_teacher) {
        setFormError('You are not assigned as a Class Teacher.');
        return;
      }
      if (!targetStudentId) {
        setFormError('Please select a student.');
        return;
      }
    }

    try {
      setCreating(true);
      await notificationService.createNotification({
        title: title.trim(),
        message: message.trim(),
        notification_type: notificationType,
        target_class_id:
          notificationType === 'ONLY_FOR_CLASS' || notificationType === 'ONLY_FOR_STUDENT'
            ? classInfo.section_id || null
            : null,
        target_student_id: notificationType === 'ONLY_FOR_STUDENT' ? Number(targetStudentId) : null,
      });

      setTitle('');
      setMessage('');
      setTargetStudentId('');
      setShowModal(false);
      setSuccessMessage('Notification sent successfully.');
      setTimeout(() => setSuccessMessage(null), 4000);
      fetchNotifications();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to send notification.');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this notification?')) return;
    try {
      await notificationService.deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch {
      setError('Failed to delete notification.');
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'PUBLIC':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Globe className="w-3 h-3" /> Public
          </span>
        );
      case 'STAFF_ONLY':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Users className="w-3 h-3" /> Staff Only
          </span>
        );
      case 'ONLY_FOR_CLASS':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            <School className="w-3 h-3" /> Only for Class
          </span>
        );
      case 'ONLY_FOR_STUDENT':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <UserCheck className="w-3 h-3" /> Student Specific
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {type}
          </span>
        );
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Notifications & Announcements</h1>
          <p className="text-xs text-slate-500">
            {classInfo.is_class_teacher
              ? `Class Teacher for: ${classInfo.grade_name ? classInfo.grade_name + ' - ' : ''}${classInfo.section_name}`
              : 'View received alerts and send public or class announcements'}
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="h-10 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-xs font-bold flex items-center gap-2 shadow-xs transition-all flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
          Send Notification
        </button>
      </div>

      {successMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-600" />
          {successMessage}
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        {[
          { key: 'ALL', label: 'All' },
          { key: 'PUBLIC', label: 'Public' },
          { key: 'STAFF', label: 'Staff Only' },
          { key: 'CLASS_TEACHER', label: 'Class Teacher' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === tab.key
                ? 'bg-blue-600 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Notifications List */}
      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : notifications.length === 0 ? (
        <EmptyState
          title="No Notifications"
          description="No notifications found in this category."
          icon={<Bell className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((notif) => (
            <div
              key={notif.id}
              className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs hover:border-blue-200 transition-all flex flex-col sm:flex-row items-start justify-between gap-3"
            >
              <div className="flex items-start gap-3.5 flex-1 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bell className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    {getTypeBadge(notif.notification_type)}
                    {notif.target_class_name && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                        Class: {notif.target_class_name}
                      </span>
                    )}
                    {notif.target_student_name && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                        Student: {notif.target_student_name}
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{notif.title}</h3>
                  <p className="text-xs text-slate-600 mt-1 whitespace-pre-line leading-relaxed">
                    {notif.message}
                  </p>
                  <div className="flex items-center gap-3 mt-2.5 text-[11px] text-slate-400">
                    <span>From: {notif.sender_name || notif.sender_role || 'Staff'}</span>
                    <span>•</span>
                    <span>{new Date(notif.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              {/* Teachers can delete notifications they sent */}
              {notif.sender_role === 'TEACHER' && (
                <button
                  onClick={() => handleDelete(notif.id)}
                  className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all self-end sm:self-center"
                  title="Delete Notification"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Notification Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900">Create Teacher Notification</h2>
              <button
                onClick={() => {
                  setShowModal(false);
                  setFormError(null);
                }}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {!classInfo.is_class_teacher && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <span>
                  You are not currently assigned as a Class Teacher. Only Public announcements can be published.
                </span>
              </div>
            )}

            {formError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-3.5">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Notification Type
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    disabled={!classInfo.is_class_teacher}
                    onClick={() => {
                      setNotificationType('ONLY_FOR_CLASS');
                      setTargetStudentId('');
                    }}
                    className={`py-2 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1 transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                      notificationType === 'ONLY_FOR_CLASS'
                        ? 'border-indigo-600 bg-indigo-50 text-indigo-800 ring-2 ring-indigo-500/20'
                        : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <School className="w-4 h-4" />
                    Only for Class
                  </button>

                  <button
                    type="button"
                    disabled={!classInfo.is_class_teacher}
                    onClick={() => setNotificationType('ONLY_FOR_STUDENT')}
                    className={`py-2 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1 transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                      notificationType === 'ONLY_FOR_STUDENT'
                        ? 'border-amber-600 bg-amber-50 text-amber-800 ring-2 ring-amber-500/20'
                        : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <UserCheck className="w-4 h-4" />
                    Only a Student
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setNotificationType('PUBLIC');
                      setTargetStudentId('');
                    }}
                    className={`py-2 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1 transition-all ${
                      notificationType === 'PUBLIC'
                        ? 'border-emerald-600 bg-emerald-50 text-emerald-800 ring-2 ring-emerald-500/20'
                        : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <Globe className="w-4 h-4" />
                    Public
                  </button>
                </div>

                <p className="text-[11px] text-slate-500 mt-1.5">
                  {notificationType === 'ONLY_FOR_CLASS' &&
                    `Audience: All students in your assigned class (${classInfo.section_name || 'Class'}).`}
                  {notificationType === 'ONLY_FOR_STUDENT' &&
                    'Audience: One specific student enrolled in your class.'}
                  {notificationType === 'PUBLIC' &&
                    'Audience: General public announcement across the school.'}
                </p>
              </div>

              {/* Assigned Class Indicator for Class Notifications */}
              {notificationType === 'ONLY_FOR_CLASS' && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                  <span className="text-xs text-slate-500 block">Assigned Class:</span>
                  <span className="text-xs font-bold text-slate-900">
                    {classInfo.grade_name ? `${classInfo.grade_name} - ` : ''}
                    {classInfo.section_name || 'Assigned Class'}
                  </span>
                </div>
              )}

              {/* Student Selector (Only shown for Only for a Student) */}
              {notificationType === 'ONLY_FOR_STUDENT' && (
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Select Student ({classInfo.section_name}) <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={targetStudentId}
                    onChange={(e) => setTargetStudentId(e.target.value)}
                    required
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
                  >
                    <option value="">Select Student</option>
                    {classInfo.students.map((st) => (
                      <option key={st.student_id} value={st.student_id}>
                        {st.full_name} {st.roll_number ? `(Roll: ${st.roll_number})` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Title <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Notification title..."
                  required
                  className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Message Body <span className="text-rose-500">*</span>
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Write message details..."
                  rows={4}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold hover:bg-slate-200 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all disabled:opacity-50"
                >
                  {creating ? 'Sending...' : 'Send Notification'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherNotifications;