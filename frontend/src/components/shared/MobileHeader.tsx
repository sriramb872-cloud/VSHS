// src/components/shared/MobileHeader.tsx
import React from 'react';
import { ArrowLeft, Bell, User, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface MobileHeaderProps {
  title: string;
  subtitle?: string;
  showBack?: boolean;
  onBack?: () => void;
  roleLabel?: string;
  roleColorClass?: string;
  notificationsPath?: string;
  onOpenSidebar?: () => void;
}

export const MobileHeader: React.FC<MobileHeaderProps> = ({
  title,
  subtitle,
  showBack = false,
  onBack,
  roleLabel,
  roleColorClass = 'text-indigo-600 bg-indigo-50',
  notificationsPath,
  onOpenSidebar,
}) => {
  const navigate = useNavigate();

  const handleBackClick = () => {
    if (onBack) {
      onBack();
    } else {
      navigate(-1);
    }
  };

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-14 px-4 bg-white/95 backdrop-blur border-b border-slate-200/80 shadow-xs transition-all">
      <div className="flex items-center gap-2.5 min-w-0">
        {showBack ? (
          <button
            onClick={handleBackClick}
            className="flex items-center justify-center w-9 h-9 rounded-full text-slate-600 hover:bg-slate-100 active:scale-95 transition-all"
            aria-label="Go back"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
        ) : onOpenSidebar ? (
          <button
            onClick={onOpenSidebar}
            className="md:hidden flex items-center justify-center w-9 h-9 rounded-lg text-slate-600 hover:bg-slate-100 active:scale-95 transition-all"
            aria-label="Open Navigation"
          >
            <Menu className="w-5 h-5" />
          </button>
        ) : null}

        <div className="truncate">
          <h1 className="text-base font-bold text-slate-900 truncate leading-snug">{title}</h1>
          {subtitle && <p className="text-xs text-slate-500 truncate -mt-0.5">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-1.5 flex-shrink-0">
        {notificationsPath && (
          <button
            onClick={() => navigate(notificationsPath)}
            className="flex items-center justify-center w-9 h-9 rounded-full text-slate-600 hover:bg-slate-100 active:scale-95 transition-all relative"
            aria-label="Notifications"
          >
            <Bell className="w-4.5 h-4.5" />
          </button>
        )}

        {roleLabel && (
          <div className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${roleColorClass}`}>
            <User className="w-3.5 h-3.5" />
            <span>{roleLabel}</span>
          </div>
        )}
      </div>
    </header>
  );
};

export default MobileHeader;
