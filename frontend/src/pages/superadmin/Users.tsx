// src/pages/superadmin/Users.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { Users as UsersIcon, Search } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';
import { usersService } from '../../services/users';
import { AppUser, UserRole } from '../../types';

const ROLES: { value: string; label: string }[] = [
  { value: '', label: 'All Roles' },
  { value: 'SUPER_ADMIN', label: 'Super Admin' },
  { value: 'PRINCIPAL', label: 'Principal' },
  { value: 'TEACHER', label: 'Teacher' },
  { value: 'STUDENT', label: 'Student' },
];

export const SuperAdminUsers: React.FC = () => {
  const [users, setUsers] = useState<AppUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await usersService.listUsers();
      setUsers(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const filtered = users.filter((u) => {
    const matchSearch =
      u.display_name?.toLowerCase().includes(search.toLowerCase()) ||
      u.mobile?.includes(search) ||
      u.email?.toLowerCase().includes(search.toLowerCase());
    const matchRole = roleFilter ? u.role === roleFilter : true;
    return matchSearch && matchRole;
  });

  const roleColor: Record<string, string> = {
    SUPER_ADMIN: 'bg-indigo-50 text-indigo-600',
    PRINCIPAL: 'bg-emerald-50 text-emerald-600',
    TEACHER: 'bg-blue-50 text-blue-600',
    STUDENT: 'bg-amber-50 text-amber-600',
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Users</h1>
        <p className="text-xs text-slate-500">All system users across all schools</p>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users..."
            className="w-full h-11 pl-10 pr-4 rounded-xl border border-slate-200 bg-white text-xs sm:text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="h-11 px-3 rounded-xl border border-slate-200 bg-white text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
      </div>

      {error && <ErrorState title="Load Error" message="Failed to load users" onRetry={fetchUsers} />}

      {loading ? (
        <LoadingSkeleton type="list" count={5} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No Users Found"
          description="No users match your current filters."
          icon={<UsersIcon className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2">
          {filtered.map((u) => (
            <MobileListItem
              key={u.id}
              title={u.display_name || u.mobile}
              subtitle={u.email || u.mobile}
              icon={<UsersIcon className="w-4 h-4" />}
              avatarBg={roleColor[u.role] || 'bg-slate-50 text-slate-600'}
              badge={<StatusBadge status={u.is_active ? 'ACTIVE' : 'INACTIVE'} />}
              metaText={u.role}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminUsers;