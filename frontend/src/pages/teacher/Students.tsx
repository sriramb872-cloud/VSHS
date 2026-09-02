// src/pages/teacher/Students.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  Search,
  ChevronRight,
  Plus,
  X,
  Save,
  AlertCircle,
  CheckCircle,
  GraduationCap,
  ShieldCheck,
  Phone,
  Layers,
  School,
  Lock,
} from 'lucide-react';
import { teachersService } from '../../services/teachers';
import { sectionsService } from '../../services/sections';
import { studentsService } from '../../services/students';
import { Teacher, Section, Student } from '../../types';
import { EmptyState, LoadingSkeleton, ErrorState } from '../../components/shared';

export const TeacherStudents: React.FC = () => {
  const [profile, setProfile] = useState<Teacher | null>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  // Class assignment state
  const [selectedSectionId, setSelectedSectionId] = useState<string>('');
  const [assigning, setAssigning] = useState(false);
  const [assignmentFeedback, setAssignmentFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  // Add student modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [submittingStudent, setSubmittingStudent] = useState(false);
  const [studentModalFeedback, setStudentModalFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  // New Student Form Data
  const [formData, setFormData] = useState({
    full_name: '',
    admission_number: '',
    admission_date: new Date().toISOString().slice(0, 10),
    roll_number: '',
    date_of_birth: '',
    gender: 'MALE',
    blood_group: '',
    father_name: '',
    father_mobile: '',
    mother_name: '',
    mother_mobile: '',
    guardian_mobile: '',
    address: '',
    email: '',
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch teacher profile to identify current assigned class
      const teacherProfile = await teachersService.getMyTeacherProfile();
      setProfile(teacherProfile);

      // Fetch available sections belonging to the teacher's school
      const sectionsList = await sectionsService.listSections();
      setSections(sectionsList || []);

      // If teacher is assigned as class teacher, load students for her class
      if (teacherProfile.class_teacher_section) {
        const studentList = await studentsService.listStudents();
        setStudents(studentList || []);
      } else {
        setStudents([]);
      }
    } catch (err: any) {
      console.error('Failed to load teacher class data', err);
      setError(err?.response?.data?.detail || 'Unable to load class and student data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAssignClassTeacher = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSectionId) {
      setAssignmentFeedback({
        type: 'error',
        message: 'Please select a class to assign yourself as Class Teacher.',
      });
      return;
    }

    try {
      setAssigning(true);
      setAssignmentFeedback(null);

      const updatedProfile = await teachersService.assignMeAsClassTeacher(
        Number(selectedSectionId)
      );
      setProfile(updatedProfile);
      setAssignmentFeedback({
        type: 'success',
        message: `Successfully assigned as Class Teacher!`,
      });

      // Reload students and sections to reflect assignment
      const studentList = await studentsService.listStudents();
      setStudents(studentList || []);
      const sectionsList = await sectionsService.listSections();
      setSections(sectionsList || []);
    } catch (err: any) {
      console.error('Failed to assign class teacher', err);
      setAssignmentFeedback({
        type: 'error',
        message:
          err?.response?.data?.detail ||
          'Failed to assign class teacher. Please try again.',
      });
    } finally {
      setAssigning(false);
    }
  };

  const handleCreateStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.full_name.trim()) {
      setStudentModalFeedback({
        type: 'error',
        message: 'Student full name is required.',
      });
      return;
    }

    if (!profile?.class_teacher_section) {
      setStudentModalFeedback({
        type: 'error',
        message: 'You must be assigned as a Class Teacher to add students.',
      });
      return;
    }

    try {
      setSubmittingStudent(true);
      setStudentModalFeedback(null);

      const payload = {
        full_name: formData.full_name.trim(),
        display_name: formData.full_name.trim(),
        admission_number: formData.admission_number.trim() || undefined,
        admission_date: formData.admission_date || undefined,
        roll_number: formData.roll_number.trim() || undefined,
        date_of_birth: formData.date_of_birth || undefined,
        gender: formData.gender || undefined,
        blood_group: formData.blood_group.trim() || undefined,
        father_name: formData.father_name.trim() || undefined,
        father_mobile: formData.father_mobile.trim() || undefined,
        mother_name: formData.mother_name.trim() || undefined,
        mother_mobile: formData.mother_mobile.trim() || undefined,
        guardian_mobile:
          formData.guardian_mobile.trim() ||
          formData.father_mobile.trim() ||
          formData.mother_mobile.trim() ||
          undefined,
        address: formData.address.trim() || undefined,
        email: formData.email.trim() || undefined,
      };

      await studentsService.createStudent(payload);
      setShowAddModal(false);
      setFormData({
        full_name: '',
        admission_number: '',
        admission_date: new Date().toISOString().slice(0, 10),
        roll_number: '',
        date_of_birth: '',
        gender: 'MALE',
        blood_group: '',
        father_name: '',
        father_mobile: '',
        mother_name: '',
        mother_mobile: '',
        guardian_mobile: '',
        address: '',
        email: '',
      });

      // Refresh student roster
      const studentList = await studentsService.listStudents();
      setStudents(studentList || []);
    } catch (err: any) {
      console.error('Failed to create student', err);
      setStudentModalFeedback({
        type: 'error',
        message:
          err?.response?.data?.detail ||
          'Failed to add student. Please verify all inputs.',
      });
    } finally {
      setSubmittingStudent(false);
    }
  };

  const assignedSection = profile?.class_teacher_section;
  const assignedClassDisplayName = assignedSection
    ? `${assignedSection.grade_name || `Grade ${assignedSection.grade_id}`} - ${assignedSection.name || assignedSection.section_name}`
    : null;

  const filteredStudents = students.filter(
    (st) =>
      (st.display_name || st.full_name || '').toLowerCase().includes(search.toLowerCase()) ||
      (st.admission_number || '').toLowerCase().includes(search.toLowerCase()) ||
      (st.roll_number || '').toLowerCase().includes(search.toLowerCase()) ||
      (st.mobile || '').includes(search)
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Student Management</h1>
          <p className="text-xs text-slate-500">
            {assignedSection
              ? `Manage students enrolled in ${assignedClassDisplayName}`
              : 'Class Teacher Assignment & Student Roster'}
          </p>
        </div>

        {assignedSection && (
          <button
            onClick={() => {
              setShowAddModal(true);
              setStudentModalFeedback(null);
            }}
            className="h-10 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm transition-all self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            Add Student
          </button>
        )}
      </div>

      {error && <ErrorState message={error} onRetry={loadData} />}

      {/* Global Feedback Banner */}
      {assignmentFeedback && (
        <div
          className={`p-3.5 rounded-xl border text-xs font-medium flex items-center gap-2.5 ${
            assignmentFeedback.type === 'success'
              ? 'bg-blue-50 border-blue-200 text-blue-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          {assignmentFeedback.type === 'success' ? (
            <CheckCircle className="w-4 h-4 text-blue-600 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          )}
          <span>{assignmentFeedback.message}</span>
        </div>
      )}

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : !assignedSection ? (
        /* Unassigned State: Class Teacher Self-Assignment Card */
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-blue-50 via-sky-50 to-indigo-50 border border-blue-200/80 rounded-3xl p-6 sm:p-8 space-y-5 shadow-xs">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center flex-shrink-0 shadow-md">
                <GraduationCap className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h2 className="text-base sm:text-lg font-bold text-slate-900">
                  You are not assigned as a Class Teacher yet
                </h2>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  To manage students and enroll new students, please select a class from your school and assign yourself as the Class Teacher.
                </p>
              </div>
            </div>

            <form onSubmit={handleAssignClassTeacher} className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Select Class / Section
                </label>
                <select
                  value={selectedSectionId}
                  onChange={(e) => setSelectedSectionId(e.target.value)}
                  className="w-full h-11 px-3.5 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="">-- Choose a Class / Section --</option>
                  {sections.map((sec) => {
                    const secDisplayName = `${sec.grade_name || `Grade ${sec.grade_id}`} - ${sec.name}`;
                    const isOccupied =
                      sec.class_teacher_id &&
                      sec.class_teacher_id !== profile?.id;
                    return (
                      <option
                        key={sec.id}
                        value={sec.id}
                        disabled={Boolean(isOccupied)}
                      >
                        {secDisplayName}{' '}
                        {isOccupied
                          ? `(Assigned to: ${sec.class_teacher_name || 'Another Teacher'})`
                          : '(Available)'}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <button
                  type="submit"
                  disabled={assigning || !selectedSectionId}
                  className="h-11 px-6 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  <ShieldCheck className="w-4 h-4" />
                  {assigning ? 'Assigning...' : 'Assign Me as Class Teacher'}
                </button>
              </div>
            </form>
          </div>

          <EmptyState
            title="Student Roster Locked"
            description="Student roster and onboarding will become available once you assign yourself as Class Teacher."
            icon={<Lock className="w-10 h-10 text-slate-300" />}
          />
        </div>
      ) : (
        /* Assigned State: Show Assigned Banner + Student Roster */
        <div className="space-y-4">
          {/* Class Teacher Banner */}
          <div className="bg-white rounded-2xl border border-blue-200/80 p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center flex-shrink-0 font-bold">
                <GraduationCap className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-blue-600 font-semibold uppercase tracking-wider">
                  Class Teacher Assignment
                </p>
                <h2 className="text-sm font-bold text-slate-900">
                  You are the Class Teacher of {assignedClassDisplayName}
                </h2>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                <CheckCircle className="w-3 h-3 mr-1 text-emerald-600" /> Active Class Teacher
              </span>
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by student name, roll number, admission number or mobile..."
              className="w-full h-11 pl-10 pr-4 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs sm:text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
          </div>

          {/* Student Roster List */}
          {filteredStudents.length === 0 ? (
            <EmptyState
              title="No Students in Your Class"
              description={
                search
                  ? 'No student in your class matches your search query.'
                  : `No students enrolled in ${assignedClassDisplayName} yet. Click "Add Student" to onboard students.`
              }
              icon={<Users className="w-10 h-10 text-slate-300" />}
            />
          ) : (
            <div className="space-y-2.5">
              {filteredStudents.map((st) => (
                <Link
                  key={st.id}
                  to={`/teacher/students/${st.id}`}
                  className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs hover:border-blue-300 hover:shadow-xs transition-all cursor-pointer active:scale-[0.99] flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center font-bold text-sm flex-shrink-0">
                      {(st.display_name || st.full_name || 'ST').slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-bold text-slate-900 truncate">
                        {st.display_name || st.full_name || 'Student Name'}
                      </h3>
                      <div className="flex flex-wrap items-center gap-x-2 text-xs text-slate-500 mt-0.5">
                        <span>Class: {assignedClassDisplayName}</span>
                        <span>•</span>
                        <span>ID: {st.admission_number || `SCH${st.id}`}</span>
                        {st.roll_number && (
                          <>
                            <span>•</span>
                            <span>Roll: {st.roll_number}</span>
                          </>
                        )}
                        {st.mobile && (
                          <>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <Phone className="w-3 h-3" /> {st.mobile}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add Student Modal (Scoped to Teacher's Class) */}
      {showAddModal && assignedSection && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 space-y-5 shadow-2xl border border-slate-100 my-8">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Add Student to {assignedClassDisplayName}</h2>
                <p className="text-xs text-slate-500">Student profile automatically assigned to your class</p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {studentModalFeedback && (
              <div
                className={`p-3.5 rounded-xl border text-xs font-medium flex items-center gap-2 ${
                  studentModalFeedback.type === 'success'
                    ? 'bg-blue-50 border-blue-200 text-blue-800'
                    : 'bg-rose-50 border-rose-200 text-rose-800'
                }`}
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{studentModalFeedback.message}</span>
              </div>
            )}

            <form onSubmit={handleCreateStudent} className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
              {/* Assigned Class Banner (Locked) */}
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider block">
                    Target Class (Automatically Bound)
                  </span>
                  <span className="text-xs font-bold text-blue-900">
                    {assignedClassDisplayName}
                  </span>
                </div>
                <span className="text-[10px] font-semibold bg-blue-200/70 text-blue-800 px-2 py-0.5 rounded-md flex items-center gap-1">
                  <Lock className="w-2.5 h-2.5" /> Enforced by Server
                </span>
              </div>

              {/* Identity Details */}
              <div>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                  1. Student Identity
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.full_name}
                      onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                      placeholder="e.g. Rahul Sharma"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1 flex items-center justify-between">
                      <span>Admission Number</span>
                      <span className="text-[10px] text-blue-600 font-normal">Auto-generated if empty</span>
                    </label>
                    <input
                      type="text"
                      value={formData.admission_number}
                      onChange={(e) => setFormData({ ...formData, admission_number: e.target.value })}
                      placeholder="e.g. SCH2026001"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Roll Number
                    </label>
                    <input
                      type="text"
                      value={formData.roll_number}
                      onChange={(e) => setFormData({ ...formData, roll_number: e.target.value })}
                      placeholder="e.g. 15"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Gender
                    </label>
                    <select
                      value={formData.gender}
                      onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
                    >
                      <option value="MALE">Male</option>
                      <option value="FEMALE">Female</option>
                      <option value="OTHER">Other</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Date of Birth
                    </label>
                    <input
                      type="date"
                      value={formData.date_of_birth}
                      onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Blood Group
                    </label>
                    <input
                      type="text"
                      value={formData.blood_group}
                      onChange={(e) => setFormData({ ...formData, blood_group: e.target.value })}
                      placeholder="e.g. O+, A+, B+"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Admission Date
                    </label>
                    <input
                      type="date"
                      value={formData.admission_date}
                      onChange={(e) => setFormData({ ...formData, admission_date: e.target.value })}
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="student@example.com"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Parent & Guardian Details */}
              <div className="pt-2 border-t border-slate-100">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                  2. Parent / Guardian Details
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Father's Name
                    </label>
                    <input
                      type="text"
                      value={formData.father_name}
                      onChange={(e) => setFormData({ ...formData, father_name: e.target.value })}
                      placeholder="Father's Full Name"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Father's Mobile
                    </label>
                    <input
                      type="tel"
                      value={formData.father_mobile}
                      onChange={(e) => setFormData({ ...formData, father_mobile: e.target.value })}
                      placeholder="e.g. 9876543210"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Mother's Name
                    </label>
                    <input
                      type="text"
                      value={formData.mother_name}
                      onChange={(e) => setFormData({ ...formData, mother_name: e.target.value })}
                      placeholder="Mother's Full Name"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Mother's Mobile
                    </label>
                    <input
                      type="tel"
                      value={formData.mother_mobile}
                      onChange={(e) => setFormData({ ...formData, mother_mobile: e.target.value })}
                      placeholder="e.g. 9876543211"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Guardian's Mobile
                    </label>
                    <input
                      type="tel"
                      value={formData.guardian_mobile}
                      onChange={(e) => setFormData({ ...formData, guardian_mobile: e.target.value })}
                      placeholder="e.g. 9876543212"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Residential Address
                    </label>
                    <input
                      type="text"
                      value={formData.address}
                      onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                      placeholder="Complete residential address"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="flex gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="submit"
                  disabled={submittingStudent}
                  className="flex-1 h-11 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
                >
                  <Save className="w-4 h-4" />
                  {submittingStudent ? 'Saving Student...' : 'Add Student to Class'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-6 h-11 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold active:scale-95 transition-all"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherStudents;