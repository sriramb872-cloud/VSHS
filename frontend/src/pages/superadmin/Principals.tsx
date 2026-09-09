// src/pages/superadmin/Principals.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Search, Plus, X, AlertCircle } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';
import { principalsService } from '../../services/principals';
import { schoolsService } from '../../services/schools';
import { Principal, School } from '../../types';

export const SuperAdminPrincipals: React.FC = () => {
  const [principals, setPrincipals] = useState<Principal[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [modalFeedback, setModalFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Assign School Modal State (for fixing principals with missing school_id)
  const [assignModalPrincipal, setAssignModalPrincipal] = useState<Principal | null>(null);
  const [assignSchoolId, setAssignSchoolId] = useState<string>('');
  const [assignSubmitting, setAssignSubmitting] = useState(false);
  const [assignFeedback, setAssignFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // New Principal Form State
  const [formData, setFormData] = useState({
    school_id: '',
    full_name: '',
    mobile: '',
    email: '',
  });

  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [principalsData, schoolsData] = await Promise.all([
        principalsService.listPrincipals(),
        schoolsService.listSchools(),
      ]);
      setPrincipals(principalsData || []);
      setSchools(schoolsData || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const schoolMap = useMemo(() => {
    const map = new Map<number, string>();
    schools.forEach((s) => map.set(s.id, s.name));
    return map;
  }, [schools]);

  const assignedSchoolIds = useMemo(() => {
    return new Set(principals.filter((p) => p.school_id).map((p) => p.school_id as number));
  }, [principals]);

  const filtered = principals.filter(
    (p) =>
      p.display_name?.toLowerCase().includes(search.toLowerCase()) ||
      p.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      p.mobile?.includes(search) ||
      (p.school_id && schoolMap.get(p.school_id)?.toLowerCase().includes(search.toLowerCase()))
  );

  const handleCreatePrincipal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.school_id) {
      setModalFeedback({ type: 'error', message: 'Please select a school.' });
      return;
    }
    if (!formData.full_name.trim()) {
      setModalFeedback({ type: 'error', message: 'Principal full name is required.' });
      return;
    }
    if (!formData.mobile.trim()) {
      setModalFeedback({ type: 'error', message: 'Mobile number is required for login credentials.' });
      return;
    }

    try {
      setSubmitting(true);
      setModalFeedback(null);

      await principalsService.createPrincipal({
        school_id: Number(formData.school_id),
        full_name: formData.full_name.trim(),
        mobile: formData.mobile.trim(),
        email: formData.email.trim() || undefined,
      });

      setShowAddModal(false);
      setFormData({
        school_id: '',
        full_name: '',
        mobile: '',
        email: '',
      });
      fetchData();
    } catch (err: any) {
      console.error('Failed to onboard principal', err);
      setModalFeedback({
        type: 'error',
        message: err?.response?.data?.detail || 'Failed to onboard principal. Please check your inputs.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleAssignSchool = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignModalPrincipal || !assignSchoolId) {
      setAssignFeedback({ type: 'error', message: 'Please select a school to assign.' });
      return;
    }

    try {
      setAssignSubmitting(true);
      setAssignFeedback(null);
      await principalsService.updatePrincipal(assignModalPrincipal.id, {
        school_id: Number(assignSchoolId),
      });
      setAssignModalPrincipal(null);
      setAssignSchoolId('');
      fetchData();
    } catch (err: any) {
      console.error('Failed to assign school', err);
      setAssignFeedback({
        type: 'error',
        message: err?.response?.data?.detail || 'Failed to assign school. Please try again.',
      });
    } finally {
      setAssignSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Principals</h1>
          <p className="text-xs text-slate-500">School administrators across all registered institutions</p>
        </div>
        <button
          onClick={() => {
            setShowAddModal(true);
            setModalFeedback(null);
          }}
          className="h-10 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          Onboard Principal
        </button>
      </div>

      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search principals by name, mobile, or school..."
          className="w-full h-11 pl-10 pr-4 rounded-xl border border-slate-200 bg-white text-xs sm:text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {error && <ErrorState title="Load Error" message="Failed to load principals" onRetry={fetchData} />}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No Principals Found"
          description={search ? 'No principals match your search.' : 'No principals registered yet.'}
          icon={<User className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {filtered.map((p) => {
            const isUnassigned = !p.school_id;
            return (
              <MobileListItem
                key={p.id}
                title={p.display_name || p.full_name || 'Principal'}
                subtitle={p.mobile || p.email || 'No contact'}
                icon={<User className="w-5 h-5 text-purple-600" />}
                avatarBg="bg-purple-50 text-purple-600"
                badge={<StatusBadge status={p.is_active || 'INACTIVE'} />}
                metaText={isUnassigned ? 'No school assigned (Click to assign)' : (schoolMap.get(p.school_id as number) || `School #${p.school_id}`)}
                onClick={
                  isUnassigned
                    ? () => {
                        setAssignModalPrincipal(p);
                        setAssignSchoolId('');
                        setAssignFeedback(null);
                      }
                    : undefined
                }
              />
            );
          })}
        </div>
      )}

      {/* Onboard Principal Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 space-y-5 shadow-2xl border border-slate-100 my-8">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Onboard Principal</h2>
                <p className="text-xs text-slate-500">Assign an administrator to an onboarding school</p>
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

            {schools.length === 0 ? (
              <div className="p-5 rounded-2xl bg-amber-50 border border-amber-200 text-center space-y-3">
                <p className="text-sm font-semibold text-amber-900">Please onboard a school first.</p>
                <p className="text-xs text-amber-700 max-w-sm mx-auto">
                  No schools currently exist in the system. A principal must be assigned to an active school.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    navigate('/superadmin/schools/create');
                  }}
                  className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-all"
                >
                  Onboard School
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreatePrincipal} className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    School Assignment *
                  </label>
                  <select
                    required
                    value={formData.school_id}
                    onChange={(e) => setFormData({ ...formData, school_id: e.target.value })}
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                  >
                    <option value="">Select a school...</option>
                    {schools.map((s) => {
                      const isAssigned = assignedSchoolIds.has(s.id);
                      return (
                        <option key={s.id} value={s.id} disabled={isAssigned}>
                          {s.name} {isAssigned ? '(Principal already assigned)' : ''}
                        </option>
                      );
                    })}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    placeholder="e.g. Dr. Sunita Rao"
                    className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Mobile Number *
                    </label>
                    <input
                      type="tel"
                      required
                      value={formData.mobile}
                      onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                      placeholder="e.g. 9876543210"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Email Address
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="principal@school.edu"
                      className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-xl transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50"
                  >
                    {submitting ? 'Onboarding...' : 'Onboard Principal'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Assign School Modal */}
      {assignModalPrincipal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-5 shadow-2xl border border-slate-100 my-8">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Assign School</h2>
                <p className="text-xs text-slate-500">
                  Assign an institution to {assignModalPrincipal.display_name || assignModalPrincipal.full_name || 'Principal'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setAssignModalPrincipal(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {assignFeedback && (
              <div
                className={`p-3.5 rounded-xl border text-xs font-medium flex items-center gap-2 ${
                  assignFeedback.type === 'success'
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : 'bg-rose-50 border-rose-200 text-rose-800'
                }`}
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{assignFeedback.message}</span>
              </div>
            )}

            <form onSubmit={handleAssignSchool} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Select School *
                </label>
                <select
                  required
                  value={assignSchoolId}
                  onChange={(e) => setAssignSchoolId(e.target.value)}
                  className="w-full h-10 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                >
                  <option value="">Select a school...</option>
                  {schools.map((s) => {
                    const isAssigned = assignedSchoolIds.has(s.id);
                    return (
                      <option key={s.id} value={s.id} disabled={isAssigned}>
                        {s.name} {isAssigned ? '(Principal already assigned)' : ''}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setAssignModalPrincipal(null)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={assignSubmitting}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50"
                >
                  {assignSubmitting ? 'Assigning...' : 'Assign School'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SuperAdminPrincipals;