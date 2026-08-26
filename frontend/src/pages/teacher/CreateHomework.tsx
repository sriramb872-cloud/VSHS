import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, BookOpen, Layers } from 'lucide-react';
import { homeworkService } from '../../services/homework';
import { teachersService } from '../../services/teachers';
import { EmptyState, LoadingSkeleton } from '../../components/shared';

interface TeachingAssignment {
  grade_id: number;
  grade_name: string;
  section_id: number;
  section_name: string;
  subject_id: number;
  subject_name: string;
}

export const CreateHomeworkPage: React.FC = () => {
  const navigate = useNavigate();
  const [assignments, setAssignments] = useState<TeachingAssignment[]>([]);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [selectedClassKey, setSelectedClassKey] = useState<string>('');
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    due_date: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    teachersService
      .getMyTeacherProfile()
      .then(profile => {
        const list: TeachingAssignment[] = profile.teaching_assignments || [];
        setAssignments(list);
        if (list.length > 0) {
          const firstKey = `${list[0].grade_id}_${list[0].section_id}`;
          setSelectedClassKey(firstKey);
        }
      })
      .catch(err => {
        console.error(err);
        setError('Failed to load teaching assignments');
      })
      .finally(() => setLoadingProfile(false));
  }, []);

  // Extract unique assigned classes (grade + section)
  const uniqueClasses = React.useMemo(() => {
    const map = new Map<string, { grade_id: number; grade_name: string; section_id: number; section_name: string }>();
    assignments.forEach(a => {
      const key = `${a.grade_id}_${a.section_id}`;
      if (!map.has(key)) {
        map.set(key, {
          grade_id: a.grade_id,
          grade_name: a.grade_name,
          section_id: a.section_id,
          section_name: a.section_name,
        });
      }
    });
    return Array.from(map.entries()).map(([key, val]) => ({ key, ...val }));
  }, [assignments]);

  // Extract available subjects for the currently selected class
  const availableSubjects = React.useMemo(() => {
    if (!selectedClassKey) return [];
    const [gId, sId] = selectedClassKey.split('_').map(Number);
    const subMap = new Map<number, string>();
    assignments
      .filter(a => a.grade_id === gId && a.section_id === sId)
      .forEach(a => {
        subMap.set(a.subject_id, a.subject_name);
      });
    return Array.from(subMap.entries()).map(([id, name]) => ({ id, name }));
  }, [selectedClassKey, assignments]);

  // Set default subject when class changes
  useEffect(() => {
    if (availableSubjects.length > 0) {
      setSelectedSubjectId(String(availableSubjects[0].id));
    } else {
      setSelectedSubjectId('');
    }
  }, [selectedClassKey, availableSubjects]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClassKey || !selectedSubjectId) {
      setError('Please select an assigned class and subject.');
      return;
    }
    const [grade_id, section_id] = selectedClassKey.split('_').map(Number);
    try {
      setLoading(true);
      setError(null);
      await homeworkService.createHomework({
        title: formData.title.trim(),
        description: formData.description.trim(),
        due_date: formData.due_date,
        grade_id,
        section_id,
        subject_id: Number(selectedSubjectId),
      });
      navigate('/teacher/homework');
    } catch (err: any) {
      console.error('Failed to create homework', err);
      setError(err?.response?.data?.detail || 'Failed to create homework. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loadingProfile) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-4">
        <LoadingSkeleton type="card" count={3} />
      </div>
    );
  }

  if (assignments.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-4">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 mb-2"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <EmptyState
          title="No Teaching Assignments Found"
          description="You do not have any active class/subject assignments in the timetable to post homework for."
        />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-4">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 mb-2"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Create New Homework</h1>
          <p className="text-xs text-slate-500 mt-1">Assign homework for your assigned classes</p>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Step 1: Select Class */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-600" /> Select Class & Section
            </label>
            <select
              value={selectedClassKey}
              onChange={e => setSelectedClassKey(e.target.value)}
              className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              required
            >
              {uniqueClasses.map(c => (
                <option key={c.key} value={c.key}>
                  {c.grade_name || `Grade ${c.grade_id}`} {c.section_name ? `- Section ${c.section_name}` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Step 2: Select Subject */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-blue-600" /> Select Subject
            </label>
            <select
              value={selectedSubjectId}
              onChange={e => setSelectedSubjectId(e.target.value)}
              className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              required
            >
              {availableSubjects.map(s => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* Title */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Homework Title</label>
            <input
              type="text"
              required
              placeholder="e.g. Chapter 4 Exercise Problems"
              value={formData.title}
              onChange={e => setFormData({ ...formData, title: e.target.value })}
              className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Due Date */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Due Date</label>
            <input
              type="date"
              required
              value={formData.due_date}
              onChange={e => setFormData({ ...formData, due_date: e.target.value })}
              className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Description / Instructions */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Description & Instructions</label>
            <textarea
              rows={4}
              required
              placeholder="Write assignment instructions here..."
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              className="w-full p-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="h-11 px-5 rounded-xl border border-slate-300 text-slate-700 text-xs font-bold hover:bg-slate-50 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="h-11 px-6 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition-all disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Homework'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateHomeworkPage;