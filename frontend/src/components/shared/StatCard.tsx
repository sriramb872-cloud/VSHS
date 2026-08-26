// src/components/shared/StatCard.tsx
import React from 'react';

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  trend?: string;
  trendUp?: boolean;
  subtitle?: string;
  badgeText?: string;
  iconBgClass?: string;
  onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  icon,
  label,
  value,
  trend,
  trendUp,
  subtitle,
  badgeText,
  iconBgClass = 'bg-indigo-50 text-indigo-600',
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs hover:shadow-md transition-all ${
        onClick ? 'cursor-pointer active:scale-98' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2.5">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-medium ${iconBgClass}`}>
          {icon}
        </div>
        {badgeText && (
          <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-700">
            {badgeText}
          </span>
        )}
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-0.5">{label}</p>
        <h3 className="text-2xl font-extrabold text-slate-900 tracking-tight leading-tight">{value}</h3>
      </div>

      {(trend || subtitle) && (
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
          {trend && (
            <span
              className={`font-semibold flex items-center gap-0.5 ${
                trendUp === true
                  ? 'text-emerald-600'
                  : trendUp === false
                  ? 'text-rose-600'
                  : 'text-slate-600'
              }`}
            >
              {trendUp === true ? '↑' : trendUp === false ? '↓' : ''} {trend}
            </span>
          )}
          {subtitle && <span className="text-slate-400 truncate">{subtitle}</span>}
        </div>
      )}
    </div>
  );
};

export default StatCard;
