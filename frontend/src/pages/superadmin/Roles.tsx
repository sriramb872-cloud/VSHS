// src/pages/superadmin/Roles.tsx
import React, { useState, useEffect } from 'react';
import { Shield } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton } from '../../components/shared';

export const SuperAdminRoles: React.FC = () => {
  const [roles, setRoles] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch roles
    setLoading(false);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">System Roles</h1>
        <p className="text-xs text-slate-500">Configured access roles (V1)</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : roles.length === 0 ? (
        <div className="space-y-2.5">
          {[
            { name: 'SUPER_ADMIN', label: 'Super Administrator', desc: 'Full platform management access' },
            { name: 'PRINCIPAL', label: 'School Principal', desc: 'School leadership & operational management' },
            { name: 'TEACHER', label: 'Teacher', desc: 'Classroom, attendance, homework & marks management' },
            { name: 'STUDENT', label: 'Student', desc: 'Learner portal access' },
          ].map((r) => (
            <MobileListItem
              key={r.name}
              title={r.label}
              subtitle={r.desc}
              icon={<Shield className="w-5 h-5 text-indigo-600" />}
              avatarBg="bg-indigo-50 text-indigo-600"
              metaText={r.name}
            />
          ))}
        </div>
      ) : (
        <div className="space-y-2.5">
          {roles.map((r, idx) => (
            <MobileListItem
              key={idx}
              title={r.name || r}
              icon={<Shield className="w-5 h-5 text-indigo-600" />}
              avatarBg="bg-indigo-50 text-indigo-600"
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminRoles;