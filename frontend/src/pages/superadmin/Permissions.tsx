// src/pages/superadmin/Permissions.tsx
import React, { useState, useEffect } from 'react';
import { Lock } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton } from '../../components/shared';

export const SuperAdminPermissions: React.FC = () => {
  const [permissions, setPermissions] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch system permissions
    setLoading(false);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Permission Matrix</h1>
        <p className="text-xs text-slate-500">Fine-grained access rights definitions</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : permissions.length === 0 ? (
        <EmptyState
          title="No Permissions Defined"
          description="System permissions list is currently empty."
          icon={<Lock className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {permissions.map((perm) => (
            <MobileListItem
              key={perm.id}
              title={perm.name}
              subtitle={perm.description || 'System permission constraint'}
              icon={<Lock className="w-5 h-5 text-indigo-600" />}
              avatarBg="bg-indigo-50 text-indigo-600"
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminPermissions;