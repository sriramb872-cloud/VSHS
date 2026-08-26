// src/pages/principal/Enrollments.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  GraduationCap,
  Users,
  Layers,
  ChevronRight,
  ArrowLeft,
  School,
  User,
  Percent,
} from 'lucide-react';
import { gradesService } from '../../services/grades';
import { sectionsService } from '../../services/sections';
import { enrollmentsService } from '../../services/enrollments';
import { Grade, Section, StudentEnrollment } from '../../types';
import { EmptyState, LoadingSkeleton, ErrorState } from '../../components/shared';

export const Enrollments: React.FC = () => {
  const navigate = useNavigate();

  const [grades, setGrades] = useState<Grade[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [enrollments, setEnrollments] = useState<StudentEnrollment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Drilldown selection state
  const [selectedGrade, setSelectedGrade] = useState<Grade | null>(null);
  const [selectedSection, setSelectedSection] = useState<Section | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [gradesData, sectionsData, enrollmentsData] = await Promise.all([
        gradesService.listGrades(),
        sectionsService.listSections(),
        enrollmentsService.listEnrollments(),
      ]);
      setGrades(gradesData || []);
      setSections(sectionsData || []);
      setEnrollments(enrollmentsData || []);
    } catch (err) {
      console.error('Failed to load enrollment data', err);
      setError('Unable to load classes and enrollment records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Helper calculation functions
  const getGradeSections = (gradeId: number) => {
    return sections.filter((s) => s.grade_id === gradeId);
  };

  const getGradeEnrollments = (gradeId: number) => {
    const gradeSectionIds = new Set(getGradeSections(gradeId).map((s) => s.id));
    return enrollments.filter(
      (e) => (e.grade_id === gradeId) || (e.section_id && gradeSectionIds.has(e.section_id))
    );
  };

  const getSectionEnrollments = (sectionId: number) => {
    return enrollments.filter((e) => e.section_id === sectionId);
  };

  // Selection handlers
  const handleSelectGrade = (grade: Grade) => {
    const gradeSecs = getGradeSections(grade.id);
    setSelectedGrade(grade);
    if (gradeSecs.length === 0) {
      // No sections: directly view grade students
      setSelectedSection(null);
    } else {
      setSelectedSection(null);
    }
  };

  const handleSelectSection = (section: Section) => {
    setSelectedSection(section);
  };

  const handleBackToClasses = () => {
    setSelectedGrade(null);
    setSelectedSection(null);
  };

  const handleBackToSections = () => {
    setSelectedSection(null);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Classes & Enrollment</h1>
          <p className="text-xs text-slate-500">Class, section, and student rosters</p>
        </div>
        <LoadingSkeleton type="card" count={4} />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  // ==================== VIEW 3: STUDENTS IN SECTION OR GRADE ====================
  if (selectedGrade && (selectedSection || getGradeSections(selectedGrade.id).length === 0)) {
    const studentsToDisplay = selectedSection
      ? getSectionEnrollments(selectedSection.id)
      : getGradeEnrollments(selectedGrade.id);

    const hasSections = getGradeSections(selectedGrade.id).length > 0;

    return (
      <div className="space-y-4">
        {/* Header & Breadcrumb */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={hasSections ? handleBackToSections : handleBackToClasses}
            className="p-2 rounded-xl text-slate-600 hover:bg-slate-100 active:scale-95 transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
              <span className="cursor-pointer hover:text-slate-900" onClick={handleBackToClasses}>
                Classes
              </span>
              <span>/</span>
              {hasSections ? (
                <>
                  <span className="cursor-pointer hover:text-slate-900" onClick={handleBackToSections}>
                    {selectedGrade.name}
                  </span>
                  <span>/</span>
                  <span className="text-slate-900 font-semibold">{selectedSection?.name}</span>
                </>
              ) : (
                <span className="text-slate-900 font-semibold">{selectedGrade.name}</span>
              )}
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              {selectedSection
                ? `${selectedGrade.name} - Section ${selectedSection.name}`
                : `${selectedGrade.name} (All Students)`}
            </h1>
          </div>
        </div>

        {/* Students List */}
        {studentsToDisplay.length === 0 ? (
          <EmptyState
            title="No students enrolled in this class."
            description="No student records were found matching this class / section."
            icon={<GraduationCap className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <div className="space-y-2.5">
            <div className="text-xs font-semibold text-slate-500 px-1">
              Enrolled Students ({studentsToDisplay.length})
            </div>
            {studentsToDisplay.map((st) => (
              <div
                key={st.id || st.student_id}
                onClick={() => navigate(`/principal/students/${st.student_id || st.id}`)}
                className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all cursor-pointer active:scale-[0.99] flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-11 h-11 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0">
                    {(st.student_name || st.full_name || 'ST').slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-slate-900 truncate">
                      {st.student_name || st.full_name || 'Enrolled Student'}
                    </h3>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mt-0.5">
                      <span>Adm: {st.admission_number || '-'}</span>
                      {st.roll_number && (
                        <>
                          <span>•</span>
                          <span>Roll: {st.roll_number}</span>
                        </>
                      )}
                      {st.gender && (
                        <>
                          <span>•</span>
                          <span>{st.gender}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 flex-shrink-0">
                  {st.attendance_percentage !== null && st.attendance_percentage !== undefined ? (
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full flex items-center gap-1">
                      <Percent className="w-3 h-3" /> {st.attendance_percentage}%
                    </span>
                  ) : null}
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ==================== VIEW 2: SECTIONS LIST FOR SELECTED GRADE ====================
  if (selectedGrade) {
    const gradeSecs = getGradeSections(selectedGrade.id);
    const totalStudentsInGrade = getGradeEnrollments(selectedGrade.id).length;

    return (
      <div className="space-y-4">
        {/* Breadcrumb Header */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleBackToClasses}
            className="p-2 rounded-xl text-slate-600 hover:bg-slate-100 active:scale-95 transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
              <span className="cursor-pointer hover:text-slate-900" onClick={handleBackToClasses}>
                Classes
              </span>
              <span>/</span>
              <span className="text-slate-900 font-semibold">{selectedGrade.name}</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900">Select Section</h1>
          </div>
        </div>

        {/* Section Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {gradeSecs.map((sec) => {
            const count = getSectionEnrollments(sec.id).length;
            return (
              <div
                key={sec.id}
                onClick={() => handleSelectSection(sec)}
                className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all cursor-pointer active:scale-[0.99] space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-base">
                      {sec.name}
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">Section {sec.name}</h3>
                      <p className="text-xs text-slate-500">{selectedGrade.name}</p>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center gap-1.5 text-xs text-slate-600">
                  <Users className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-semibold text-slate-900">{count}</span> Students
                </div>
              </div>
            );
          })}
        </div>

        {/* Option to view all students in this grade */}
        <div
          onClick={() => setSelectedSection(null)}
          className="p-4 bg-emerald-50/60 rounded-2xl border border-emerald-100 hover:border-emerald-300 transition-all cursor-pointer flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <GraduationCap className="w-5 h-5 text-emerald-700" />
            <div>
              <p className="text-xs font-bold text-emerald-950">View All Students in {selectedGrade.name}</p>
              <p className="text-[11px] text-emerald-700">{totalStudentsInGrade} total students across all sections</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-emerald-600" />
        </div>
      </div>
    );
  }

  // ==================== VIEW 1: ALL CLASSES / GRADES ====================
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Classes & Enrollment</h1>
          <p className="text-xs text-slate-500">Select a class to view sections and enrolled students</p>
        </div>
        <button
          onClick={() => navigate('/principal/grades')}
          className="h-10 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all flex-shrink-0"
        >
          + Add Class
        </button>
      </div>

      {grades.length === 0 ? (
        <EmptyState
          title="No classes found."
          description="No grades or classes have been set up for this school yet."
          icon={<School className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {grades.map((gr) => {
            const grSecs = getGradeSections(gr.id);
            const studentCount = getGradeEnrollments(gr.id).length;

            return (
              <div
                key={gr.id}
                onClick={() => handleSelectGrade(gr)}
                className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all cursor-pointer active:scale-[0.99] space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold text-base">
                      <School className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">{gr.name}</h3>
                      <p className="text-xs text-slate-500">
                        {grSecs.length > 0 ? `${grSecs.length} Sections` : 'No Sections'}
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                  <div className="flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-slate-400" />
                    <span className="font-semibold text-slate-900">{studentCount}</span> Students
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-slate-400" />
                    <span>{grSecs.length > 0 ? grSecs.map((s) => s.name).join(', ') : 'Direct'}</span>
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

export default Enrollments;