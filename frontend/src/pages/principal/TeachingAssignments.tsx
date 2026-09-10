// src/pages/principal/TeachingAssignments.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { BookOpen, UserCheck, Check, X, Plus, AlertCircle, Trash2 } from 'lucide-react';
import { gradesService } from '../../services/grades';
import { sectionsService } from '../../services/sections';
import { subjectsService } from '../../services/subjects';
import { teachersService } from '../../services/teachers';
import { gradeSubjectsService } from '../../services/gradeSubjects';
import { teacherSubjectsService } from '../../services/teacherSubjects';
import { useAuth } from '../../contexts/AuthContext';
import { Grade, Section, Subject, Teacher, GradeSubject, TeacherSubject } from '../../types';
import { EmptyState, LoadingSkeleton } from '../../components/shared';

export const TeachingAssignments: React.FC = () => {
  const { user } = useAuth();

  // Tab state
  const [activeTab, setActiveTab] = useState<'GRADE_SUBJECTS' | 'TEACHER_SUBJECTS'>('GRADE_SUBJECTS');

  // Common catalogs
  const [grades, setGrades] = useState<Grade[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loadingInitial, setLoadingInitial] = useState<boolean>(true);

  // Tab A state
  const [selectedGradeIdA, setSelectedGradeIdA] = useState<number | null>(null);
  const [gradeSubjectsA, setGradeSubjectsA] = useState<GradeSubject[]>([]);
  const [loadingGradeSubjectsA, setLoadingGradeSubjectsA] = useState<boolean>(false);
  const [togglingSubjectId, setTogglingSubjectId] = useState<number | null>(null);
  const [errorA, setErrorA] = useState<string | null>(null);

  // Tab B state
  const [selectedGradeIdB, setSelectedGradeIdB] = useState<number | ''>('');
  const [selectedSectionIdB, setSelectedSectionIdB] = useState<number | ''>('');
  const [selectedSubjectIdB, setSelectedSubjectIdB] = useState<number | ''>('');
  const [selectedTeacherIdB, setSelectedTeacherIdB] = useState<number | ''>('');
  const [assignedGradeSubjectsB, setAssignedGradeSubjectsB] = useState<GradeSubject[]>([]);
  const [schoolTeacherAssignments, setSchoolTeacherAssignments] = useState<TeacherSubject[]>([]);
  const [loadingAssignmentsB, setLoadingAssignmentsB] = useState<boolean>(false);
  const [assigningB, setAssigningB] = useState<boolean>(false);
  const [deletingAssignmentId, setDeletingAssignmentId] = useState<number | null>(null);
  const [errorB, setErrorB] = useState<string | null>(null);
  const [successB, setSuccessB] = useState<string | null>(null);

  // Load baseline catalogs on mount
  useEffect(() => {
    const loadInitialCatalogs = async () => {
      try {
        setLoadingInitial(true);
        const [gradesData, sectionsData, subjectsData, teachersData] = await Promise.all([
          gradesService.listGrades(),
          sectionsService.listSections(),
          subjectsService.listSubjects(),
          teachersService.listTeachers(),
        ]);
        setGrades(gradesData || []);
        setSections(sectionsData || []);
        setSubjects(subjectsData || []);
        setTeachers(teachersData || []);

        // Default selected grade for Tab A if available
        if (gradesData && gradesData.length > 0) {
          setSelectedGradeIdA(gradesData[0].id);
        }
      } catch (err) {
        console.error('Failed to load initial catalogs', err);
      } finally {
        setLoadingInitial(false);
      }
    };

    loadInitialCatalogs();
  }, []);

  // ─── TAB A: Load Grade Subjects whenever selectedGradeIdA changes ───────────
  useEffect(() => {
    if (!selectedGradeIdA) {
      setGradeSubjectsA([]);
      return;
    }
    const loadGradeSubjects = async () => {
      try {
        setLoadingGradeSubjectsA(true);
        setErrorA(null);
        const res = await gradeSubjectsService.listByGrade(selectedGradeIdA);
        setGradeSubjectsA(res || []);
      } catch (err) {
        console.error('Failed to load grade subjects', err);
        setErrorA('Failed to load subjects for this grade.');
      } finally {
        setLoadingGradeSubjectsA(false);
      }
    };
    loadGradeSubjects();
  }, [selectedGradeIdA]);

  const handleToggleGradeSubject = async (subjectId: number) => {
    if (!selectedGradeIdA || togglingSubjectId !== null) return;
    setErrorA(null);
    setTogglingSubjectId(subjectId);

    const existing = gradeSubjectsA.find((gs) => gs.subject_id === subjectId);
    try {
      if (existing) {
        // Toggle OFF -> remove
        await gradeSubjectsService.remove(existing.id);
        setGradeSubjectsA((prev) => prev.filter((gs) => gs.id !== existing.id));
      } else {
        // Toggle ON -> assign
        const created = await gradeSubjectsService.assign({
          grade_id: selectedGradeIdA,
          subject_id: subjectId,
        });
        setGradeSubjectsA((prev) => [...prev, created]);
      }
    } catch (err: any) {
      console.error('Failed to toggle grade subject', err);
      setErrorA(err?.response?.data?.detail || 'Failed to update subject assignment for this grade.');
    } finally {
      setTogglingSubjectId(null);
    }
  };

  // ─── TAB B: Load Teacher Assignments and Grade Subjects for Grade B ─────────
  // Load school assignments on tab switch or mount
  useEffect(() => {
    if (activeTab !== 'TEACHER_SUBJECTS') return;
    const loadTeacherAssignments = async () => {
      try {
        setLoadingAssignmentsB(true);
        const res = await teacherSubjectsService.listBySchool();
        setSchoolTeacherAssignments(res || []);
      } catch (err) {
        console.error('Failed to load teacher assignments', err);
      } finally {
        setLoadingAssignmentsB(false);
      }
    };
    loadTeacherAssignments();
  }, [activeTab]);

  // When Grade B changes, load assigned GradeSubjects for Grade B
  useEffect(() => {
    if (!selectedGradeIdB) {
      setAssignedGradeSubjectsB([]);
      setSelectedSectionIdB('');
      setSelectedSubjectIdB('');
      return;
    }
    const loadAssignedForGradeB = async () => {
      try {
        const res = await gradeSubjectsService.listByGrade(Number(selectedGradeIdB));
        setAssignedGradeSubjectsB(res || []);
      } catch (err) {
        console.error('Failed to load subjects for selected grade', err);
        setAssignedGradeSubjectsB([]);
      }
    };
    loadAssignedForGradeB();
    setSelectedSectionIdB('');
    setSelectedSubjectIdB('');
  }, [selectedGradeIdB]);

  // Client-side filtered sections for Grade B
  const gradeBSections = useMemo(() => {
    if (!selectedGradeIdB) return [];
    return sections.filter((sec) => sec.grade_id === Number(selectedGradeIdB));
  }, [sections, selectedGradeIdB]);

  // Available subjects for Tab B: Only subjects assigned to this grade in Tab A
  const eligibleSubjectsForGradeB = useMemo(() => {
    const assignedSubjectIds = new Set(assignedGradeSubjectsB.map((gs) => gs.subject_id));
    return subjects.filter((s) => assignedSubjectIds.has(s.id));
  }, [subjects, assignedGradeSubjectsB]);

  // Filtered teacher assignments for selected Grade + Section
  const filteredTeacherAssignments = useMemo(() => {
    if (!selectedGradeIdB || !selectedSectionIdB) return [];
    return schoolTeacherAssignments.filter(
      (ta) =>
        ta.grade_id === Number(selectedGradeIdB) &&
        ta.section_id === Number(selectedSectionIdB)
    );
  }, [schoolTeacherAssignments, selectedGradeIdB, selectedSectionIdB]);

  const handleAssignTeacher = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorB(null);
    setSuccessB(null);

    if (!selectedGradeIdB || !selectedSectionIdB || !selectedSubjectIdB || !selectedTeacherIdB) {
      return;
    }

    const schoolId = user?.school_id || 0;
    setAssigningB(true);

    try {
      const payload = {
        teacher_id: Number(selectedTeacherIdB),
        subject_id: Number(selectedSubjectIdB),
        grade_id: Number(selectedGradeIdB),
        section_id: Number(selectedSectionIdB),
        school_id: schoolId,
      };
      const created = await teacherSubjectsService.assign(payload);
      setSchoolTeacherAssignments((prev) => [...prev, created]);
      setSuccessB('Teacher assigned successfully.');
      setSelectedSubjectIdB('');
      setSelectedTeacherIdB('');
    } catch (err: any) {
      console.error('Failed to assign teacher', err);
      if (err?.response?.status === 400 || err?.status === 400) {
        setErrorB('This teacher is already assigned to this subject for this section.');
      } else {
        setErrorB(err?.response?.data?.detail || 'Failed to assign teacher.');
      }
    } finally {
      setAssigningB(false);
    }
  };

  const handleRemoveAssignment = async (assignmentId: number) => {
    setErrorB(null);
    setSuccessB(null);
    setDeletingAssignmentId(assignmentId);
    try {
      await teacherSubjectsService.remove(assignmentId);
      setSchoolTeacherAssignments((prev) => prev.filter((ta) => ta.id !== assignmentId));
      setSuccessB('Assignment removed successfully.');
    } catch (err: any) {
      console.error('Failed to remove assignment', err);
      setErrorB(err?.response?.data?.detail || 'Failed to remove assignment.');
    } finally {
      setDeletingAssignmentId(null);
    }
  };

  // Helper lookups
  const getTeacherName = (teacherId: number) => {
    const t = teachers.find((tch) => tch.id === teacherId);
    return t ? t.full_name || t.display_name || `Teacher #${teacherId}` : `Teacher #${teacherId}`;
  };

  const getSubjectName = (subjectId: number) => {
    const s = subjects.find((sub) => sub.id === subjectId);
    return s ? s.name : `Subject #${subjectId}`;
  };

  if (loadingInitial) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Teaching Assignments</h1>
          <p className="text-xs text-slate-500">Curriculum and teacher mapping</p>
        </div>
        <LoadingSkeleton type="card" count={3} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Teaching Assignments</h1>
        <p className="text-xs text-slate-500">Configure grade subjects and assign teachers to sections</p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('GRADE_SUBJECTS')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
            activeTab === 'GRADE_SUBJECTS'
              ? 'bg-emerald-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Subjects per Grade</span>
        </button>
        <button
          onClick={() => setActiveTab('TEACHER_SUBJECTS')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
            activeTab === 'TEACHER_SUBJECTS'
              ? 'bg-emerald-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <UserCheck className="w-3.5 h-3.5" />
          <span>Teacher Assignments</span>
        </button>
      </div>

      {/* ==================== TAB A: SUBJECTS PER GRADE ==================== */}
      {activeTab === 'GRADE_SUBJECTS' && (
        <div className="space-y-4">
          {errorA && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorA}</span>
            </div>
          )}

          {/* Grade Picker Pills */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600">Select Grade</label>
            {grades.length === 0 ? (
              <p className="text-xs text-slate-400">No grades found. Create grades first.</p>
            ) : (
              <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                {grades.map((grade) => {
                  const isSelected = selectedGradeIdA === grade.id;
                  return (
                    <button
                      key={grade.id}
                      type="button"
                      onClick={() => setSelectedGradeIdA(grade.id)}
                      className={`h-8 px-3.5 rounded-full text-xs font-semibold whitespace-nowrap flex-shrink-0 transition-all ${
                        isSelected
                          ? 'bg-emerald-600 text-white shadow-xs'
                          : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {grade.name}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Subjects Toggle Chip Catalog */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  {selectedGradeIdA
                    ? `Curriculum for ${grades.find((g) => g.id === selectedGradeIdA)?.name || 'Selected Grade'}`
                    : 'Select a Grade'}
                </h3>
                <p className="text-xs text-slate-500">
                  Click a subject chip to enable or disable it for this grade
                </p>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full">
                {gradeSubjectsA.length} Assigned
              </span>
            </div>

            {loadingGradeSubjectsA ? (
              <LoadingSkeleton type="card" count={2} />
            ) : subjects.length === 0 ? (
              <EmptyState
                title="No subjects in catalog"
                description="Please configure subjects in the Subjects Curriculum page first."
                icon={<BookOpen className="w-10 h-10 text-slate-300" />}
              />
            ) : (
              <div className="flex flex-wrap gap-2.5 pt-2">
                {subjects.map((sub) => {
                  const isAssigned = gradeSubjectsA.some((gs) => gs.subject_id === sub.id);
                  const isToggling = togglingSubjectId === sub.id;

                  return (
                    <button
                      key={sub.id}
                      type="button"
                      disabled={isToggling}
                      onClick={() => handleToggleGradeSubject(sub.id)}
                      className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 border transition-all active:scale-95 ${
                        isAssigned
                          ? 'bg-emerald-50 border-emerald-400 text-emerald-900 shadow-2xs'
                          : 'bg-slate-50/70 border-slate-200 text-slate-600 hover:bg-slate-100 hover:border-slate-300'
                      } ${isToggling ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    >
                      <div
                        className={`w-4 h-4 rounded-md flex items-center justify-center border transition-colors ${
                          isAssigned
                            ? 'bg-emerald-600 border-emerald-600 text-white'
                            : 'border-slate-300 bg-white'
                        }`}
                      >
                        {isAssigned && <Check className="w-3 h-3" />}
                      </div>
                      <span>{sub.name}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================== TAB B: TEACHER ASSIGNMENTS ==================== */}
      {activeTab === 'TEACHER_SUBJECTS' && (
        <div className="space-y-4">
          {errorB && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorB}</span>
            </div>
          )}

          {successB && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center gap-2">
              <Check className="w-4 h-4 flex-shrink-0 text-emerald-600" />
              <span>{successB}</span>
            </div>
          )}

          {/* Form Card */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs space-y-4">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Assign Teacher to Class & Subject
            </h3>

            <form onSubmit={handleAssignTeacher} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* 1. Grade Picker */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Grade <span className="text-rose-500">*</span>
                  </label>
                  <select
                    aria-label="Grade"
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    value={selectedGradeIdB}
                    onChange={(e) => setSelectedGradeIdB(e.target.value ? Number(e.target.value) : '')}
                    required
                  >
                    <option value="">Select Grade...</option>
                    {grades.map((grade) => (
                      <option key={grade.id} value={grade.id}>
                        {grade.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* 2. Section Picker (Filtered by Grade) */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Section <span className="text-rose-500">*</span>
                  </label>
                  <select
                    aria-label="Section"
                    disabled={!selectedGradeIdB}
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none disabled:bg-slate-50 disabled:text-slate-400"
                    value={selectedSectionIdB}
                    onChange={(e) => setSelectedSectionIdB(e.target.value ? Number(e.target.value) : '')}
                    required
                  >
                    <option value="">
                      {!selectedGradeIdB
                        ? 'Select grade first...'
                        : gradeBSections.length === 0
                        ? 'No sections for grade'
                        : 'Select Section...'}
                    </option>
                    {gradeBSections.map((sec) => (
                      <option key={sec.id} value={sec.id}>
                        Section {sec.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* 3. Subject Picker (Filtered by Tab A's assigned subjects for this Grade) */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Subject <span className="text-rose-500">*</span>
                  </label>
                  <select
                    aria-label="Subject"
                    disabled={!selectedGradeIdB}
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none disabled:bg-slate-50 disabled:text-slate-400"
                    value={selectedSubjectIdB}
                    onChange={(e) => setSelectedSubjectIdB(e.target.value ? Number(e.target.value) : '')}
                    required
                  >
                    <option value="">
                      {!selectedGradeIdB
                        ? 'Select grade first...'
                        : eligibleSubjectsForGradeB.length === 0
                        ? 'No subjects assigned in Tab A'
                        : 'Select Subject...'}
                    </option>
                    {eligibleSubjectsForGradeB.map((sub) => (
                      <option key={sub.id} value={sub.id}>
                        {sub.name}
                      </option>
                    ))}
                  </select>
                  {selectedGradeIdB && eligibleSubjectsForGradeB.length === 0 && (
                    <p className="text-[11px] text-amber-600 mt-1">
                      Configure subjects for this grade in &quot;Subjects per Grade&quot; tab first.
                    </p>
                  )}
                </div>

                {/* 4. Teacher Picker */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Teacher <span className="text-rose-500">*</span>
                  </label>
                  <select
                    aria-label="Teacher"
                    className="w-full h-11 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    value={selectedTeacherIdB}
                    onChange={(e) => setSelectedTeacherIdB(e.target.value ? Number(e.target.value) : '')}
                    required
                  >
                    <option value="">Select Teacher...</option>
                    {teachers.map((teacher) => (
                      <option key={teacher.id} value={teacher.id}>
                        {teacher.full_name || teacher.display_name || `Teacher #${teacher.id}`}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={
                    !selectedGradeIdB ||
                    !selectedSectionIdB ||
                    !selectedSubjectIdB ||
                    !selectedTeacherIdB ||
                    assigningB
                  }
                  className="h-11 px-6 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-1.5 disabled:bg-slate-300 disabled:cursor-not-allowed disabled:transform-none"
                >
                  <Plus className="w-4 h-4" />
                  <span>{assigningB ? 'Assigning...' : 'Assign Teacher'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Existing Assignments for Selected Grade + Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Current Assignments
                {selectedGradeIdB && selectedSectionIdB && (
                  <span className="text-slate-500 normal-case font-normal ml-1">
                    for {grades.find((g) => g.id === Number(selectedGradeIdB))?.name} - Section{' '}
                    {sections.find((s) => s.id === Number(selectedSectionIdB))?.name}
                  </span>
                )}
              </h3>
              {selectedGradeIdB && selectedSectionIdB && (
                <span className="text-xs text-slate-500 font-semibold">
                  {filteredTeacherAssignments.length} Assigned
                </span>
              )}
            </div>

            {!selectedGradeIdB || !selectedSectionIdB ? (
              <div className="p-8 bg-white rounded-2xl border border-slate-200/80 text-center space-y-1">
                <UserCheck className="w-8 h-8 text-slate-300 mx-auto" />
                <p className="text-sm font-semibold text-slate-700">Select a Grade & Section above</p>
                <p className="text-xs text-slate-400">
                  Choose a grade and section to view or manage assigned subject teachers.
                </p>
              </div>
            ) : loadingAssignmentsB ? (
              <LoadingSkeleton type="list" count={3} />
            ) : filteredTeacherAssignments.length === 0 ? (
              <EmptyState
                title="No Teachers Assigned"
                description="No subjects have been assigned to teachers for this section yet. Use the form above to assign teachers."
                icon={<UserCheck className="w-10 h-10 text-slate-300" />}
              />
            ) : (
              <div className="space-y-2.5">
                {filteredTeacherAssignments.map((assignment) => {
                  const isDeleting = deletingAssignmentId === assignment.id;
                  return (
                    <div
                      key={assignment.id}
                      className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs hover:shadow-xs transition-all flex items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0">
                          <BookOpen className="w-5 h-5 text-emerald-600" />
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-sm font-bold text-slate-900 truncate">
                            {getSubjectName(assignment.subject_id)}
                          </h4>
                          <p className="text-xs text-slate-500 truncate flex items-center gap-1.5 mt-0.5">
                            <span className="font-medium text-slate-700">
                              {getTeacherName(assignment.teacher_id)}
                            </span>
                          </p>
                        </div>
                      </div>

                      <button
                        type="button"
                        aria-label="Remove assignment"
                        disabled={isDeleting}
                        onClick={() => handleRemoveAssignment(assignment.id)}
                        className="p-2 rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 active:scale-95 transition-all flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Remove Assignment"
                      >
                        {isDeleting ? (
                          <div className="w-4 h-4 border-2 border-rose-600 border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TeachingAssignments;
