// src/components/subscriptions/PlanCard.tsx
import React from 'react';
import { Check, CreditCard } from 'lucide-react';
import type { SubscriptionPlan } from '../../types/subscription';
import { formatBillingInterval, formatDuration, formatPrice } from './format';
import { AccessBadge } from './AccessBadge';

interface PlanCardProps {
  plan: SubscriptionPlan;
  /** Disable selection (inactive plan, or no payment channel available). */
  disabled?: boolean;
  selected?: boolean;
  onSelect?: (plan: SubscriptionPlan) => void;
  /** Extra line rendered under the price (e.g. "Active until …"). */
  footnote?: string;
}

export const PlanCard: React.FC<PlanCardProps> = ({
  plan,
  disabled = false,
  selected = false,
  onSelect,
  footnote,
}) => {
  const inactive = !plan.is_active;

  return (
    <div
      className={`relative rounded-2xl border p-4 transition-all ${
        selected
          ? 'border-indigo-500 ring-2 ring-indigo-500/20 bg-white'
          : 'border-slate-200 bg-white hover:border-slate-300'
      } ${disabled ? 'opacity-60' : ''}`}
    >
      {selected && (
        <span className="absolute -top-2.5 right-4 bg-indigo-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
          Selected
        </span>
      )}

      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900 truncate">{plan.name}</h3>
            {inactive && <AccessBadge status="NONE" label="Inactive" />}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {formatBillingInterval(plan.billing_interval)}
            {' · '}
            {formatDuration(plan.duration_value, plan.duration_unit)}
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <div className="text-base font-bold text-slate-900 leading-tight">
            {formatPrice(plan.price, plan.currency)}
          </div>
          <div className="text-[10px] text-slate-400">per {formatDuration(plan.duration_value, plan.duration_unit)}</div>
        </div>
      </div>

      {plan.description && (
        <p className="text-xs text-slate-500 mt-2 leading-relaxed">{plan.description}</p>
      )}

      <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-3">
        <Check className="w-3.5 h-3.5 text-emerald-600" />
        <span>For {String(plan.role || '').toLowerCase()} accounts in this school</span>
      </div>

      {footnote && <p className="text-[11px] text-slate-500 mt-2">{footnote}</p>}

      {onSelect && (
        <button
          type="button"
          disabled={disabled || inactive}
          onClick={() => onSelect(plan)}
          className="mt-3 w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-xs shadow-xs transition-all"
        >
          <CreditCard className="w-3.5 h-3.5" />
          <span>{inactive ? 'Unavailable' : 'Select plan'}</span>
        </button>
      )}
    </div>
  );
};

export default PlanCard;
