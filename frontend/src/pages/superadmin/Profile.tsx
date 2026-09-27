// src/pages/superadmin/Profile.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { Phone, Shield, Mail, Key, Pencil, X, Check } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { LoadingSkeleton, ErrorState } from '../../components/shared';
import ProfilePhotoUpload from '../../components/shared/ProfilePhotoUpload';
import { usersService } from '../../services/users';
import { errorMessage } from '../../helpers/errorMessage';
import { AppUser } from '../../types';
import type { User } from '../../contexts/AuthContext';

export const SuperAdminProfile: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [profile, setProfile] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadFailed, setLoadFailed] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<boolean>(false);
  const [editing, setEditing] = useState<boolean>(false);
  const [displayName, setDisplayName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [mobile, setMobile] = useState<string>('');
  const [saved, setSaved] = useState<boolean>(false);

  // This page previously read only from AuthContext, whose `User` type has no
  // `email` field, so it always fell through to the hard-coded
  // "admin@scholaris.edu" placeholder and offered no way to edit anything.
  // It now uses the existing GET/PATCH /users/me endpoints.
  const load = useCallback(async () => {
    setLoading(true);
    setLoadFailed(false);
    setError(null);
    try {
      const data = await usersService.getMyUserProfile();
      setProfile(data);
      setDisplayName(data.display_name ?? '');
      setEmail(data.email ?? '');
      setMobile(data.mobile ?? '');
    } catch (err) {
      setLoadFailed(true);
      setError(errorMessage(err, 'Unable to load the admin profile.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await usersService.updateMyUserProfile({
        display_name: displayName.trim(),
        email: email.trim() || undefined,
        mobile: mobile.trim(),
      } as any);
      setProfile(updated);
      setEditing(false);
      setSaved(true);
      await refreshUser();
    } catch (err) {
      setError(errorMessage(err, 'Failed to update the profile.'));
    } finally {
      setSaving(false);
    }
  };

  const displayNameValue = profile?.display_name || user?.display_name || 'Super Administrator';

  return (
    <div className="space-y-4 max-w-xl mx-auto">
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-2xs p-4">
        <ProfilePhotoUpload />
      </div>
      <div>
        <h1 className="text-xl font-bold text-slate-900">Admin Profile</h1>
        <p className="text-xs text-slate-500">Account credentials and platform role</p>
      </div>

      {error && !loadFailed && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}
      {saved && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-xs flex items-center gap-1.5">
          <Check className="w-3.5 h-3.5" /> Profile updated successfully.
        </div>
      )}

      {loadFailed ? (
        <ErrorState title="Load Error" message={error || 'Failed to load the profile'} onRetry={load} />
      ) : loading ? (
        <LoadingSkeleton type="card" count={1} />
      ) : (
        <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center gap-4 pb-4 border-b border-slate-100">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600 text-white flex items-center justify-center font-bold text-lg shadow-md shadow-indigo-600/20">
              {displayNameValue.slice(0, 2).toUpperCase()}
            </div>
            <div className="flex-1">
              <h2 className="text-base font-bold text-slate-900">{displayNameValue}</h2>
              <span className="inline-flex items-center gap-1 text-xs text-indigo-600 font-semibold bg-indigo-50 px-2.5 py-0.5 rounded-full mt-1">
                <Shield className="w-3 h-3" /> {profile?.role || user?.role || 'SUPER_ADMIN'}
              </span>
            </div>
            {!editing && (
              <button
                onClick={() => { setEditing(true); setSaved(false); }}
                className="h-9 px-3 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold flex items-center gap-1.5 hover:bg-slate-50"
              >
                <Pencil className="w-3.5 h-3.5" /> Edit
              </button>
            )}
          </div>

          {editing ? (
            <form onSubmit={handleSave} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="sa-name">Full Name</label>
                <input
                  id="sa-name"
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  required
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="sa-mobile">Mobile Number</label>
                <input
                  id="sa-mobile"
                  type="tel"
                  value={mobile}
                  onChange={e => setMobile(e.target.value)}
                  required
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="sa-email">Email Address</label>
                <input
                  id="sa-email"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="No email registered"
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => { setEditing(false); load(); }}
                  className="h-10 px-4 rounded-xl border border-slate-200 text-slate-700 text-xs font-bold flex items-center gap-1.5"
                >
                  <X className="w-3.5 h-3.5" /> Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="h-10 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold disabled:opacity-50"
                >
                  {saving ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-3 text-xs sm:text-sm">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-600">
                  <Phone className="w-4 h-4 text-slate-400" />
                  <span>Mobile Number</span>
                </div>
                <span className="font-semibold text-slate-900">{profile?.mobile || user?.mobile || '-'}</span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-600">
                  <Mail className="w-4 h-4 text-slate-400" />
                  <span>Email Address</span>
                </div>
                <span className="font-semibold text-slate-900">
                  {profile?.email || <span className="text-slate-400 font-normal">No email registered</span>}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-600">
                  <Key className="w-4 h-4 text-slate-400" />
                  <span>Security Token</span>
                </div>
                <span className="font-semibold text-slate-900">Valid JWT Session</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Local shape of the auth context user, kept here so this page does not need to
// import the context's internal type.
export default SuperAdminProfile;
