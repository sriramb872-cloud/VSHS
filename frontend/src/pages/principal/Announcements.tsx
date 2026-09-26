// src/pages/principal/Announcements.tsx
import React, { useEffect, useState } from 'react';
import { Megaphone, Plus, Edit2, Send, Archive, Trash2 } from 'lucide-react';
import { announcementService } from '../../services/announcement';
import { gradesService } from '../../services/grades';
import { sectionsService } from '../../services/sections';
import { academicYearsService } from '../../services/academicYears';
import { Announcement, Grade, Section, AcademicYear } from '../../types';
import { SelectableAnnouncementAudience } from '../../types/announcement';
import { ConfirmDialog, EditModal, Field } from '../../components/EditModal';
import { StatusBadge } from '../../components/shared';

export const PrincipalAnnouncementsPage: React.FC = () => {
  const [items, setItems] = useState<Announcement[]>([]);
  const [grades, setGrades] = useState<Grade[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [audience, setAudience] = useState<SelectableAnnouncementAudience>('School-Wide');
  const [gradeId, setGradeId] = useState<number | ''>('');
  const [sectionId, setSectionId] = useState<number | ''>('');
  const [priority, setPriority] = useState<string>('Normal');
  const [publishDate, setPublishDate] = useState<string>(() => {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  });
  const [expiryDate, setExpiryDate] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  // Edit / Delete Dialog State
  const [editingItem, setEditingItem] = useState<Announcement | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [annResult, gList, sList, ayList] = await Promise.all([
        announcementService.listAnnouncements(),
        gradesService.listGrades().catch(() => []),
        sectionsService.listSections().catch(() => []),
        academicYearsService.listAcademicYears().catch(() => []),
      ]);
      setItems(annResult.items || []);
      setGrades(gList);
      setSections(sList);
      setAcademicYears(ayList);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load announcements.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const currentAcademicYear = academicYears.find(ay => ay.is_current) || academicYears[0];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload: any = {
        title: title.trim(),
        description: description.trim(),
        audience,
        grade_id: (audience === 'Grade' || audience === 'Section') && gradeId ? Number(gradeId) : undefined,
        section_id: audience === 'Section' && sectionId ? Number(sectionId) : undefined,
        academic_year_id: currentAcademicYear?.id,
        priority,
        publish_date: new Date(publishDate).toISOString(),
        expiry_date: expiryDate ? new Date(expiryDate).toISOString() : undefined,
        status: 'Draft',
      };
      const created = await announcementService.createAnnouncement(payload);
      setItems(current => [created, ...current]);
      setTitle('');
      setDescription('');
      setAudience('School-Wide');
      setGradeId('');
      setSectionId('');
      setPriority('Normal');
      setExpiryDate('');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create announcement.');
    } finally {
      setSubmitting(false);
    }
  };

  const handlePublish = async (id: number) => {
    try {
      const updated = await announcementService.publishAnnouncement(id);
      setItems(current => current.map(item => (item.id === id ? updated : item)));
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to publish announcement.');
    }
  };

  const handleArchive = async (id: number) => {
    try {
      const updated = await announcementService.archiveAnnouncement(id);
      setItems(current => current.map(item => (item.id === id ? updated : item)));
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to archive announcement.');
    }
  };

  const handleDelete = async () => {
    if (!deletingId) return;
    try {
      await announcementService.deleteAnnouncement(deletingId);
      setItems(current => current.filter(item => item.id !== deletingId));
      setDeletingId(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to delete announcement.');
    }
  };

  const editFields: Field[] = [
    { key: 'title', label: 'Title', type: 'text', required: true },
    { key: 'description', label: 'Description', type: 'textarea', required: true },
    {
      key: 'audience',
      label: 'Audience',
      type: 'select',
      required: true,
      options: [
        { value: 'School-Wide', label: 'School-Wide' },
        { value: 'Teachers', label: 'Teachers' },
        { value: 'Students', label: 'Students' },
        { value: 'Grade', label: 'Grade' },
        { value: 'Section', label: 'Section' },
      ],
    },
    {
      key: 'grade_id',
      label: 'Grade',
      type: 'select',
      options: grades.map(g => ({ value: g.id, label: g.name })),
    },
    {
      key: 'section_id',
      label: 'Section',
      type: 'select',
      options: sections.map(s => ({ value: s.id, label: `${s.name} (Grade ${s.grade_id})` })),
    },
    {
      key: 'priority',
      label: 'Priority',
      type: 'select',
      options: [
        { value: 'Low', label: 'Low' },
        { value: 'Normal', label: 'Normal' },
        { value: 'High', label: 'High' },
        { value: 'Urgent', label: 'Urgent' },
      ],
    },
  ];

  const filteredSections = gradeId
    ? sections.filter(s => s.grade_id === Number(gradeId))
    : sections;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Announcements</h1>
        <p className="text-xs text-slate-500">Create, publish, and manage school announcements</p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">
          {error}
        </div>
      )}

      {/* Create Announcement Form */}
      <form onSubmit={handleCreate} className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3 shadow-xs">
        <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
          <Megaphone className="w-4 h-4 text-indigo-600" /> New Announcement
        </h2>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-600">Title</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Announcement Title"
            className="w-full rounded-lg border border-slate-200 p-2 text-sm"
            required
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-600">Description</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Announcement details..."
            rows={3}
            className="w-full rounded-lg border border-slate-200 p-2 text-sm"
            required
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="text-xs font-semibold text-slate-600">Audience</label>
            <select
              value={audience}
              onChange={e => setAudience(e.target.value as SelectableAnnouncementAudience)}
              className="w-full rounded-lg border border-slate-200 p-2 text-sm"
            >
              <option value="School-Wide">School-Wide</option>
              <option value="Teachers">Teachers</option>
              <option value="Students">Students</option>
              <option value="Grade">Grade</option>
              <option value="Section">Section</option>
            </select>
          </div>

          {(audience === 'Grade' || audience === 'Section') && (
            <div>
              <label className="text-xs font-semibold text-slate-600">Grade</label>
              <select
                value={gradeId}
                onChange={e => {
                  setGradeId(e.target.value ? Number(e.target.value) : '');
                  setSectionId('');
                }}
                className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                required
              >
                <option value="">Select Grade...</option>
                {grades.map(g => (
                  <option key={g.id} value={g.id}>{g.name}</option>
                ))}
              </select>
            </div>
          )}

          {audience === 'Section' && (
            <div>
              <label className="text-xs font-semibold text-slate-600">Section</label>
              <select
                value={sectionId}
                onChange={e => setSectionId(e.target.value ? Number(e.target.value) : '')}
                className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                required
              >
                <option value="">Select Section...</option>
                {filteredSections.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-slate-600">Priority</label>
            <select
              value={priority}
              onChange={e => setPriority(e.target.value)}
              className="w-full rounded-lg border border-slate-200 p-2 text-sm"
            >
              <option value="Low">Low</option>
              <option value="Normal">Normal</option>
              <option value="High">High</option>
              <option value="Urgent">Urgent</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600">Publish Date</label>
            <input
              type="datetime-local"
              value={publishDate}
              onChange={e => setPublishDate(e.target.value)}
              className="w-full rounded-lg border border-slate-200 p-2 text-sm"
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600">Expiry Date (Optional)</label>
            <input
              type="datetime-local"
              value={expiryDate}
              onChange={e => setExpiryDate(e.target.value)}
              className="w-full rounded-lg border border-slate-200 p-2 text-sm"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Plus className="w-3.5 h-3.5" />
            {submitting ? 'Creating…' : 'Create Announcement'}
          </button>
        </div>
      </form>

      {/* Announcements List */}
      <div className="space-y-3">
        {loading ? (
          <p className="text-xs text-slate-500">Loading announcements…</p>
        ) : items.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-xs text-slate-500">
            No announcements found.
          </div>
        ) : (
          items.map(item => (
            <article key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="font-semibold text-slate-900 text-sm">{item.title}</h2>
                  <p className="text-xs text-slate-500">
                    Audience: <span className="font-medium text-slate-700">{item.audience || 'School-Wide'}</span>
                    {item.grade_id ? ` · Grade #${item.grade_id}` : ''}
                    {item.section_id ? ` · Section #${item.section_id}` : ''}
                    {item.created_at ? ` · ${new Date(item.created_at).toLocaleDateString()}` : ''}
                  </p>
                </div>
                <StatusBadge status={item.status || 'Draft'} />
              </div>

              <p className="text-xs text-slate-600 whitespace-pre-line">
                {item.description || item.content || item.message}
              </p>

              <div className="flex items-center gap-2 pt-2 border-t border-slate-100 text-xs">
                <button
                  onClick={() => setEditingItem(item)}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 font-medium"
                >
                  <Edit2 className="w-3 h-3" /> Edit
                </button>
                {item.status !== 'Published' && (
                  <button
                    onClick={() => handlePublish(item.id)}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-emerald-200 text-emerald-700 hover:bg-emerald-50 font-medium"
                  >
                    <Send className="w-3 h-3" /> Publish
                  </button>
                )}
                {item.status !== 'Archived' && (
                  <button
                    onClick={() => handleArchive(item.id)}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-amber-200 text-amber-700 hover:bg-amber-50 font-medium"
                  >
                    <Archive className="w-3 h-3" /> Archive
                  </button>
                )}
                <button
                  onClick={() => setDeletingId(item.id)}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50 font-medium ml-auto"
                >
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              </div>
            </article>
          ))
        )}
      </div>

      {/* Edit Announcement Modal */}
      {editingItem && (
        <EditModal
          title="Edit Announcement"
          fields={editFields}
          initialValues={{
            title: editingItem.title,
            description: editingItem.description || editingItem.content || editingItem.message || '',
            audience: editingItem.audience || 'School-Wide',
            grade_id: editingItem.grade_id || '',
            section_id: editingItem.section_id || '',
            priority: (editingItem as any).priority || 'Normal',
          }}
          onSubmit={async values => {
            const payload: any = {
              title: values.title?.trim(),
              description: values.description?.trim(),
              audience: values.audience,
              grade_id: (values.audience === 'Grade' || values.audience === 'Section') && values.grade_id ? Number(values.grade_id) : undefined,
              section_id: values.audience === 'Section' && values.section_id ? Number(values.section_id) : undefined,
              priority: values.priority,
            };
            const updated = await announcementService.updateAnnouncement(editingItem.id, payload);
            setItems(current => current.map(u => (u.id === updated.id ? updated : u)));
          }}
          onClose={() => setEditingItem(null)}
        />
      )}

      {/* Confirm Delete Dialog */}
      {deletingId && (
        <ConfirmDialog
          title="Delete Announcement"
          message="Are you sure you want to delete this announcement? This action cannot be undone."
          confirmLabel="Delete"
          confirmVariant="danger"
          onConfirm={handleDelete}
          onClose={() => setDeletingId(null)}
        />
      )}
    </div>
  );
};

export default PrincipalAnnouncementsPage;
