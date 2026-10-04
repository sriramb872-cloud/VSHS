// src/pages/common/PasswordResetRequests.tsx
//
// Flow B queue, shared by the Super Admin and Principal layouts (the backend
// scopes the rows: a Principal only ever sees Teachers/Students of their own
// school, a Super Admin sees everything - the client never decides that).
//
// The temporary password returned by the Reset action is plaintext, shown
// exactly once, and deliberately dropped from state as soon as the admin
// closes the dialog.
import React, { useCallback, useEffect, useState } from 'react';
import {
  Copy,
  Eye,
  EyeOff,
  KeyRound,
  RefreshCw,
  ShieldAlert,
  UserCheck,
  X,
} from 'lucide-react';
import { ConfirmDialog, EmptyState, LoadingSkeleton, StatusBadge } from '../../components/shared';
import {
  passwordResetService,
  toResetError,
} from '../../services/passwordReset';
import type {
  AdminResetPasswordResponse,
  PasswordResetRequest,
} from '../../types/auth';

type Filter = 'pending' | 'completed' | 'rejected' | 'all';

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'pending', label: 'Pending' },
  { id: 'completed', label: 'Completed' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'all', label: 'All' },
];

const roleLabel = (role: string) =>
  (role || '')
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');

const formatDate = (value: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
};

