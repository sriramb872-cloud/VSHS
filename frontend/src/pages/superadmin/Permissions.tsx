// src/pages/superadmin/Permissions.tsx
import React, { useCallback, useEffect, useState } from 'react';
import { Lock, Shield, RefreshCw } from 'lucide-react';
import { LoadingSkeleton, ErrorState } from '../../components/shared';
import { rolesService } from '../../services/roles';
import { RoleSummary } from '../../types/roles';
import errorMessage from '../../helpers/errorMessage';

/**
 * This platform has **no per-permission grant table**.
 *
 * Authorization in SCHOLARIS is entirely role-based: `users.role` is a MySQL
 * ENUM of `SUPER_ADMIN | PRINCIPAL | TEACHER | STUDENT`, and every check reads
 * it - `app/api/deps.py::require_roles`, the `check_*_permission` helpers in
 * `app/permissions/`, and the `RoleRoute` guards on the frontend. There is no
 * `permissions` table, no `role_permissions` join, and no per-user overrides.
 *
 * Rather than render a fabricated permission matrix, this screen reports the
 * real, queryable facts: the role catalogue and where each role's checks live.
 * A per-permission editor would be a new subsystem, not a fix.
 */
export const SuperAdminPermissions: React.FC = () => {
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await rolesService.listRoles();
      setRoles(res.items);
    } catch (err) {
      setError(errorMessage(err, 'Failed to load the role catalogue.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Permission Matrix</h1>
          <p className="text-xs text-slate-500">How access is actually enforced</p>
        </div>
        <button
          type="button"
          onClick={load}
          className="p-2 rounded-xl border border-slate-200 bg-white text-slate-500 hover:text-slate-800 hover:border-slate-300 active:scale-95 transition-all"
          aria-label="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
        <div className="flex items-start gap-2.5">
          <Lock className="w-4 h-4 text-amber-700 mt-0.5 flex-shrink-0" />
          <div>
            <h2 className="text-sm font-bold text-amber-900">
              This platform is role-based, not permission-based
            </h2>
            <p className="text-xs text-amber-800 mt-1">
              There is no permission table to edit. <code className="font-mono">users.role</code> is
              an enum of {roles.length || 4} values, and every authorization check in the API reads
              it directly. Granular permissions (per-module grants, per-user overrides) are not
              part of the current domain model, so this screen does not pretend otherwise.
            </p>
          </div>
        </div>
      </div>

      {error && <ErrorState title="Could not load roles" message={error} onRetry={load} />}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : (
        <>
          <div className="space-y-2.5">
            {roles.map((role) => (
              <div
                key={role.name}
                className="flex items-center justify-between p-3.5 bg-white rounded-xl border border-slate-200/80 shadow-2xs"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center flex-shrink-0">
                    <Shield className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-slate-900 truncate">{role.name}</h3>
                    <p className="text-xs text-slate-500 truncate">{role.description}</p>
                  </div>
                </div>
                <span className="text-xs text-slate-400 font-medium shrink-0 ml-3">
                  {role.user_count} user{role.user_count === 1 ? '' : 's'}
                </span>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-slate-200/80 bg-white p-4">
            <h2 className="text-sm font-bold text-slate-900 mb-2">Where the checks live</h2>
            <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
              <li>
                <span className="font-mono text-slate-800">backend-python/app/api/deps.py</span> —
                <span className="font-mono"> require_roles()</span>, the FastAPI dependency that
                guards a whole router.
              </li>
              <li>
                <span className="font-mono text-slate-800">backend-python/app/permissions/</span> —
                resource-level helpers such as{' '}
                <span className="font-mono">check_student_write_permission()</span> that also
                enforce school ownership.
              </li>
              <li>
                <span className="font-mono text-slate-800">frontend/src/routes/RoleRoute.tsx</span> —
                client-side route guards, one per role. These are UX only; the server re-checks
                every request.
              </li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
};

export default SuperAdminPermissions;
