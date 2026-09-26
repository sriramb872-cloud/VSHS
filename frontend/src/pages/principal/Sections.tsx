// src/pages/principal/Sections.tsx
import React, { useState, useEffect } from 'react';
import { School, Plus } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton } from '../../components/shared';
import { EditModal, ConfirmDialog } from '../../components/EditModal';
import { sectionsService } from '../../services/sections';
import { gradesService } from '../../services/grades';
import { teachersService } from '../../services/teachers';
import { Grade, Section, Teacher } from '../../types';

export const Sections: React.FC = () => {
  const [sections, setSections] = useState<Section[]>([]);
  const [grades, setGrades] = useState<Grade[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [editingSection, setEditingSection] = useState<Section | null>(null);
  const [deletingSection, setDeletingSection] = useState<Section | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sectionName, setSectionName] = useState('');
  const [gradeId, setGradeId] = useState('');

  useEffect(() => {
    Promise.all([sectionsService.listSections(), gradesService.listGrades(), teachersService.listTeachers()])
      .then(([sectionData, gradeData, teacherData]) => {
        setSections(sectionData);
        setGrades(gradeData);
        setTeachers(teacherData);
      })
      .catch(() => setError('Failed to load sections'))
      .finally(() => setLoading(false));
  }, []);

  const handleCreateSection = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sectionName.trim() || !gradeId) return;
    if (sectionName.trim().length > 10) {
      setError('Section name must be 10 characters or fewer.');
      return;
    }
    sectionsService
      .createSection({ name: sectionName.trim(), grade_id: Number(gradeId) })
      .then(newSection => {
        setSections(prev => [...prev, newSection]);
        setSectionName('');
        setGradeId('');
      })
      .catch(() => setError('Failed to create section'));
  };
  const editSection = (section: Section) => {
    setEditingSection(section);
  };
  const removeSection = (section: Section) => {
    setDeletingSection(section);
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Section Management</h1>
        <p className="text-xs text-slate-500">Class sections and divisions</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Add Class Section</h3>
        <form onSubmit={handleCreateSection} className="flex flex-col sm:flex-row gap-2">
          <select
            aria-label="Grade"
            className="h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            value={gradeId}
            onChange={(e) => setGradeId(e.target.value)}
            required
          >
            <option value="">Select grade...</option>
            {grades.map((grade) => (
              <option key={grade.id} value={grade.id}>{grade.name}</option>
            ))}
          </select>
          <input
            type="text"
            className="flex-1 h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            value={sectionName}
            onChange={(e) => setSectionName(e.target.value)}
            placeholder="e.g. Section A"
            maxLength={10}
            required
          />
          <button
            type="submit"
            className="h-11 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Create Section</span>
          </button>
        </form>
      </div>

      {loading ? (
        <LoadingSkeleton type="list" count={3} />
      ) : sections.length === 0 ? (
        <EmptyState
          title="No Sections Found"
          description="Create your first class section above."
          icon={<School className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {sections.map((s) => (
            <MobileListItem
              key={s.id}
              title={s.name}
              subtitle={`Grade ID: ${s.grade_id}`}
              icon={<School className="w-5 h-5 text-emerald-600" />}
              avatarBg="bg-emerald-50 text-emerald-600"
              actions={<div className="flex gap-1" onClick={event => event.stopPropagation()}><button type="button" className="text-xs text-indigo-700" onClick={() => editSection(s)}>Edit</button><button type="button" className="text-xs text-rose-700" onClick={() => removeSection(s)}>Archive</button></div>}
            />
          ))}
        </div>
      )}

      {editingSection && (
        <EditModal
          title="Edit Section"
          fields={[
            { key: 'name', label: 'Section Name', required: true },
            {
              key: 'class_teacher_id',
              label: 'Class Teacher',
              type: 'select',
              options: [
                { value: '', label: 'None (Unassigned)' },
                ...teachers.map(t => ({
                  value: t.id,
                  label: `${t.display_name || t.full_name}${t.employee_id ? ` (${t.employee_id})` : ''}`,
                })),
              ],
            },
          ]}
          initialValues={{
            name: editingSection.name,
            class_teacher_id: editingSection.class_teacher_id || '',
          }}
          onSubmit={async (values) => {
            const updated = await sectionsService.updateSection(editingSection.id, {
              name: values.name.trim(),
              class_teacher_id: values.class_teacher_id ? Number(values.class_teacher_id) : null,
            } as any);
            setSections(items => items.map(item => (item.id === editingSection.id ? { ...item, ...updated } : item)));
            setEditingSection(null);
          }}
          onClose={() => setEditingSection(null)}
        />
      )}

      {deletingSection && (
        <ConfirmDialog
          title="Archive Section"
          message={`Are you sure you want to archive ${deletingSection.name}? This is allowed only when it has no active dependencies.`}
          confirmLabel="Archive"
          confirmVariant="danger"
          onConfirm={async () => {
            await sectionsService.deleteSection(deletingSection.id);
            setSections(items => items.filter(item => item.id !== deletingSection.id));
          }}
          onClose={() => setDeletingSection(null)}
        />
      )}
    </div>
  );
};

export default Sections;
