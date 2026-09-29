// src/pages/principal/Settings.tsx
import React, { useEffect, useState } from 'react';
import { settingsService } from '../../services/settings';
import { PrincipalSettings } from '../../types/settings';

import { Save, Settings2 } from 'lucide-react';
import { LoadingSkeleton } from '../../components/shared';
import { AcademicYearSection } from '../../components/settings/AcademicYearSection';

/** The free-text school fields this form edits.
 * NOTE: `academic_year` is NOT one of them. It is derived server-side from the
 * school's ACTIVE AcademicYear record and is displayed (and fully managed:
 * create / list / activate / view) by the Academic Year section below, so the
 * two can never contradict each other. */
type EditableField = 'school_name' | 'school_address' | 'phone_number' | 'email' | 'school_timings';

export const PrincipalSettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<PrincipalSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    settingsService
      .getPrincipalSettings()
      .then((data) => setSettings(data))
      .catch(() => setError('Failed to load settings'))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const { id: _id, ...rest } = settings;
      // academic_year is derived server-side from the active AcademicYear —
      // never send it back as an editable value.
      const { academic_year: _ay, ...payload } = rest;
      const updated = await settingsService.updatePrincipalSettings(payload);
      setSettings(updated);
      setMessage('School settings updated successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setError('Failed to update settings.');
    } finally {
      setSaving(false);
    }
  };

  const fields: { key: EditableField; label: string; type?: string }[] = [
    { key: 'school_name', label: 'School Name' },
    { key: 'school_address', label: 'School Address' },
    { key: 'phone_number', label: 'Phone Number', type: 'tel' },
    { key: 'email', label: 'Email Address', type: 'email' },
    { key: 'school_timings', label: 'School Timings' },
  ];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">School Settings</h1>
        <p className="text-xs text-slate-500">Manage school configuration and preferences</p>
      </div>

      {message && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-xs font-medium">
          ✓ {message}
        </div>
      )}
      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : !settings ? (
        <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center text-rose-600 text-sm">
          Failed to load settings.
        </div>
      ) : (
        <form onSubmit={handleSave} className="space-y-3">
          <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
              <Settings2 className="w-4 h-4 text-emerald-600" />
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">School Information</h3>
            </div>
            {fields.map(({ key, label, type }) => (
              <div key={key}>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">{label}</label>
                <input
                  type={type ?? 'text'}
                  value={settings[key] ?? ''}
                  onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
                  className="w-full h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>
            ))}
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full h-12 rounded-2xl bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98] text-white font-bold text-sm shadow-sm transition-all disabled:opacity-60 flex items-center justify-center gap-2"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving Changes...' : 'Save Settings'}
          </button>
        </form>
      )}

      {/* Academic Year: create, list every year, see which one is Active,
          activate another, and pick which year's data to view. */}
      <AcademicYearSection />
    </div>
  );
};

export default PrincipalSettingsPage;
