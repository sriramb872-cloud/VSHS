// src/pages/superadmin/CreateSchool.tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Building } from 'lucide-react';
import { schoolsService } from '../../services/schools';
import { SchoolCreatePayload } from '../../types';

export const SuperAdminCreateSchool: React.FC = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState<SchoolCreatePayload>({ name: '', code: '', is_active: true });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!form.name.trim()) errors.name = 'School name is required';
    if (!form.code.trim()) errors.code = 'School code is required';
    else if (form.code.length > 10) errors.code = 'Code must be 10 characters or less';
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    setError(null);
    try {
      const school = await schoolsService.createSchool(form);
      navigate(`/superadmin/schools/${school.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create school');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: keyof SchoolCreatePayload, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (fieldErrors[field as string]) {
      setFieldErrors((prev) => { const n = { ...prev }; delete n[field as string]; return n; });
    }
  };

  return (
    <div className="max-w-lg mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/superadmin/schools')} className="p-2 rounded-xl hover:bg-slate-100">
          <ArrowLeft className="w-5 h-5 text-slate-600" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-900">New School</h1>
          <p className="text-xs text-slate-500">Onboard a new institution</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
        <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center">
            <Building className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900">School Information</p>
            <p className="text-xs text-slate-400">Enter school details below</p>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
        )}

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">School Name <span className="text-rose-500">*</span></label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => handleChange('name', e.target.value)}
            placeholder="e.g. Springfield High School"
            className={`w-full h-11 px-3.5 rounded-xl border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${fieldErrors.name ? 'border-rose-400' : 'border-slate-200'}`}
          />
          {fieldErrors.name && <p className="text-xs text-rose-500">{fieldErrors.name}</p>}
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700">School Code <span className="text-rose-500">*</span></label>
          <input
            type="text"
            value={form.code}
            onChange={(e) => handleChange('code', e.target.value.toUpperCase())}
            placeholder="e.g. SHS001"
            maxLength={10}
            className={`w-full h-11 px-3.5 rounded-xl border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${fieldErrors.code ? 'border-rose-400' : 'border-slate-200'}`}
          />
          {fieldErrors.code && <p className="text-xs text-rose-500">{fieldErrors.code}</p>}
        </div>

        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="is_active"
            checked={form.is_active}
            onChange={(e) => handleChange('is_active', e.target.checked)}
            className="w-4 h-4 rounded text-indigo-600"
          />
          <label htmlFor="is_active" className="text-sm text-slate-700">Active school</label>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate('/superadmin/schools')}
            className="flex-1 h-11 rounded-xl border border-slate-200 text-sm text-slate-700 font-semibold hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 h-11 rounded-xl bg-indigo-600 text-white font-bold text-sm hover:bg-indigo-700 disabled:opacity-60"
          >
            {loading ? 'Creating...' : 'Create School'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SuperAdminCreateSchool;