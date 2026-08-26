// src/pages/principal/Students.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Search, ChevronRight, GraduationCap, Plus, X, Save, AlertCircle, CheckCircle, Sparkles } from 'lucide-react';
import { studentsService } from '../../services/students';
import { gradesService } from '../../services/grades';
import { sectionsService } from '../../services/sections';
import { Student, Grade, Section } from '../../types';
import { EmptyState, LoadingSkeleton, ErrorState } from '../../components/shared';

export const Students: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [grades, setGrades] = useState<Grade[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [modalFeedback, setModalFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // New Student Form State
  const [formData, setFormData] = useState({
    full_name: '',
    admission_number: '',
    admission_date: new Date().toISOString().slice(0, 10),
    roll_number: '',
    grade_id: '',
    section_id: '',
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

  const navigate = useNavigate();

  const fetchStudents = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await studentsService.listStudents();
      setStudents(data || []);
    } catch (err) {
      console.error('Failed to load student roster', err);
      setError('Unable to load student roster.');
    } finally {
      setLoading(false);
    }
  };

  const loadGradesAndSections = async () => {
    try {
      const [gradesData, sectionsData] = await Promise.allSettled([
        gradesService.listGrades(),
        sectionsService.listSections(),
      ]);
      if (gradesData.status === 'fulfilled') setGrades(gradesData.value || []);
      if (sectionsData.status === 'fulfilled') setSections(sectionsData.value || []);
    } catch (err) {
      console.error('Failed to load grades/sections', err);
    }
  };

  useEffect(() => {
    fetchStudents();
    loadGradesAndSections();
  }, []);

  const handleCreateStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.full_name.trim()) {
      setModalFeedback({ type: 'error', message: 'Student full name is required.' });
      return;
    }

    try {
      setSubmitting(true);
      setModalFeedback(null);

      const payload = {
        full_name: formData.full_name.trim(),
        display_name: formData.full_name.trim(),
        admission_number: formData.admission_number.trim() || undefined,
        admission_date: formData.admission_date || undefined,
        roll_number: formData.roll_number.trim() || undefined,
        grade_id: formData.grade_id ? Number(formData.grade_id) : undefined,
        section_id: formData.section_id ? Number(formData.section_id) : undefined,
        date_of_birth: formData.date_of_birth || undefined,
        gender: formData.gender || undefined,
        blood_group: formData.blood_group.trim() || undefined,
        father_name: formData.father_name.trim() || undefined,
        father_mobile: formData.father_mobile.trim() || undefined,
        mother_name: formData.mother_name.trim() || undefined,
        mother_mobile: formData.mother_mobile.trim() || undefined,
        guardian_mobile: formData.guardian_mobile.trim() || formData.father_mobile.trim() || formData.mother_mobile.trim() || undefined,
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
        grade_id: '',
        section_id: '',
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
      fetchStudents();
    } catch (err: any) {
      console.error('Failed to create student', err);
      setModalFeedback({
        type: 'error',
        message: err?.response?.data?.detail || 'Failed to onboard student. Please verify all inputs.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const filteredStudents = students.filter(
    (st) =>
      (st.display_name || st.full_name || '').toLowerCase().includes(search.toLowerCase()) ||
      (st.admission_number || '').toLowerCase().includes(search.toLowerCase()) ||
      (st.mobile || '').includes(search) ||
      (st.grade_name || '').toLowerCase().includes(search.toLowerCase()) ||
      (st.section_name || '').toLowerCase().includes(search.toLowerCase())
  );

  const availableSections = formData.grade_id
    ? sections.filter((s) => s.grade_id === Number(formData.grade_id))
    : sections;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Students Roster</h1>
          <p className="text-xs text-slate-500">All enrolled student profiles & academic records</p>
        </div>
        <button
          onClick={() => {
            setShowAddModal(true);
            setModalFeedback(null);
          }}
          className="h-10 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          Onboard Student
        </button>
      </div>

      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by student name, admission no, class or mobile..."
          className="w-full h-11 pl-10 pr-4 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs sm:text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
        />
      </div>

      {error && <ErrorState message={error} onRetry={fetchStudents} />}

      {loading ? (
        <LoadingSkeleton type="card" count={4} />
      ) : filteredStudents.length === 0 ? (
        <EmptyState
          title="No Students Found"
          description={search ? "No student record matches your search." : "No student profiles enrolled yet."}
          icon={<Users className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {filteredStudents.map((st) => (
            <div
              key={st.id}
              onClick={() => navigate(`/principal/students/${st.id}`)}
              className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all cursor-pointer active:scale-[0.99] flex items-center justify-between gap-3"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-11 h-11 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-sm flex-shrink-0">
                  {(st.display_name || st.full_name || 'ST').slice(0, 2).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-bold text-slate-900 truncate">
                    {st.display_name || st.full_name || 'Student Name'}
                  </h3>
                  <div className="flex flex-wrap items-center gap-x-2 text-xs text-slate-500 mt-0.5">
                    <span>
                      {st.grade_name ? `${st.grade_name}${st.section_name ? ` (${st.section_name})` : ''}` : 'Unassigned'}
                    </span>
                    <span>•</span>
                    <span>ID: {st.admission_number || `SCH${st.id}`}</span>
                    {st.roll_number && (
                      <>
                        <span>•</span>
                        <span>Roll: {st.roll_number}</span>
                      </>
                    )}
                    {st.status && (
                      <>
                        <span>•</span>
                        <span className="font-semibold text-teal-700">{st.status}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
            </div>
          ))}
        </div>
      )}

      {/* Onboard Student Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 space-y-5 shadow-2xl border border-slate-100 my-8">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Onboard New Student</h2>
                <p className="text-xs text-slate-500">Student identity, guardian info, and class enrollment</p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {modalFeedback && (
              <div
                className={`p-3.5 rounded-xl border text-xs font-medium flex items-center gap-2 ${
                  modalFeedback.type === 'success'
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : 'bg-rose-50 border-rose-200 text-rose-800'
                }`}
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{modalFeedback.message}</span>
              </div>
            )}

            <form onSubmit={handleCreateStudent} className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
              {/* Identity Details */}
              <div>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">1. Identity Information</h3>
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
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1 flex items-center justify-between">
                      <span>Student ID (Admission No)</span>
                      <span className="text-[10px] text-emerald-600 font-normal">Auto-generated if empty</span>
                    </label>
                    <input
                      type="text"
                      value={formData.admission_number}
                      onChange={(e) => setFormData({ ...formData, admission_number: e.target.value })}
                      placeholder="e.g. SCH2026001 (or leave blank)"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Date of Birth
                    </label>
                    <input
                      type="date"
                      value={formData.date_of_birth}
                      onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Gender
                    </label>
                    <select
                      value={formData.gender}
                      onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none bg-white"
                    >
                      <option value="MALE">Male</option>
                      <option value="FEMALE">Female</option>
                      <option value="OTHER">Other</option>
                    </select>
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
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
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
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Class & Enrollment */}
              <div className="pt-2 border-t border-slate-100">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">2. Academic Enrollment</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Grade / Class
                    </label>
                    <select
                      value={formData.grade_id}
                      onChange={(e) => setFormData({ ...formData, grade_id: e.target.value, section_id: '' })}
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none bg-white"
                    >
                      <option value="">Select Grade</option>
                      {grades.map((g) => (
                        <option key={g.id} value={g.id}>{g.name}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Section
                    </label>
                    <select
                      value={formData.section_id}
                      onChange={(e) => setFormData({ ...formData, section_id: e.target.value })}
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none bg-white"
                    >
                      <option value="">Select Section</option>
                      {availableSections.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
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
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Guardian Contact Info */}
              <div className="pt-2 border-t border-slate-100">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">3. Parent / Guardian Details</h3>
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
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
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
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
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
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
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
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
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
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="flex gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 h-11 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
                >
                  <Save className="w-4 h-4" />
                  {submitting ? 'Saving Student...' : 'Complete Onboarding'}
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

export default Students;