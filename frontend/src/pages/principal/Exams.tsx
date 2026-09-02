// src/pages/principal/Exams.tsx
import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Calendar, Award, Layers, CheckCircle2, Clock } from 'lucide-react';
import { examService } from '../../services/exam';
import { gradesService } from '../../services/grades';
import { sectionsService } from '../../services/sections';
import { academicYearsService } from '../../services/academicYears';
import { Exam, ExamCreatePayload } from '../../types/exam';
import { Grade, Section, AcademicYear } from '../../types';
import { LoadingSkeleton, EmptyState, ConfirmDialog } from '../../components/shared';

export const PrincipalExamsPage: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [grades, setGrades] = useState<Grade[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form state
  const [formData, setFormData] = useState<ExamCreatePayload>({
    name: '',
    exam_type: 'Summative Assessment',
    assessment_mode: 'SUMMATIVE',
    academic_year_id: 1,
    grade_id: 1,
    section_id: 1,
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0],
    maximum_marks: 100,
    passing_marks: 35,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [examsData, gradesData, sectionsData, yearsData] = await Promise.all([
        examService.listExams({ limit: 100 }),
        gradesService.listGrades(),
        sectionsService.listSections(),
        academicYearsService.listAcademicYears(),
      ]);

      setExams(examsData.items);
      setGrades(gradesData);
      setSections(sectionsData);
      setAcademicYears(yearsData);

      if (yearsData.length > 0 && !formData.academic_year_id) {
        setFormData(prev => ({ ...prev, academic_year_id: yearsData[0].id }));
      }
      if (gradesData.length > 0 && !formData.grade_id) {
        setFormData(prev => ({ ...prev, grade_id: gradesData[0].id }));
      }
      if (sectionsData.length > 0 && !formData.section_id) {
        setFormData(prev => ({ ...prev, section_id: sectionsData[0].id }));
      }
    } catch (err: any) {
      console.error('Failed to load exams', err);
      setFeedback({ type: 'error', text: 'Failed to load examinations data' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateExam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setFeedback({ type: 'error', text: 'Exam title is required' });
      return;
    }

    try {
      setSubmitting(true);
      setFeedback(null);
      await examService.createExam(formData);
      setFeedback({
        type: 'success',
        text: `Exam "${formData.name}" created successfully with auto-generated subject schedules!`,
      });
      setIsCreateOpen(false);
      setFormData(prev => ({
        ...prev,
        name: '',
      }));
      await loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to create exam',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await examService.deleteExam(deleteId);
      setExams(prev => prev.filter(e => e.id !== deleteId));
      setFeedback({ type: 'success', text: 'Exam deleted successfully' });
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.response?.data?.detail || 'Failed to delete exam' });
    } finally {
      setDeleteId(null);
    }
  };

  const filteredSections = sections.filter(s => s.grade_id === Number(formData.grade_id));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Examinations & Assessments</h1>
          <p className="text-xs text-slate-500">
            Create school examination windows and monitor per-subject marks entry
          </p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="h-10 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all flex-shrink-0"
        >
          <Plus className="w-4 h-4" />
          Schedule Exam
        </button>
      </div>

      {/* Feedback message */}
      {feedback && (
        <div
          className={`p-4 rounded-xl text-sm font-medium flex items-center justify-between ${
            feedback.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback(null)} className="text-xs underline ml-4">
            Dismiss
          </button>
        </div>
      )}

      {/* Create Exam Modal / Form */}
      {isCreateOpen && (
        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900">Schedule New Examination Window</h2>
            <button
              onClick={() => setIsCreateOpen(false)}
              className="text-xs font-semibold text-slate-400 hover:text-slate-600"
            >
              Cancel
            </button>
          </div>

          <form onSubmit={handleCreateExam} className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Exam Name / Code *</label>
              <input
                type="text"
                placeholder="e.g. SA1, Mid-Term 2026, Annual Exam"
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
                required
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Assessment Mode *</label>
              <select
                value={formData.assessment_mode}
                onChange={e =>
                  setFormData({
                    ...formData,
                    assessment_mode: e.target.value as 'SUMMATIVE' | 'FORMATIVE',
                    maximum_marks: e.target.value === 'SUMMATIVE' ? 100 : 35,
                    passing_marks: e.target.value === 'SUMMATIVE' ? 35 : 14,
                  })
                }
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
              >
                <option value="SUMMATIVE">SUMMATIVE (Single Total Marks)</option>
                <option value="FORMATIVE">FORMATIVE (4-Component FA)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Academic Year *</label>
              <select
                value={formData.academic_year_id}
                onChange={e => setFormData({ ...formData, academic_year_id: Number(e.target.value) })}
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
              >
                {academicYears.map(y => (
                  <option key={y.id} value={y.id}>
                    {y.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Grade / Class *</label>
              <select
                value={formData.grade_id}
                onChange={e => {
                  const gId = Number(e.target.value);
                  const validSecs = sections.filter(s => s.grade_id === gId);
                  setFormData({
                    ...formData,
                    grade_id: gId,
                    section_id: validSecs.length > 0 ? validSecs[0].id : 1,
                  });
                }}
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
              >
                {grades.map(g => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Section *</label>
              <select
                value={formData.section_id}
                onChange={e => setFormData({ ...formData, section_id: Number(e.target.value) })}
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
              >
                {filteredSections.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Exam Type Label</label>
              <input
                type="text"
                value={formData.exam_type}
                onChange={e => setFormData({ ...formData, exam_type: e.target.value })}
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Start Date *</label>
              <input
                type="date"
                value={formData.start_date}
                onChange={e => setFormData({ ...formData, start_date: e.target.value })}
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
                required
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">End Date *</label>
              <input
                type="date"
                value={formData.end_date}
                onChange={e => setFormData({ ...formData, end_date: e.target.value })}
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
                required
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Default Max Marks</label>
              <input
                type="number"
                value={formData.maximum_marks}
                onChange={e => setFormData({ ...formData, maximum_marks: Number(e.target.value) })}
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Default Passing Marks</label>
              <input
                type="number"
                value={formData.passing_marks}
                onChange={e => setFormData({ ...formData, passing_marks: Number(e.target.value) })}
                className="w-full h-10 px-3 border border-slate-200 rounded-xl outline-none focus:border-blue-500 font-medium"
              />
            </div>

            <div className="sm:col-span-2 flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsCreateOpen(false)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold disabled:opacity-50"
              >
                {submitting ? 'Creating...' : 'Create & Auto-Assign Subjects'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Exams List */}
      {loading ? (
        <LoadingSkeleton type="card" count={4} />
      ) : exams.length === 0 ? (
        <EmptyState
          title="No Examinations Scheduled"
          description="Schedule your school's first examination window above."
          icon={<Calendar className="w-10 h-10 text-slate-300" />}
          action={{ label: 'Schedule Exam', onClick: () => setIsCreateOpen(true) }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {exams.map(exam => {
            const isPublished = (exam.status || '').toUpperCase() === 'PUBLISHED';
            return (
              <div
                key={exam.id}
                className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between space-y-4"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">{exam.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-purple-50 text-purple-700">
                          {exam.assessment_mode}
                        </span>
                        <span className="text-xs text-slate-500">{exam.exam_type}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                          isPublished
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : exam.status === 'MARKS_IN_PROGRESS'
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-blue-50 text-blue-700 border border-blue-200'
                        }`}
                      >
                        {exam.status}
                      </span>
                      <button
                        onClick={() => setDeleteId(exam.id)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                        title="Delete Exam"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 mt-4 text-xs text-slate-600">
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>
                        {exam.start_date} to {exam.end_date}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-slate-400" />
                      <span>
                        {exam.grade_name || `Grade ${exam.grade_id}`} - {exam.section_name || `Sec ${exam.section_id}`}
                      </span>
                    </div>
                  </div>

                  {/* Subject schedule summary */}
                  {exam.exam_subjects && exam.exam_subjects.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5">
                      <div className="text-xs font-bold text-slate-700 flex items-center justify-between">
                        <span>Subjects ({exam.exam_subjects.length})</span>
                        <span className="font-normal text-slate-500">
                          {exam.exam_subjects.filter(s => s.is_marks_submitted).length} submitted
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {exam.exam_subjects.map(s => (
                          <span
                            key={s.id}
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs ${
                              s.is_marks_submitted
                                ? 'bg-emerald-50 text-emerald-700 font-semibold'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {s.is_marks_submitted ? (
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            ) : (
                              <Clock className="w-3 h-3 text-slate-400" />
                            )}
                            {s.subject_name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="pt-2 flex items-center justify-between text-xs text-slate-400 border-t border-slate-100">
                  <span>Exam ID: #{exam.id}</span>
                  <span>{new Date(exam.created_at || Date.now()).toLocaleDateString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteId !== null}
        title="Delete Examination?"
        message="This will delete this exam window, all subject schedules, and recorded marks."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
};

export default PrincipalExamsPage;
