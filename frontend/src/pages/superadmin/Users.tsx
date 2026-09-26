// src/pages/superadmin/Users.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Users as UsersIcon, Search } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';
import { EditModal } from '../../components/EditModal';
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
  const [searchParams] = useSearchParams();
  const [users, setUsers] = useState<AppUser[]>([]);
  const [editingUser, setEditingUser] = useState<AppUser | null>(null);
  const [resettingUser, setResettingUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState(searchParams.get('role') || '');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await usersService.listUsers({
        role: roleFilter || undefined,
        search: debouncedSearch || undefined,
      });
      setUsers(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [roleFilter, debouncedSearch]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const roleColor: Record<string, string> = {
    SUPER_ADMIN: 'bg-indigo-50 text-indigo-600',
    PRINCIPAL: 'bg-emerald-50 text-emerald-600',
    TEACHER: 'bg-blue-50 text-blue-600',
    STUDENT: 'bg-amber-50 text-amber-600',
  };
  const setUserActive = async (user: AppUser, active: boolean) => {
    const updated = await usersService.setUserActive(user.id, active);
    setUsers(items => items.map(item => item.id === user.id ? updated : item));
  };
  const resetPassword = (user: AppUser) => {
    setResettingUser(user);
  };

  const generateTemporaryPassword = () => {
    const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*';
    const values = new Uint32Array(14);
    if (globalThis.crypto?.getRandomValues) globalThis.crypto.getRandomValues(values);
    else values.fill(Math.floor(Math.random() * alphabet.length));
    return Array.from(values, value => alphabet[value % alphabet.length]).join('');
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
      ) : users.length === 0 ? (
        <EmptyState
          title="No Users Found"
          description="No users match your current filters."
          icon={<UsersIcon className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2">
          {users.map((u) => (
            <MobileListItem
              key={u.id}
              title={u.display_name || u.mobile}
              subtitle={u.email || u.mobile}
              icon={<UsersIcon className="w-4 h-4" />}
              avatarBg={roleColor[u.role] || 'bg-slate-50 text-slate-600'}
              badge={<StatusBadge status={u.is_active || 'INACTIVE'} />}
              metaText={u.role}
              actions={<div className="flex gap-1" onClick={event => event.stopPropagation()}><button type="button" className="text-xs text-indigo-700" onClick={() => setEditingUser(u)}>Edit</button><button type="button" className="text-xs text-emerald-700" onClick={() => setUserActive(u, !(u.is_active === true || u.is_active === 'ACTIVE'))}>{u.is_active === true || u.is_active === 'ACTIVE' ? 'Deactivate' : 'Activate'}</button><button type="button" className="text-xs text-slate-700" onClick={() => resetPassword(u)}>Reset Password</button><button type="button" className="text-xs text-rose-700" onClick={() => setUserActive(u, false)}>Offboard</button></div>}
            />
          ))}
        </div>
      )}

      {editingUser && (
        <EditModal
          title="Edit User"
          fields={[
            { key: 'full_name', label: 'Full Name', required: true },
            { key: 'email', label: 'Email', type: 'email' },
            { key: 'mobile', label: 'Mobile', type: 'tel' },
          ]}
          initialValues={{
            full_name: editingUser.display_name || '',
            email: editingUser.email || '',
            mobile: editingUser.mobile || '',
          }}
          onSubmit={async (values) => {
            const updated = await usersService.updateUser(editingUser.id, {
              display_name: values.full_name,
              full_name: values.full_name,
              email: values.email || undefined,
              mobile: values.mobile || undefined,
            } as any);
            setUsers(current => current.map(u => (u.id === updated.id ? { ...u, ...updated } : u)));
            setEditingUser(null);
          }}
          onClose={() => setEditingUser(null)}
        />
      )}

      {resettingUser && (
        <EditModal
          title={`Reset Password — ${resettingUser.display_name || resettingUser.mobile}`}
          fields={[
            { key: 'password', label: 'New Temporary Password', type: 'password', required: true },
          ]}
          initialValues={{ password: generateTemporaryPassword() }}
          onSubmit={async (values) => {
            await usersService.resetUserPassword(resettingUser.id, values.password);
          }}
          onClose={() => setResettingUser(null)}
        />
      )}
    </div>
  );
};

export default SuperAdminUsers;
