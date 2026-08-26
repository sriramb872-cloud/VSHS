// src/components/shared/MobileListItem.tsx
import React from 'react';
import { ChevronRight } from 'lucide-react';

interface MobileListItemProps {
  title: string;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  avatarText?: string;
  avatarBg?: string;
  badge?: React.ReactNode;
  metaText?: string;
  onClick?: () => void;
  actions?: React.ReactNode;
}

export const MobileListItem: React.FC<MobileListItemProps> = ({
  title,
  subtitle,
  icon,
  avatarText,
  avatarBg = 'bg-indigo-100 text-indigo-700',
  badge,
  metaText,
  onClick,
  actions,
}) => {
  return (
    <div
      onClick={onClick}
      className={`flex items-center justify-between p-3.5 bg-white rounded-xl border border-slate-200/80 shadow-2xs transition-all ${
        onClick ? 'hover:border-slate-300 active:bg-slate-50 cursor-pointer' : ''
      }`}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {avatarText ? (
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${avatarBg}`}>
            {avatarText.slice(0, 2).toUpperCase()}
          </div>
        ) : icon ? (
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${avatarBg}`}>
            {icon}
          </div>
        ) : null}

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-slate-900 truncate leading-snug">{title}</h4>
            {badge}
          </div>
          {subtitle && (
            <div className="text-xs text-slate-500 truncate mt-0.5">{subtitle}</div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 ml-3 flex-shrink-0">
        {metaText && <span className="text-xs text-slate-400 font-medium">{metaText}</span>}
        {actions}
        {onClick && !actions && <ChevronRight className="w-4 h-4 text-slate-400" />}
      </div>
    </div>
  );
};

export default MobileListItem;
