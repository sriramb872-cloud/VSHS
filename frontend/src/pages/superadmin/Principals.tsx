// src/pages/superadmin/Principals.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Search, Edit } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';
import { principalsService } from '../../services/principals';
import { Principal } from '../../types';

export const SuperAdminPrincipals: React.FC = () => {
  const [principals, setPrincipals] = useState<Principal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  const fetchPrincipals = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await principalsService.listPrincipals();
      setPrincipals(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPrincipals(); }, [fetchPrincipals]);

  const filtered = principals.filter(
    (p) =>
      p.display_name?.toLowerCase().includes(search.toLowerCase()) ||
      p.mobile?.includes(search)
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Principals</h1>
          <p className="text-xs text-slate-500">School administrators</p>
        </div>
      </div>

      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search principals..."
          className="w-full h-11 pl-10 pr-4 rounded-xl border border-slate-200 bg-white text-xs sm:text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {error && <ErrorState title="Load Error" message="Failed to load principals" onRetry={fetchPrincipals} />}

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
          {filtered.map((p) => (
            <MobileListItem
              key={p.id}
              title={p.display_name}
              subtitle={p.mobile}
              icon={<User className="w-5 h-5 text-purple-600" />}
              avatarBg="bg-purple-50 text-purple-600"
              badge={<StatusBadge status={p.is_active ? 'ACTIVE' : 'INACTIVE'} />}
              metaText={p.school_id ? `School #${p.school_id}` : 'No school'}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminPrincipals;