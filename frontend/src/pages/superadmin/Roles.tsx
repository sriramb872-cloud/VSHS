// src/pages/superadmin/Roles.tsx
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Users, RefreshCw } from 'lucide-react';
import { MobileListItem, LoadingSkeleton, EmptyState, ErrorState, ConfirmDialog } from '../../components/shared';
import { rolesService } from '../../services/roles';
import { RoleSummary } from '../../types/roles';
import { AppUser } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import errorMessage from '../../helpers/errorMessage';

const ROLE_LABELS: Record<string, string> = {
  SUPER_ADMIN: 'Super Administrator',
  PRINCIPAL: 'Principal',
  TEACHER: 'Teacher',
  STUDENT: 'Student',
};

const ROLE_TONES: Record<string, string> = {
  SUPER_ADMIN: 'bg-indigo-50 text-indigo-700',
  PRINCIPAL: 'bg-purple-50 text-purple-700',
  TEACHER: 'bg-blue-50 text-blue-700',
  STUDENT: 'bg-emerald-50 text-emerald-700',
};

export const SuperAdminRoles: React.FC = () => {
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const currentUserId = currentUser?.id ?? null;
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [users, setUsers] = useState<AppUser[]>([]);
  const [assignable, setAssignable] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Role-change confirmation state
  const [pending, setPending] = useState<{ user: AppUser; role: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [roleRes, userRes, names] = await Promise.all([
        rolesService.listRoles(),
        rolesService.listRoleAssignments({ limit: 200 }),
        rolesService.listAssignableRoles(),
      ]);
      setRoles(roleRes.items);
      setUsers(userRes);
      setAssignable(names);
    } catch (err) {
      setError(errorMessage(err, 'Failed to load roles.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const totalUsers = useMemo(() => roles.reduce((sum, r) => sum + r.user_count, 0), [roles]);

  const confirmChange = async () => {
    if (!pending) return;
    setSaving(true);
    setActionError(null);
    try {
      const res = await rolesService.assignRole(pending.user.id, pending.role);
      setUsers((prev) => prev.map((u) => (u.id === res.user.id ? { ...u, ...res.user } : u)));
      setNotice(res.message);
      setPending(null);
      // Role counts changed, so refresh the catalogue too.
      const roleRes = await rolesService.listRoles();
      setRoles(roleRes.items);
    } catch (err) {
      setActionError(errorMessage(err, 'Failed to change role.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">System Roles</h1>
          <p className="text-xs text-slate-500">
            The {roles.length || 4} access roles the platform recognises, with live user counts
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="p-2 rounded-xl border border-slate-200 bg-white text-slate-500 hover:text-slate-800 hover:border-slate-300 active:scale-95 transition-all"
          aria-label="Refresh roles"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {notice && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-xs font-medium">
          {notice}
        </div>
      )}
      {actionError && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">
          {actionError}
        </div>
      )}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : error ? (
        <ErrorState title="Could not load roles" message={error} onRetry={load} />
      ) : roles.length === 0 ? (
        <EmptyState
          title="No Roles Defined"
          description="The role catalogue is empty."
          icon={<Shield className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <>
          <div className="space-y-2.5">
            {roles.map((role) => (
              <MobileListItem
                key={role.name}
                title={ROLE_LABELS[role.name] || role.name}
                subtitle={role.description}
                icon={<Shield className="w-5 h-5 text-indigo-600" />}
                avatarBg={ROLE_TONES[role.name] || 'bg-slate-50 text-slate-600'}
                metaText={`${role.active_user_count}/${role.user_count} active`}
                onClick={() => navigate(`/superadmin/users?role=${role.name}`)}
                actions={
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    {role.name}
                  </span>
                }
              />
            ))}
          </div>

          <div className="rounded-2xl border border-slate-200/80 bg-white p-4">
            <div className="flex items-center gap-2 mb-1">
              <Users className="w-4 h-4 text-slate-500" />
              <h2 className="text-sm font-bold text-slate-900">Role assignment</h2>
            </div>
            <p className="text-xs text-slate-500 mb-3">
              {totalUsers} user{totalUsers === 1 ? '' : 's'} across all roles. Change a user's role
              here; the change is recorded in the audit log.
            </p>

            {users.length === 0 ? (
              <p className="text-xs text-slate-400">No users to assign.</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {users.map((u) => (
                  <div
                    key={u.id}
                    className="flex items-center justify-between gap-2 rounded-xl border border-slate-200/80 px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900 truncate">
                        {u.display_name || u.mobile}
                      </p>
                      <p className="text-[11px] text-slate-500 truncate">
                        {u.mobile}
                        {u.school_name ? ` · ${u.school_name}` : ' · Platform'}
                      </p>
                    </div>
                    <select
                      value={u.role}
                      disabled={u.id === currentUserId}
                      onChange={(e) => setPending({ user: u, role: e.target.value })}
                      className="shrink-0 h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs font-semibold text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none disabled:opacity-60"
                      aria-label={`Role for ${u.display_name || u.mobile}`}
                      title={
                        u.id === currentUserId
                          ? 'You cannot change your own role.'
                          : `Change role for ${u.display_name || u.mobile}`
                      }
                    >
                      {assignable.map((r) => (
                        <option key={r} value={r}>
                          {ROLE_LABELS[r] || r}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <ConfirmDialog
        isOpen={!!pending}
        title="Change User Role?"
        message={
          pending
            ? `Change ${pending.user.display_name || pending.user.mobile} from ${
                ROLE_LABELS[pending.user.role] || pending.user.role
              } to ${ROLE_LABELS[pending.role] || pending.role}? They will immediately get the new role's access.`
            : ''
        }
        confirmLabel={saving ? 'Saving...' : 'Change Role'}
        isDanger
        isLoading={saving}
        onCancel={() => {
          setPending(null);
          setActionError(null);
          // Restore the select to the persisted role.
          setUsers((prev) => [...prev]);
        }}
        onConfirm={confirmChange}
      />
    </div>
  );
};

export default SuperAdminRoles;
