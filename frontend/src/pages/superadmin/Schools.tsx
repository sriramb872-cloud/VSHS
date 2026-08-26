// src/pages/superadmin/Schools.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building, Plus, Search, Edit, Eye } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';
import { schoolsService } from '../../services/schools';
import { School } from '../../types';

export const SuperAdminSchools: React.FC = () => {
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  const fetchSchools = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await schoolsService.listSchools();
      setSchools(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load schools');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSchools();
  }, [fetchSchools]);

  const filteredSchools = schools.filter(
    (s) =>
      s.name?.toLowerCase().includes(search.toLowerCase()) ||
      s.code?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Schools</h1>
          <p className="text-xs text-slate-500">Manage onboarded institutions</p>
        </div>
        <button
          onClick={() => navigate('/superadmin/schools/create')}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white font-bold text-xs shadow-xs transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>New School</span>
        </button>
      </div>

      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by school name or code..."
          className="w-full h-11 pl-10 pr-4 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs sm:text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
        />
      </div>

      {error && (
        <ErrorState title="Load Error" message={error} onRetry={fetchSchools} />
      )}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : filteredSchools.length === 0 ? (
        <EmptyState
          title="No Schools Found"
          description={search ? 'No school matches your search criteria.' : 'There are no schools onboarded yet.'}
          icon={<Building className="w-10 h-10 text-slate-300" />}
          action={{
            label: 'Create First School',
            onClick: () => navigate('/superadmin/schools/create'),
          }}
        />
      ) : (
        <div className="space-y-2.5">
          {filteredSchools.map((sch) => (
            <MobileListItem
              key={sch.id}
              title={sch.name}
              subtitle={`Code: ${sch.code}`}
              icon={<Building className="w-5 h-5 text-indigo-600" />}
              avatarBg="bg-indigo-50 text-indigo-600"
              badge={<StatusBadge status={sch.is_active ? 'ACTIVE' : 'INACTIVE'} />}
              onClick={() => navigate(`/superadmin/schools/${sch.id}`)}
              actions={[
                {
                  label: 'View',
                  icon: <Eye className="w-4 h-4" />,
                  onClick: () => navigate(`/superadmin/schools/${sch.id}`),
                },
                {
                  label: 'Edit',
                  icon: <Edit className="w-4 h-4" />,
                  onClick: () => navigate(`/superadmin/schools/${sch.id}/edit`),
                },
              ]}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminSchools;