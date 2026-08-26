// src/components/shared/StatusBadge.tsx
import React from 'react';

export type StatusVariant =
  | 'ACTIVE'
  | 'INACTIVE'
  | 'PENDING'
  | 'COMPLETED'
  | 'PRESENT'
  | 'ABSENT'
  | 'LATE'
  | 'OVERDUE'
  | 'SUCCESS'
  | 'WARNING'
  | 'DANGER'
  | 'INFO'
  | 'NEUTRAL'
  | string;

interface StatusBadgeProps {
  status: StatusVariant;
  label?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  size = 'sm',
}) => {
  const normalized = (status || '').toUpperCase();
  const text = label || normalized;

  let colorStyle = 'bg-slate-100 text-slate-700';

  if (['ACTIVE', 'PRESENT', 'COMPLETED', 'SUCCESS', 'PUBLISHED', 'PASSED'].includes(normalized)) {
    colorStyle = 'bg-emerald-50 text-emerald-700 border border-emerald-200/60';
  } else if (['PENDING', 'WARNING', 'DUE_SOON', 'EXPIRED', 'LATE'].includes(normalized)) {
    colorStyle = 'bg-amber-50 text-amber-700 border border-amber-200/60';
  } else if (['INACTIVE', 'ABSENT', 'OVERDUE', 'DANGER', 'FAILED', 'REJECTED'].includes(normalized)) {
    colorStyle = 'bg-rose-50 text-rose-700 border border-rose-200/60';
  } else if (['INFO', 'SCHEDULED', 'ASSIGNED'].includes(normalized)) {
    colorStyle = 'bg-cyan-50 text-cyan-700 border border-cyan-200/60';
  }

  const sizeStyle = size === 'md' ? 'px-3 py-1 text-xs font-bold' : 'px-2.5 py-0.5 text-[11px] font-semibold';

  return (
    <span className={`inline-flex items-center justify-center rounded-full leading-none tracking-wide ${colorStyle} ${sizeStyle}`}>
      {text}
    </span>
  );
};

export default StatusBadge;
