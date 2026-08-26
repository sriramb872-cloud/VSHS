// src/pages/principal/Exams.tsx
import React, { useEffect, useState } from 'react';
import { examService } from '../../services/exam';
import { gradesService } from '../../services/grades';
import { sectionsService } from '../../services/sections';
import { subjectsService } from '../../services/subjects';
import { academicYearsService } from '../../services/academicYears';
import { Exam, ExamTimetableEntry } from '../../types/exam';
import { Grade, Section, Subject, AcademicYear } from '../../types';
import {
  ClipboardList,
  Plus,
  Trash2,
  Calendar,
  Clock,
  ArrowLeft,
  BookOpen,
  Edit2,
  CheckCircle,
  Layers,
  School,
} from 'lucide-react';
import { LoadingSkeleton, ErrorState } from '../../components/shared';

const LOCAL_STORAGE_KEY = 'scholaris_exam_timetables_v1';

export const PrincipalExamsPage: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [grades, setGrades] = useState<Grade[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Category filter for the main view: 'ALL' | 'FA' | 'SA'
  const [selectedCategory, setSelectedCategory] = useState<'ALL' | 'FA' | 'SA'>('ALL');

  // Add exam modal/inline form state (NO Subject in exam creation)
  const [addingCategory, setAddingCategory] = useState<'FA' | 'SA' | null>(null);
  const [creatingExam, setCreatingExam] = useState<boolean>(false);
  const [createFormData, setCreateFormData] = useState({
    name: '',
    grade_id: 1,
    section_id: 1,
    academic_year_id: 1,
  });

  // Dedicated Exam Timetable state (Selected exam to view/manage timetable)
  const [selectedExam, setSelectedExam] = useState<Exam | null>(null);
  const [examTimetables, setExamTimetables] = useState<Record<number, ExamTimetableEntry[]>>({});

  // Add/Edit Subject Timetable Entry form state
  const [isSubjectFormOpen, setIsSubjectFormOpen] = useState<boolean>(false);
  const [editingEntry, setEditingEntry] = useState<ExamTimetableEntry | null>(null);
  const [subjectFormData, setSubjectFormData] = useState({
    subject_id: 1,
    subject_name: '',
    exam_date: '',
    start_time: '09:00',
    end_time: '10:00',
    maximum_marks: 20,
    passing_marks: 7,
  });

  // Load persistent exam timetables
  const loadSavedTimetables = (currentExams: Exam[], allSubjects: Subject[]) => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      let parsed: Record<number, ExamTimetableEntry[]> = saved ? JSON.parse(saved) : {};

      // Seed initial realistic subject schedules if none exist for loaded exams
      let updated = false;
      currentExams.forEach((ex, idx) => {
        if (!parsed[ex.id] || parsed[ex.id].length === 0) {
          const isFaExam = (ex.exam_type || '').toUpperCase().includes('FA') || (ex.name || '').toUpperCase().startsWith('FA');
          const maxM = isFaExam ? 20 : 80;
          const passM = isFaExam ? 7 : 28;
          const baseDate = new Date();
          baseDate.setDate(baseDate.getDate() + idx * 2 + 1);

          const defaultSubjectNames = allSubjects.length > 0
            ? allSubjects.slice(0, 3).map(s => ({ id: s.id, name: s.name }))
            : [
                { id: 1, name: 'Mathematics' },
                { id: 2, name: 'English' },
                { id: 3, name: 'Science' },
              ];

          parsed[ex.id] = defaultSubjectNames.map((s, sIdx) => {
            const d = new Date(baseDate);
            d.setDate(d.getDate() + sIdx);
            return {
              id: `${ex.id}-${s.id}-${sIdx}`,
              exam_id: ex.id,
              subject_id: s.id,
              subject_name: s.name,
              exam_date: d.toISOString().split('T')[0],
              start_time: '09:00',
              end_time: isFaExam ? '10:00' : '12:00',
              maximum_marks: maxM,
              passing_marks: passM,
            };
          });
          updated = true;
        }
      });

      if (updated) {
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(parsed));
      }
      setExamTimetables(parsed);
    } catch (e) {
      console.error('Failed to load saved exam timetables', e);
    }
  };

  const saveTimetables = (newMap: Record<number, ExamTimetableEntry[]>) => {
    setExamTimetables(newMap);
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(newMap));
    } catch (e) {
      console.error('Failed to save exam timetables', e);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [examsData, gradesData, sectionsData, subjectsData, academicYearsData] = await Promise.allSettled([
        examService.listExams(),
        gradesService.listGrades(),
        sectionsService.listSections(),
        subjectsService.listSubjects(),
        academicYearsService.listAcademicYears(),
      ]);

      let loadedExams: Exam[] = [];
      let loadedSubjects: Subject[] = [];

      if (examsData.status === 'fulfilled') {
        loadedExams = examsData.value.items || [];
        setExams(loadedExams);
      }
      if (gradesData.status === 'fulfilled') {
        setGrades(gradesData.value || []);
      }
      if (sectionsData.status === 'fulfilled') {
        setSections(sectionsData.value || []);
      }
      if (subjectsData.status === 'fulfilled') {
        loadedSubjects = subjectsData.value || [];
        setSubjects(loadedSubjects);
      }
      if (academicYearsData.status === 'fulfilled') {
        setAcademicYears(academicYearsData.value || []);
      }

      loadSavedTimetables(loadedExams, loadedSubjects);
    } catch (err) {
      console.error('Failed to load exams and reference data', err);
      setError('Unable to load examination schedules.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const isFA = (exam: Exam) => {
    const type = (exam.exam_type || '').toUpperCase();
    const name = (exam.name || '').toUpperCase();
    return type === 'FA' || type.includes('FA') || name.startsWith('FA');
  };

  const isSA = (exam: Exam) => {
    const type = (exam.exam_type || '').toUpperCase();
    const name = (exam.name || '').toUpperCase();
    return type === 'SA' || type.includes('SA') || name.startsWith('SA');
  };

  const faExams = exams.filter(isFA);
  const saExams = exams.filter(isSA);

  // Helper name lookups
  const getGradeName = (gradeId?: number) => {
    const g = grades.find(item => item.id === gradeId);
    return g ? g.name : `Grade ${gradeId || 1}`;
  };

  const getSectionName = (sectionId?: number) => {
    const s = sections.find(item => item.id === sectionId);
    return s ? s.name : `Section ${sectionId || 1}`;
  };

  // ─────────────────────────────────────────────────────────────
  // 1. CREATE EXAM LOGIC (NO SUBJECT FIELD)
  // ─────────────────────────────────────────────────────────────
  const handleOpenAddForm = (category: 'FA' | 'SA') => {
    const existingCategoryExams = category === 'FA' ? faExams : saExams;
    const nextNumber = existingCategoryExams.length + 1;

    setCreateFormData({
      name: `${category} ${nextNumber}`,
      grade_id: grades[0]?.id || 1,
      section_id: sections[0]?.id || 1,
      academic_year_id: academicYears[0]?.id || 1,
    });
    setAddingCategory(category);
  };

  const handleCreateExam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addingCategory || !createFormData.name.trim()) return;

    try {
      setCreatingExam(true);
      const today = new Date().toISOString().split('T')[0];
      // Create single overall FA/SA exam record for selected Class + Section
      const created = await examService.createExam({
        name: createFormData.name.trim(),
        exam_type: addingCategory,
        grade_id: Number(createFormData.grade_id),
        section_id: Number(createFormData.section_id),
        academic_year_id: Number(createFormData.academic_year_id),
        subject_id: subjects[0]?.id || 1,
        exam_date: today,
        start_time: '09:00',
        end_time: addingCategory === 'FA' ? '10:00' : '12:00',
        maximum_marks: addingCategory === 'FA' ? 20 : 80,
        passing_marks: addingCategory === 'FA' ? 7 : 28,
        instructions: `Category: ${addingCategory}`,
      });

      setExams(prev => [...prev, created]);
      setAddingCategory(null);
    } catch (err) {
      console.error('Failed to create exam', err);
      alert('Failed to create examination schedule.');
    } finally {
      setCreatingExam(false);
    }
  };

  const handleDeleteExam = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this examination schedule and its timetable?')) return;
    try {
      await examService.deleteExam(id);
      setExams(prev => prev.filter(e => e.id !== id));
      const updated = { ...examTimetables };
      delete updated[id];
      saveTimetables(updated);
      if (selectedExam && selectedExam.id === id) {
        setSelectedExam(null);
      }
    } catch (err) {
      console.error('Failed to delete exam', err);
    }
  };

  // ─────────────────────────────────────────────────────────────
  // 2. EXAM TIMETABLE MANAGEMENT (SUBJECT-WISE SCHEDULES)
  // ─────────────────────────────────────────────────────────────
  const currentExamTimetable = selectedExam ? (examTimetables[selectedExam.id] || []) : [];

  const handleOpenSubjectForm = (entry?: ExamTimetableEntry) => {
    if (entry) {
      setEditingEntry(entry);
      setSubjectFormData({
        subject_id: entry.subject_id,
        subject_name: entry.subject_name,
        exam_date: entry.exam_date,
        start_time: entry.start_time,
        end_time: entry.end_time,
        maximum_marks: entry.maximum_marks,
        passing_marks: entry.passing_marks,
      });
    } else {
      setEditingEntry(null);
      const isFa = selectedExam ? isFA(selectedExam) : true;
      const firstSubject = subjects[0];
      const today = new Date().toISOString().split('T')[0];

      setSubjectFormData({
        subject_id: firstSubject?.id || 1,
        subject_name: firstSubject?.name || 'Mathematics',
        exam_date: today,
        start_time: '09:00',
        end_time: isFa ? '10:00' : '12:00',
        maximum_marks: isFa ? 20 : 80,
        passing_marks: isFa ? 7 : 28,
      });
    }
    setIsSubjectFormOpen(true);
  };

  const handleSaveSubjectSchedule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedExam) return;

    const matchedSub = subjects.find(s => s.id === Number(subjectFormData.subject_id));
    const subName = matchedSub ? matchedSub.name : (subjectFormData.subject_name || 'Subject');

    const entryToSave: ExamTimetableEntry = {
      id: editingEntry ? editingEntry.id : `${selectedExam.id}-${Date.now()}`,
      exam_id: selectedExam.id,
      subject_id: Number(subjectFormData.subject_id),
      subject_name: subName,
      exam_date: subjectFormData.exam_date,
      start_time: subjectFormData.start_time,
      end_time: subjectFormData.end_time,
      maximum_marks: Number(subjectFormData.maximum_marks),
      passing_marks: Number(subjectFormData.passing_marks),
    };

    const currentList = examTimetables[selectedExam.id] || [];
    let updatedList: ExamTimetableEntry[];

    if (editingEntry) {
      updatedList = currentList.map(item => (item.id === editingEntry.id ? entryToSave : item));
    } else {
      updatedList = [...currentList, entryToSave];
    }

    // Sort by exam date and start time
    updatedList.sort((a, b) => a.exam_date.localeCompare(b.exam_date) || a.start_time.localeCompare(b.start_time));

    const newMap = {
      ...examTimetables,
      [selectedExam.id]: updatedList,
    };

    saveTimetables(newMap);
    setIsSubjectFormOpen(false);
    setEditingEntry(null);
  };

  const handleDeleteSubjectSchedule = (entryId: string | number) => {
    if (!selectedExam) return;
    if (!window.confirm('Are you sure you want to remove this subject from the exam timetable?')) return;

    const currentList = examTimetables[selectedExam.id] || [];
    const updatedList = currentList.filter(item => item.id !== entryId);

    const newMap = {
      ...examTimetables,
      [selectedExam.id]: updatedList,
    };

    saveTimetables(newMap);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Examination Monitor</h1>
          <p className="text-xs text-slate-500">FA & SA examination schedules and evaluation cycles</p>
        </div>
        <LoadingSkeleton type="card" count={4} />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  // ─────────────────────────────────────────────────────────────
  // VIEW: DEDICATED EXAM TIMETABLE VIEW FOR SELECTED FA/SA EXAM
  // ─────────────────────────────────────────────────────────────
  if (selectedExam) {
    const isFa = isFA(selectedExam);
    return (
      <div className="space-y-5">
        {/* Navigation & Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setSelectedExam(null);
                setIsSubjectFormOpen(false);
              }}
              className="p-2 rounded-xl text-slate-600 hover:bg-slate-100 active:scale-95 transition-all"
              title="Back to Exams"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900">{selectedExam.name}</h1>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  isFa ? 'bg-teal-50 text-teal-700 border border-teal-100' : 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                }`}>
                  {isFa ? 'FA Category' : 'SA Category'}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mt-0.5 font-medium">
                <span>Class: <strong className="text-slate-800 font-semibold">{getGradeName(selectedExam.grade_id)}</strong></span>
                <span>•</span>
                <span>Section: <strong className="text-slate-800 font-semibold">{getSectionName(selectedExam.section_id)}</strong></span>
                <span>•</span>
                <span>Academic Year: <strong className="text-slate-800 font-semibold">2026 - 2027</strong></span>
              </div>
            </div>
          </div>

          <button
            onClick={() => handleOpenSubjectForm()}
            className="h-10 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all flex-shrink-0"
          >
            <Plus className="w-4 h-4" />
            + Add Subject to Exam Timetable
          </button>
        </div>

        {/* Add/Edit Subject Timetable Entry Modal / Inline Form */}
        {isSubjectFormOpen && (
          <div className="bg-white rounded-2xl p-5 border-2 border-emerald-400 shadow-md space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  {editingEntry ? 'Edit Subject Schedule' : '+ Add Subject to Exam Timetable'}
                </h3>
                <p className="text-xs text-slate-500">
                  Configure subject timetable for {selectedExam.name} ({getGradeName(selectedExam.grade_id)} - {getSectionName(selectedExam.section_id)})
                </p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700">
                Exam Timetable Entry
              </span>
            </div>

            <form onSubmit={handleSaveSubjectSchedule} className="space-y-3 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Subject</label>
                  <select
                    value={subjectFormData.subject_id}
                    onChange={e => {
                      const subId = Number(e.target.value);
                      const sub = subjects.find(s => s.id === subId);
                      setSubjectFormData({
                        ...subjectFormData,
                        subject_id: subId,
                        subject_name: sub ? sub.name : '',
                      });
                    }}
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                  >
                    {subjects.map(s => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                    {subjects.length === 0 && <option value={1}>Mathematics</option>}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Exam Date</label>
                  <input
                    type="date"
                    required
                    value={subjectFormData.exam_date}
                    onChange={e => setSubjectFormData({ ...subjectFormData, exam_date: e.target.value })}
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Start Time</label>
                    <input
                      type="time"
                      required
                      value={subjectFormData.start_time}
                      onChange={e => setSubjectFormData({ ...subjectFormData, start_time: e.target.value })}
                      className="w-full h-10 px-2 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">End Time</label>
                    <input
                      type="time"
                      required
                      value={subjectFormData.end_time}
                      onChange={e => setSubjectFormData({ ...subjectFormData, end_time: e.target.value })}
                      className="w-full h-10 px-2 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 max-w-sm">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Max Marks</label>
                  <input
                    type="number"
                    required
                    value={subjectFormData.maximum_marks}
                    onChange={e => setSubjectFormData({ ...subjectFormData, maximum_marks: Number(e.target.value) })}
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Pass Marks</label>
                  <input
                    type="number"
                    required
                    value={subjectFormData.passing_marks}
                    onChange={e => setSubjectFormData({ ...subjectFormData, passing_marks: Number(e.target.value) })}
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsSubjectFormOpen(false);
                    setEditingEntry(null);
                  }}
                  className="h-10 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold transition-all active:scale-95"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="h-10 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold transition-all active:scale-95"
                >
                  {editingEntry ? 'Update Schedule' : 'Save Subject Schedule'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Exam Timetable Table */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-emerald-600" />
              <h2 className="text-base font-bold text-slate-900">Exam Timetable</h2>
            </div>
            <span className="text-xs font-semibold text-slate-500">
              {currentExamTimetable.length} {currentExamTimetable.length === 1 ? 'Subject Scheduled' : 'Subjects Scheduled'}
            </span>
          </div>

          {currentExamTimetable.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <Calendar className="w-10 h-10 text-slate-300 mx-auto" />
              <p className="text-sm font-bold text-slate-700">No subjects scheduled for this exam timetable yet.</p>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Click "+ Add Subject to Exam Timetable" above to configure subject exam dates, timings, and maximum marks.
              </p>
              <button
                onClick={() => handleOpenSubjectForm()}
                className="mt-2 h-9 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold inline-flex items-center gap-1.5 transition-all shadow-xs"
              >
                <Plus className="w-4 h-4" />
                + Add Subject to Exam Timetable
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200/80">
                  <tr>
                    <th className="py-3 px-4">Exam Date</th>
                    <th className="py-3 px-4">Subject</th>
                    <th className="py-3 px-4">Start Time</th>
                    <th className="py-3 px-4">End Time</th>
                    <th className="py-3 px-4 text-center">Max Marks</th>
                    <th className="py-3 px-4 text-center">Pass Marks</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {currentExamTimetable.map(item => (
                    <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-slate-900 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          <span>{item.exam_date}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-bold text-slate-900">
                        {item.subject_name}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <span>{item.start_time}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <span>{item.end_time}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold text-slate-900">
                        {item.maximum_marks}
                      </td>
                      <td className="py-3.5 px-4 text-center font-semibold text-emerald-700">
                        {item.passing_marks}
                      </td>
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleOpenSubjectForm(item)}
                            className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-all"
                            title="Edit Subject Schedule"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteSubjectSchedule(item.id)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"
                            title="Delete Subject Schedule"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────
  // MAIN VIEW: FA & SA EXAMS LIST
  // ─────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Examination Monitor</h1>
          <p className="text-xs text-slate-500">Manage Formative (FA) and Summative (SA) assessment cycles</p>
        </div>

        {/* Category Filter Pills */}
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedCategory('ALL')}
            className={`h-9 px-4 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              selectedCategory === 'ALL'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            All Categories ({exams.length})
          </button>
          <button
            onClick={() => setSelectedCategory('FA')}
            className={`h-9 px-4 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              selectedCategory === 'FA'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            FA Exams ({faExams.length})
          </button>
          <button
            onClick={() => setSelectedCategory('SA')}
            className={`h-9 px-4 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              selectedCategory === 'SA'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            SA Exams ({saExams.length})
          </button>
        </div>
      </div>

      {/* Add Exam Modal / Inline Form (NO SUBJECT FIELD) */}
      {addingCategory && (
        <div className="bg-white rounded-2xl p-5 border-2 border-emerald-400 shadow-md space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Add {addingCategory} Exam</h3>
              <p className="text-xs text-slate-500">
                Create new {addingCategory === 'FA' ? 'Formative' : 'Summative'} Assessment for a Class & Section
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700">
              {addingCategory} Exam Creation
            </span>
          </div>

          <form onSubmit={handleCreateExam} className="space-y-3 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Exam Name</label>
                <input
                  type="text"
                  required
                  value={createFormData.name}
                  onChange={e => setCreateFormData({ ...createFormData, name: e.target.value })}
                  placeholder={`e.g. ${addingCategory} 1, ${addingCategory} 2...`}
                  className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Class / Grade</label>
                <select
                  value={createFormData.grade_id}
                  onChange={e => setCreateFormData({ ...createFormData, grade_id: Number(e.target.value) })}
                  className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                >
                  {grades.map(g => (
                    <option key={g.id} value={g.id}>{g.name}</option>
                  ))}
                  {grades.length === 0 && <option value={1}>Grade 1</option>}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Section</label>
                <select
                  value={createFormData.section_id}
                  onChange={e => setCreateFormData({ ...createFormData, section_id: Number(e.target.value) })}
                  className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                >
                  {sections.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                  {sections.length === 0 && <option value={1}>Section A</option>}
                </select>
              </div>
            </div>

            <div className="p-3 bg-emerald-50/50 rounded-xl border border-emerald-100 text-emerald-900 text-xs flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>
                Subjects and their individual exam dates/times can be configured inside this exam's dedicated <strong>Exam Timetable</strong> after creation.
              </span>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setAddingCategory(null)}
                className="h-10 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold transition-all active:scale-95"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creatingExam}
                className="h-10 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold transition-all active:scale-95 disabled:opacity-50"
              >
                {creatingExam ? 'Creating...' : `Create ${addingCategory} Exam`}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 1. FA EXAMS SECTION */}
      {(selectedCategory === 'ALL' || selectedCategory === 'FA') && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900">FA Exams</h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-50 text-teal-700 border border-teal-100">
                  {faExams.length} {faExams.length === 1 ? 'Exam' : 'Exams'}
                </span>
              </div>
              <p className="text-xs text-slate-500">Formative Assessment series (FA 1, FA 2, FA 3, FA 4...)</p>
            </div>

            <button
              onClick={() => handleOpenAddForm('FA')}
              className="h-9 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all flex-shrink-0"
            >
              <Plus className="w-4 h-4" />
              + Add FA Exam
            </button>
          </div>

          {faExams.length === 0 ? (
            <div className="bg-white rounded-2xl p-6 border border-slate-200/80 text-center space-y-2">
              <ClipboardList className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs font-bold text-slate-700">No FA Exams Created</p>
              <p className="text-[11px] text-slate-400">Click "+ Add FA Exam" above to create FA 1, FA 2, etc.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {faExams.map(exam => {
                const timetableCount = (examTimetables[exam.id] || []).length;
                return (
                  <div
                    key={exam.id}
                    className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all space-y-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-base font-bold text-slate-900">{exam.name}</h4>
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-teal-50 text-teal-700 border border-teal-100">
                            FA Category
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                          <span>{getGradeName(exam.grade_id)}</span>
                          <span>•</span>
                          <span>{getSectionName(exam.section_id)}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteExam(exam.id)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"
                        title="Delete Exam"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                      <span className="text-xs font-medium text-slate-500">
                        {timetableCount} {timetableCount === 1 ? 'Subject Scheduled' : 'Subjects Scheduled'}
                      </span>
                      <button
                        onClick={() => setSelectedExam(exam)}
                        className="h-8 px-3 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center gap-1.5 transition-all"
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        Exam Timetable
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 2. SA EXAMS SECTION */}
      {(selectedCategory === 'ALL' || selectedCategory === 'SA') && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900">SA Exams</h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-100">
                  {saExams.length} {saExams.length === 1 ? 'Exam' : 'Exams'}
                </span>
              </div>
              <p className="text-xs text-slate-500">Summative Assessment series (SA 1, SA 2, SA 3, SA 4...)</p>
            </div>

            <button
              onClick={() => handleOpenAddForm('SA')}
              className="h-9 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all flex-shrink-0"
            >
              <Plus className="w-4 h-4" />
              + Add SA Exam
            </button>
          </div>

          {saExams.length === 0 ? (
            <div className="bg-white rounded-2xl p-6 border border-slate-200/80 text-center space-y-2">
              <ClipboardList className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs font-bold text-slate-700">No SA Exams Created</p>
              <p className="text-[11px] text-slate-400">Click "+ Add SA Exam" above to create SA 1, SA 2, etc.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {saExams.map(exam => {
                const timetableCount = (examTimetables[exam.id] || []).length;
                return (
                  <div
                    key={exam.id}
                    className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all space-y-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-base font-bold text-slate-900">{exam.name}</h4>
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-100">
                            SA Category
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                          <span>{getGradeName(exam.grade_id)}</span>
                          <span>•</span>
                          <span>{getSectionName(exam.section_id)}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteExam(exam.id)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"
                        title="Delete Exam"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                      <span className="text-xs font-medium text-slate-500">
                        {timetableCount} {timetableCount === 1 ? 'Subject Scheduled' : 'Subjects Scheduled'}
                      </span>
                      <button
                        onClick={() => setSelectedExam(exam)}
                        className="h-8 px-3 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center gap-1.5 transition-all"
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        Exam Timetable
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PrincipalExamsPage;

