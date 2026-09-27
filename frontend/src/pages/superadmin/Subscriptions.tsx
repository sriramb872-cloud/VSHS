// src/pages/superadmin/Subscriptions.tsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CreditCard, Building, ArrowRight, BarChart3 } from 'lucide-react';

/**
 * Subscriptions are **not** part of the current domain model.
 *
 * A repository-wide search for `subscription`, `plan`, `billing`, `payment`,
 * `invoice`, `renewal`, `expiry` and `tenant limit` returns no model, table,
 * schema, CRUD, service or router: the only `expiry_date` in the codebase
 * belongs to `announcements`. There is nothing to read, and no billing
 * provider is configured.
 *
 * This screen therefore states that plainly and offers the capability that does
 * exist for the same operational question - per-school activation status via the
 * audit log and the school rollup - rather than rendering invented plans,
 * prices or renewal dates.
 */
export const SuperAdminSubscriptions: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Subscriptions</h1>
        <p className="text-xs text-slate-500">School licensing and billing status</p>
      </div>

      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
        <div className="flex items-start gap-2.5">
          <CreditCard className="w-4 h-4 text-amber-700 mt-0.5 flex-shrink-0" />
          <div>
            <h2 className="text-sm font-bold text-amber-900">
              Not available: there is no subscription model
            </h2>
            <p className="text-xs text-amber-800 mt-1">
              SCHOLARIS has no subscription, plan, billing or payment model. There is no table,
              schema or endpoint to read, and no payment provider is configured, so this screen
              cannot show licensing or renewal data without inventing it.
            </p>
            <p className="text-xs text-amber-800 mt-2">
              The closest real equivalent is per-school activation, managed from{' '}
              <span className="font-mono">/superadmin/schools</span>, with every change recorded
              in the audit log.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200/80 bg-white p-4">
        <h2 className="text-sm font-bold text-slate-900">What exists today</h2>
        <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4 mt-2">
          <li>
            <span className="font-mono text-slate-800">schools.is_active</span> — whether a school
            is currently on or off. Toggled from the Schools screen.
          </li>
          <li>
            <span className="font-mono text-slate-800">/superadmin/reports</span> — cross-school
            rollup with per-school activity, which is the closest thing to a renewal review.
          </li>
          <li>
            <span className="font-mono text-slate-800">/superadmin/audit-logs</span> — the
            authoritative history of who changed a school's status and when.
          </li>
        </ul>
        <div className="flex flex-wrap gap-2 mt-4">
          <button
            type="button"
            onClick={() => navigate('/superadmin/schools')}
            className="flex items-center gap-2 h-10 px-4 rounded-xl bg-indigo-600 text-white text-xs font-bold hover:bg-indigo-700 active:scale-95 transition-all"
          >
            <Building className="w-4 h-4" />
            Manage Schools
          </button>
          <button
            type="button"
            onClick={() => navigate('/superadmin/reports')}
            className="flex items-center gap-2 h-10 px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50 active:scale-95 transition-all"
          >
            <BarChart3 className="w-4 h-4" />
            Open Platform Report
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default SuperAdminSubscriptions;
