// src/pages/principal/Teachers.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Plus, Phone, Briefcase, Calendar, ChevronRight, Mail, X, Save, AlertCircle } from 'lucide-react';
import { teachersService } from '../../services/teachers';
import { Teacher } from '../../types';
import { EmptyState, LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';

export const Teachers: React.FC = () => {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [modalFeedback, setModalFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // New Faculty Form State
  const [formData, setFormData] = useState({
    full_name: '',
    employee_id: '',
    mobile: '',
    email: '',
    qualification: '',
    department: '',
    specialization: '',
    joining_date: new Date().toISOString().slice(0, 10),
  });

  const navigate = useNavigate();

  const fetchTeachers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await teachersService.listTeachers();
      setTeachers(data || []);
    } catch (err) {
      console.error('Failed to load faculty members', err);
      setError('Unable to load faculty list. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeachers();
  }, []);

  const handleCreateTeacher = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.full_name.trim()) {
      setModalFeedback({ type: 'error', message: 'Teacher full name is required.' });
      return;
    }
    if (!formData.mobile.trim()) {
      setModalFeedback({ type: 'error', message: 'Mobile number is required for login credentials.' });
      return;
    }

    try {
      setSubmitting(true);
      setModalFeedback(null);

      const payload = {
        full_name: formData.full_name.trim(),
        display_name: formData.full_name.trim(),
        employee_id: formData.employee_id.trim() || undefined,
        mobile: formData.mobile.trim(),
        email: formData.email.trim() || undefined,
        qualification: formData.qualification.trim() || undefined,
        department: formData.department.trim() || undefined,
        specialization: formData.specialization.trim() || undefined,
        joining_date: formData.joining_date || undefined,
      };

      await teachersService.createTeacher(payload);
      setShowAddModal(false);
      setFormData({
        full_name: '',
        employee_id: '',
        mobile: '',
        email: '',
        qualification: '',
        department: '',
        specialization: '',
        joining_date: new Date().toISOString().slice(0, 10),
      });
      fetchTeachers();
    } catch (err: any) {
      console.error('Failed to create teacher', err);
      setModalFeedback({
        type: 'error',
        message: err?.response?.data?.detail || 'Failed to onboard faculty member. Please verify inputs.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Faculty Management</h1>
          <p className="text-xs text-slate-500">All teaching staff & faculty profiles</p>
        </div>
        <button
          onClick={() => {
            setShowAddModal(true);
            setModalFeedback(null);
          }}
          className="h-10 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          Onboard Faculty
        </button>
      </div>

      {error && <ErrorState message={error} onRetry={fetchTeachers} />}

      {/* Teachers List */}
      {loading ? (
        <LoadingSkeleton type="card" count={4} />
      ) : teachers.length === 0 ? (
        <EmptyState
          title="No faculty members found."
          description="No teachers have been registered for this school yet."
          icon={<Users className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-3">
          {teachers.map((t) => (
            <div
              key={t.id}
              onClick={() => navigate(`/principal/teachers/${t.id}`)}
              className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all cursor-pointer active:scale-[0.99] space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0">
                    {(t.display_name || t.full_name || 'TC').slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 leading-tight">
                      {t.display_name || t.full_name || 'Faculty Member'}
                    </h3>
                    <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
                      <span>ID: {t.employee_id || `EMP${t.id}`}</span>
                      {t.role_type && (
                        <>
                          <span>•</span>
                          <span className="font-semibold text-emerald-700">{t.role_type}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={t.status || (t.is_active ? 'ACTIVE' : 'INACTIVE')} />
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2 border-t border-slate-100 text-xs">
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Phone className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                  <span className="truncate">{t.mobile || 'No Mobile'}</span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Briefcase className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                  <span className="truncate">{t.qualification || t.specialization || t.department || 'Faculty'}</span>
                </div>
                {t.joining_date && (
                  <div className="flex items-center gap-1.5 text-slate-600 col-span-2 sm:col-span-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                    <span className="truncate">Joined: {t.joining_date}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Onboard Faculty Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 space-y-5 shadow-2xl border border-slate-100 my-8">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Onboard Faculty Member</h2>
                <p className="text-xs text-slate-500">Teacher credentials, employee identifier, and qualifications</p>
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

            <form onSubmit={handleCreateTeacher} className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Full Name */}
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    placeholder="e.g. Dr. Ramesh Kumar"
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                {/* Employee ID */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1 flex items-center justify-between">
                    <span>Employee ID</span>
                    <span className="text-[10px] text-emerald-600 font-normal">Auto if blank</span>
                  </label>
                  <input
                    type="text"
                    value={formData.employee_id}
                    onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                    placeholder="e.g. EMP2026001"
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                {/* Mobile Phone */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Mobile Phone *
                  </label>
                  <input
                    type="tel"
                    required
                    value={formData.mobile}
                    onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                    placeholder="e.g. 9876543210"
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                {/* Email Address */}
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="teacher@school.edu"
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                {/* Qualification */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Qualification
                  </label>
                  <input
                    type="text"
                    value={formData.qualification}
                    onChange={(e) => setFormData({ ...formData, qualification: e.target.value })}
                    placeholder="e.g. M.Sc, B.Ed"
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                {/* Department */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Department
                  </label>
                  <input
                    type="text"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    placeholder="e.g. Mathematics, Science"
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                {/* Date of Joining */}
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Date of Joining
                  </label>
                  <input
                    type="date"
                    value={formData.joining_date}
                    onChange={(e) => setFormData({ ...formData, joining_date: e.target.value })}
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 h-11 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
                >
                  <Save className="w-4 h-4" />
                  {submitting ? 'Saving Faculty...' : 'Complete Onboarding'}
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

export default Teachers;
