// src/pages/superadmin/EditSchool.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Building } from 'lucide-react';
import { schoolsService } from '../../services/schools';
import { LoadingSkeleton } from '../../components/shared';

export const SuperAdminEditSchool: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [form, setForm] = useState({ name: '', code: '', is_active: true });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!id) return;
    schoolsService.getSchool(Number(id))
      .then((school) => {
        setForm({ name: school.name, code: school.code, is_active: school.is_active });
      })
      .catch(() => setError('Failed to load school'))
      .finally(() => setLoading(false));
  }, [id]);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!form.name.trim()) errors.name = 'School name is required';
    if (!form.code.trim()) errors.code = 'School code is required';
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate() || !id) return;
    setSaving(true);
    setError(null);
    try {
      await schoolsService.updateSchool(Number(id), form);
      navigate(`/superadmin/schools/${id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update school');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSkeleton type="form" count={3} />;

  return (
    <div className="max-w-lg mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(`/superadmin/schools/${id}`)} className="p-2 rounded-xl hover:bg-slate-100">
          <ArrowLeft className="w-5 h-5 text-slate-600" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-900">Edit School</h1>
          <p className="text-xs text-slate-500">Update school information</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
        <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center">
            <Building className="w-5 h-5 text-indigo-600" />
          </div>
          <p className="text-sm font-bold text-slate-900">Edit School Details</p>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
        )}

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">School Name <span className="text-rose-500">*</span></label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => { setForm(p => ({ ...p, name: e.target.value })); setFieldErrors(p => { const n={...p}; delete n.name; return n; }); }}
            className={`w-full h-11 px-3.5 rounded-xl border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${fieldErrors.name ? 'border-rose-400' : 'border-slate-200'}`}
          />
          {fieldErrors.name && <p className="text-xs text-rose-500">{fieldErrors.name}</p>}
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">School Code <span className="text-rose-500">*</span></label>
          <input
            type="text"
            value={form.code}
            onChange={(e) => { setForm(p => ({ ...p, code: e.target.value.toUpperCase() })); setFieldErrors(p => { const n={...p}; delete n.code; return n; }); }}
            maxLength={10}
            className={`w-full h-11 px-3.5 rounded-xl border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${fieldErrors.code ? 'border-rose-400' : 'border-slate-200'}`}
          />
          {fieldErrors.code && <p className="text-xs text-rose-500">{fieldErrors.code}</p>}
        </div>

        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="is_active_edit"
            checked={form.is_active}
            onChange={(e) => setForm(p => ({ ...p, is_active: e.target.checked }))}
            className="w-4 h-4 rounded text-indigo-600"
          />
          <label htmlFor="is_active_edit" className="text-sm text-slate-700">Active school</label>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate(`/superadmin/schools/${id}`)}
            className="flex-1 h-11 rounded-xl border border-slate-200 text-sm text-slate-700 font-semibold hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="flex-1 h-11 rounded-xl bg-indigo-600 text-white font-bold text-sm hover:bg-indigo-700 disabled:opacity-60"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SuperAdminEditSchool;