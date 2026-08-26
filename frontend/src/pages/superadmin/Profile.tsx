// src/pages/superadmin/Profile.tsx
import React, { useState, useEffect } from 'react';
import { User, Phone, Shield, Mail, Key } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { LoadingSkeleton } from '../../components/shared';

export const SuperAdminProfile: React.FC = () => {
  const { user } = useAuth();
  const [profile, setProfile] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Populate profile from AuthContext or endpoint
    if (user) {
      setProfile(user);
    }
    setLoading(false);
  }, [user]);

  return (
    <div className="space-y-4 max-w-xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Admin Profile</h1>
        <p className="text-xs text-slate-500">Account credentials and platform role</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      {loading ? (
        <LoadingSkeleton type="card" count={1} />
      ) : (
        <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center gap-4 pb-4 border-b border-slate-100">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600 text-white flex items-center justify-center font-bold text-lg shadow-md shadow-indigo-600/20">
              {profile?.display_name ? profile.display_name.slice(0, 2).toUpperCase() : profile?.name ? profile.name.slice(0, 2).toUpperCase() : 'SA'}
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">{profile?.display_name || profile?.name || 'Super Administrator'}</h2>
              <span className="inline-flex items-center gap-1 text-xs text-indigo-600 font-semibold bg-indigo-50 px-2.5 py-0.5 rounded-full mt-1">
                <Shield className="w-3 h-3" /> {profile?.role || 'SUPER_ADMIN'}
              </span>
            </div>
          </div>

          <div className="space-y-3 text-xs sm:text-sm">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-600">
                <Phone className="w-4 h-4 text-slate-400" />
                <span>Mobile Number</span>
              </div>
              <span className="font-semibold text-slate-900">{profile?.mobile_number || profile?.mobile || '-'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-600">
                <Mail className="w-4 h-4 text-slate-400" />
                <span>Email Address</span>
              </div>
              <span className="font-semibold text-slate-900">{profile?.email || 'admin@scholaris.edu'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-600">
                <Key className="w-4 h-4 text-slate-400" />
                <span>Security Token</span>
              </div>
              <span className="font-semibold text-slate-900">Valid JWT Session</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SuperAdminProfile;