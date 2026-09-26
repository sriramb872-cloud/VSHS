// src/pages/principal/Subjects.tsx
import React, { useState, useEffect } from 'react';
import { BookOpen, Plus } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton } from '../../components/shared';
import { EditModal, ConfirmDialog } from '../../components/EditModal';
import { subjectsService } from '../../services/subjects';
import { Subject } from '../../types';

export const Subjects: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [editingSubject, setEditingSubject] = useState<Subject | null>(null);
  const [deletingSubject, setDeletingSubject] = useState<Subject | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [subjectName, setSubjectName] = useState('');

  useEffect(() => {
    subjectsService
      .listSubjects()
      .then(setSubjects)
      .catch(() => setError('Failed to load subjects'))
      .finally(() => setLoading(false));
  }, []);

  const handleCreateSubject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subjectName.trim()) return;
    subjectsService
      .createSubject({ name: subjectName.trim() })
      .then(newSubject => {
        setSubjects(prev => [...prev, newSubject]);
        setSubjectName('');
      })
      .catch(() => setError('Failed to create subject'));
  };
  const updateSubject = (subject: Subject) => {
    setEditingSubject(subject);
  };
  const removeSubject = (subject: Subject) => {
    setDeletingSubject(subject);
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Subjects Curriculum</h1>
        <p className="text-xs text-slate-500">Academic subject catalog</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Add Subject</h3>
        <form onSubmit={handleCreateSubject} className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            className="flex-1 h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            value={subjectName}
            onChange={(e) => setSubjectName(e.target.value)}
            placeholder="e.g. Mathematics"
            required
          />
          <button
            type="submit"
            className="h-11 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Create Subject</span>
          </button>
        </form>
      </div>

      {loading ? (
        <LoadingSkeleton type="list" count={3} />
      ) : subjects.length === 0 ? (
        <EmptyState
          title="No Subjects Configured"
          description="Create your first subject in the catalog above."
          icon={<BookOpen className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {subjects.map((sub) => (
            <MobileListItem
              key={sub.id}
              title={sub.name}
              icon={<BookOpen className="w-5 h-5 text-emerald-600" />}
              avatarBg="bg-emerald-50 text-emerald-600"
              actions={<div className="flex gap-1" onClick={event => event.stopPropagation()}><button type="button" className="text-xs text-indigo-700" onClick={() => updateSubject(sub)}>Edit</button><button type="button" className="text-xs text-rose-700" onClick={() => removeSubject(sub)}>Archive</button></div>}
            />
          ))}
        </div>
      )}

      {editingSubject && (
        <EditModal
          title="Edit Subject"
          fields={[
            { key: 'name', label: 'Subject Name', required: true },
          ]}
          initialValues={{
            name: editingSubject.name,
          }}
          onSubmit={async (values) => {
            const updated = await subjectsService.updateSubject(editingSubject.id, { name: values.name.trim() });
            setSubjects(items => items.map(item => (item.id === editingSubject.id ? updated : item)));
            setEditingSubject(null);
          }}
          onClose={() => setEditingSubject(null)}
        />
      )}

      {deletingSubject && (
        <ConfirmDialog
          title="Archive Subject"
          message={`Are you sure you want to archive ${deletingSubject.name}? This is allowed only when it has no active dependencies.`}
          confirmLabel="Archive"
          confirmVariant="danger"
          onConfirm={async () => {
            await subjectsService.deleteSubject(deletingSubject.id);
            setSubjects(items => items.filter(item => item.id !== deletingSubject.id));
          }}
          onClose={() => setDeletingSubject(null)}
        />
      )}
    </div>
  );
};

export default Subjects;
