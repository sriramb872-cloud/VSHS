// src/pages/principal/Notifications.tsx
import React, { useState, useEffect } from 'react';
import { Bell, Plus, Trash2, Users, School, Globe, CheckCircle } from 'lucide-react';
import { EmptyState, LoadingSkeleton } from '../../components/shared';
import { notificationService } from '../../services/notification';
import { sectionsService } from '../../services/sections';
import { Notification, NotificationType } from '../../types/notification';
import { Section } from '../../types';

export const Notifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('ALL');

  // Form State
  const [showModal, setShowModal] = useState<boolean>(false);
  const [creating, setCreating] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [title, setTitle] = useState<string>('');
  const [message, setMessage] = useState<string>('');
  const [notificationType, setNotificationType] = useState<NotificationType>('PUBLIC');
  const [targetClassId, setTargetClassId] = useState<string>('');

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
    // Fetch sections for Class Only selector
    sectionsService
      .listSections()
      .then((data) => setSections(data || []))
      .catch((err) => console.error('Failed to load sections', err));
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!title.trim() || !message.trim()) {
      setFormError('Title and message are required.');
      return;
    }

    if (notificationType === 'CLASS_ONLY' && !targetClassId) {
      setFormError('Please select a target class.');
      return;
    }

    try {
      setCreating(true);
      await notificationService.createNotification({
        title: title.trim(),
        message: message.trim(),
        notification_type: notificationType,
        target_class_id: notificationType === 'CLASS_ONLY' ? Number(targetClassId) : null,
        target_student_id: null,
      });

      setTitle('');
      setMessage('');
      setNotificationType('PUBLIC');
      setTargetClassId('');
      setShowModal(false);
      setSuccessMessage('Notification published successfully.');
      setTimeout(() => setSuccessMessage(null), 4000);
      fetchNotifications();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to create notification.');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this notification?')) return;
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
      case 'CLASS_ONLY':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <School className="w-3 h-3" /> Class Only
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
          <p className="text-xs text-slate-500">Manage broadcasts to staff, students, or specific classes</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="h-10 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-bold flex items-center gap-2 shadow-xs transition-all flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
          Create Notification
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
          { key: 'CLASS', label: 'Class Only' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === tab.key
                ? 'bg-emerald-600 text-white'
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
          description="No notifications found in this view. Click 'Create Notification' to broadcast one."
          icon={<Bell className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((notif) => (
            <div
              key={notif.id}
              className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs hover:border-emerald-200 transition-all flex flex-col sm:flex-row items-start justify-between gap-3"
            >
              <div className="flex items-start gap-3.5 flex-1 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bell className="w-5 h-5 text-emerald-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    {getTypeBadge(notif.notification_type)}
                    {notif.target_class_name && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
                        Class: {notif.target_class_name}
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{notif.title}</h3>
                  <p className="text-xs text-slate-600 mt-1 whitespace-pre-line leading-relaxed">
                    {notif.message}
                  </p>
                  <div className="flex items-center gap-3 mt-2.5 text-[11px] text-slate-400">
                    <span>By: {notif.sender_name || notif.sender_role || 'Principal'}</span>
                    <span>•</span>
                    <span>{new Date(notif.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDelete(notif.id)}
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all self-end sm:self-center"
                title="Delete Notification"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create Notification Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900">Create Principal Notification</h2>
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
                    onClick={() => {
                      setNotificationType('PUBLIC');
                      setTargetClassId('');
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
                  <button
                    type="button"
                    onClick={() => {
                      setNotificationType('STAFF_ONLY');
                      setTargetClassId('');
                    }}
                    className={`py-2 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1 transition-all ${
                      notificationType === 'STAFF_ONLY'
                        ? 'border-blue-600 bg-blue-50 text-blue-800 ring-2 ring-blue-500/20'
                        : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <Users className="w-4 h-4" />
                    Staff Only
                  </button>
                  <button
                    type="button"
                    onClick={() => setNotificationType('CLASS_ONLY')}
                    className={`py-2 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1 transition-all ${
                      notificationType === 'CLASS_ONLY'
                        ? 'border-purple-600 bg-purple-50 text-purple-800 ring-2 ring-purple-500/20'
                        : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <School className="w-4 h-4" />
                    Class Only
                  </button>
                </div>
                <p className="text-[11px] text-slate-500 mt-1.5">
                  {notificationType === 'PUBLIC' && 'Audience: All teachers/staff and all students across the school.'}
                  {notificationType === 'STAFF_ONLY' && 'Audience: All teachers/staff only. Students will never see this.'}
                  {notificationType === 'CLASS_ONLY' && 'Audience: All students in the selected class only.'}
                </p>
              </div>

              {/* Class Selector (Only shown for Class Only) */}
              {notificationType === 'CLASS_ONLY' && (
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Target Class / Section <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={targetClassId}
                    onChange={(e) => setTargetClassId(e.target.value)}
                    required
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none bg-white"
                  >
                    <option value="">Select a Class / Section</option>
                    {sections.map((sec) => (
                      <option key={sec.id} value={sec.id}>
                        {sec.name ? sec.name : `Section #${sec.id}`}
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
                  className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
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
                  className="w-full px-4 py-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none resize-none"
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
                  className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all disabled:opacity-50"
                >
                  {creating ? 'Publishing...' : 'Publish Notification'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Notifications;