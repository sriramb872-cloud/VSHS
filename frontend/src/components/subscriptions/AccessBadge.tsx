// src/components/subscriptions/AccessBadge.tsx
import React from 'react';
import type { AccessStatus } from '../../types/subscription';

export type AccessTone = 'success' | 'info' | 'warning' | 'danger' | 'neutral';

const TONES: Record<string, { className: string; tone: AccessTone }> = {
  ACTIVE: { className: 'bg-emerald-50 text-emerald-700 border-emerald-200/60', tone: 'success' },
  FREE: { className: 'bg-cyan-50 text-cyan-700 border-cyan-200/60', tone: 'info' },
  PENDING: { className: 'bg-amber-50 text-amber-700 border-amber-200/60', tone: 'warning' },
  EXPIRED: { className: 'bg-amber-50 text-amber-700 border-amber-200/60', tone: 'warning' },
  PARTIAL: { className: 'bg-amber-50 text-amber-700 border-amber-200/60', tone: 'warning' },
  NO_PLANS: { className: 'bg-amber-50 text-amber-700 border-amber-200/60', tone: 'warning' },
  WARNING: { className: 'bg-amber-50 text-amber-700 border-amber-200/60', tone: 'warning' },
  SUSPENDED: { className: 'bg-rose-50 text-rose-700 border-rose-200/60', tone: 'danger' },
  CANCELLED: { className: 'bg-rose-50 text-rose-700 border-rose-200/60', tone: 'danger' },
  PAYMENT_REQUIRED: { className: 'bg-rose-50 text-rose-700 border-rose-200/60', tone: 'danger' },
  FAILED: { className: 'bg-rose-50 text-rose-700 border-rose-200/60', tone: 'danger' },
  NONE: { className: 'bg-slate-100 text-slate-600 border-slate-200/60', tone: 'neutral' },
  DISABLED: { className: 'bg-slate-100 text-slate-600 border-slate-200/60', tone: 'neutral' },
};

const FALLBACK = { className: 'bg-slate-100 text-slate-600 border-slate-200/60', tone: 'neutral' as AccessTone };

const LABELS: Record<string, string> = {
  PAYMENT_REQUIRED: 'Payment required',
  NO_PLANS: 'No plans',
  SUSPENDED: 'Suspended',
  CANCELLED: 'Cancelled',
  DISABLED: 'Off',
};

interface AccessBadgeProps {
  /** Raw status string straight from the API (`AccessStatus.status`, a school
   *  rollup status, a per-user bucket or a payment status). */
  status?: string | null;
  /** Optional `AccessStatus` - used to prefer the more specific reason. */
  access?: AccessStatus | null;
  /** Override the derived label (e.g. render `Inactive` for a paused plan). */
  label?: string;
  size?: 'sm' | 'md';
}

/**
 * Coloured pill for every status the subscription module reports. The label is
 * cosmetic only; the value itself is always the server's.
 */
export const AccessBadge: React.FC<AccessBadgeProps> = ({ status, access, label, size = 'sm' }) => {
  const value = (status || (access ? access.status : '') || '').toUpperCase();
  const { className } = TONES[value] || FALLBACK;
  const text =
    label ||
    LABELS[value] ||
    value.replace(/_/g, ' ').toLowerCase().replace(/^./, (c) => c.toUpperCase());

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full leading-none tracking-wide border ${className} ${
        size === 'md' ? 'px-3 py-1 text-xs font-bold' : 'px-2.5 py-0.5 text-[11px] font-semibold'
      }`}
    >
      {text}
    </span>
  );
};

export default AccessBadge;