export const PasswordResetRequests: React.FC = () => {
  const [filter, setFilter] = useState<Filter>('pending');
  const [rows, setRows] = useState<PasswordResetRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [confirmReset, setConfirmReset] = useState<PasswordResetRequest | null>(null);
  const [confirmReject, setConfirmReject] = useState<PasswordResetRequest | null>(null);

  // Plaintext temporary password: memory only, cleared on acknowledge/close.
  const [issued, setIssued] = useState<AdminResetPasswordResponse | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await passwordResetService.listRequests(filter);
      setRows(data);
    } catch (err) {
      setError(toResetError(err, 'Failed to load password reset requests.').message);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const closeIssued = () => {
    setIssued(null);
    setRevealed(false);
    setCopied(false);
  };

  const handleReset = async () => {
    if (!confirmReset) return;
    setBusyId(confirmReset.user_id);
    setError(null);
    try {
      const result = await passwordResetService.adminResetPassword(confirmReset.user_id);
      setConfirmReset(null);
      setRevealed(false);
      setCopied(false);
      setIssued(result);
      await load();
    } catch (err) {
      setError(toResetError(err, 'Could not reset this password.').message);
      setConfirmReset(null);
    } finally {
      setBusyId(null);
    }
  };

  const handleReject = async () => {
    if (!confirmReject) return;
    setBusyId(confirmReject.id);
    setError(null);
    try {
      await passwordResetService.rejectRequest(confirmReject.id);
      setConfirmReject(null);
      await load();
    } catch (err) {
      setError(toResetError(err, 'Could not reject this request.').message);
      setConfirmReject(null);
    } finally {
      setBusyId(null);
    }
  };

  const copyPassword = async () => {
    if (!issued) return;
    try {
      await navigator.clipboard.writeText(issued.temporary_password);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      // Clipboard blocked (insecure context / permission): the value stays
      // visible on screen for manual transcription.
      setRevealed(true);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Password Reset Requests</h1>
          <p className="text-xs text-slate-500">
            Accounts waiting for a staff-issued temporary password
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="p-2.5 rounded-xl border border-slate-200 bg-white text-slate-500 hover:text-slate-700 hover:bg-slate-50 disabled:opacity-60 transition-all"
          aria-label="Refresh"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setFilter(tab.id)}
            className={`px-3.5 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-wider transition-all ${
              filter === tab.id
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="flex items-start gap-2.5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs sm:text-sm">
          <ShieldAlert className="w-4 h-4 mt-0.5 flex-shrink-0 text-rose-600" />
          <span className="font-medium leading-snug">{error}</span>
        </div>
      )}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No Requests"
          description={
            filter === 'pending'
              ? 'No account is waiting for a password reset.'
              : 'Nothing to show for this filter.'
          }
          icon={<KeyRound className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2">
          {rows.map((row) => (
            <div key={row.id} className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {row.user_name}
                    </p>
                    <StatusBadge status={row.status} />
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {roleLabel(row.role)}
                    {row.mobile ? ` · ${row.mobile}` : ''}
                    {row.email ? ` · ${row.email}` : ''}
                    {!row.has_email ? ' · no email on file' : ''}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Requested {formatDate(row.requested_at)}
                    {row.handled_by_name ? ` · handled by ${row.handled_by_name}` : ''}
                  </p>
                </div>

                {row.status === 'pending' && (
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => setConfirmReject(row)}
                      disabled={busyId !== null}
                      className="px-3 py-2 rounded-lg text-[11px] font-bold text-slate-500 bg-slate-100 hover:bg-slate-200 disabled:opacity-60 transition-all"
                    >
                      Reject
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmReset(row)}
                      disabled={busyId !== null}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-[11px] font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 transition-all"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>Reset</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* --- confirm: issue a temporary password -------------------------- */}
      <ConfirmDialog
        isOpen={confirmReset !== null}
        title="Issue temporary password?"
        message={
          confirmReset
            ? `A one-time temporary password will be generated for ${confirmReset.user_name}. Every session of that account is signed out immediately and they must set a new password at next sign-in.`
            : ''
        }
        confirmLabel="Generate"
        isLoading={busyId !== null}
        onConfirm={() => void handleReset()}
        onCancel={() => setConfirmReset(null)}
      />

      {/* --- confirm: reject ---------------------------------------------- */}
      <ConfirmDialog
        isOpen={confirmReject !== null}
        title="Reject this request?"
        message={
          confirmReject
            ? `${confirmReject.user_name} will keep their current password. Use this only when the request was handled in person.`
            : ''
        }
        confirmLabel="Reject"
        isDanger
        isLoading={busyId !== null}
        onConfirm={() => void handleReject()}
        onCancel={() => setConfirmReject(null)}
      />

      {/* --- one-time reveal of the temporary password --------------------- */}
      {issued && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs" onClick={closeIssued} />
          <div className="relative z-50 w-full max-w-sm bg-white rounded-2xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150 p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2.5 rounded-full bg-indigo-50 text-indigo-600">
                <KeyRound className="w-5 h-5" />
              </div>
              <button
                onClick={closeIssued}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <h3 className="text-base font-bold text-slate-900 mb-1">Temporary Password</h3>
            <p className="text-xs sm:text-sm text-slate-500 mb-4">
              Share it with{' '}
              <span className="font-semibold text-slate-700">
                {issued.user.display_name}
              </span>{' '}
              in person. <span className="font-semibold text-rose-600">It will not be shown
              again.</span>
            </p>

            <div className="flex items-stretch gap-2 mb-4">
              <div className="flex-1 flex items-center gap-2 px-3.5 h-12 rounded-xl bg-slate-900 text-white font-mono text-sm overflow-x-auto">
                <span className={revealed ? '' : 'select-none blur-[6px]'}>
                  {issued.temporary_password}
                </span>
                {!revealed && (
                  <button
                    type="button"
                    onClick={() => setRevealed(true)}
                    className="ml-auto inline-flex items-center gap-1 text-[11px] font-bold text-indigo-300 hover:text-indigo-200 flex-shrink-0"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Show
                  </button>
                )}
                {revealed && (
                  <button
                    type="button"
                    onClick={() => setRevealed(false)}
                    className="ml-auto inline-flex items-center gap-1 text-[11px] font-bold text-slate-400 hover:text-slate-200 flex-shrink-0"
                    aria-label="Hide password"
                  >
                    <EyeOff className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              <button
                type="button"
                onClick={() => void copyPassword()}
                className="w-12 h-12 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center transition-all"
                aria-label="Copy temporary password"
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>

            {copied && (
              <p className="text-[11px] font-semibold text-emerald-600 mb-3">Copied to clipboard.</p>
            )}

            <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 text-[11px] text-amber-800 leading-relaxed mb-4">
              <span className="font-bold inline-flex items-center gap-1">
                <UserCheck className="w-3.5 h-3.5" /> What happens next
              </span>
              <p className="mt-1">
                They sign in with this password and are taken straight to a
                &ldquo;change password&rdquo; screen. It cannot be used again after that.
              </p>
            </div>

            <button
              type="button"
              onClick={closeIssued}
              className="w-full py-2.5 px-4 text-xs sm:text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-all"
            >
              I&rsquo;ve shared it
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PasswordResetRequests;
