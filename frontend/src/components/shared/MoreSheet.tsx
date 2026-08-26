// src/components/shared/MoreSheet.tsx
import React from 'react';
import { NavLink } from 'react-router-dom';
import { X, LogOut } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

export interface SecondaryNavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

interface MoreSheetProps {
  isOpen: boolean;
  onClose: () => void;
  items: SecondaryNavItem[];
  roleTitle?: string;
  activeColorClass?: string;
}

export const MoreSheet: React.FC<MoreSheetProps> = ({
  isOpen,
  onClose,
  items,
  roleTitle = 'More Options',
  activeColorClass = 'text-indigo-600 bg-indigo-50 font-semibold',
}) => {
  const { logout } = useAuth();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 md:hidden flex flex-col justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Sheet Content */}
      <div className="relative z-50 bg-white rounded-t-2xl shadow-xl max-h-[80vh] flex flex-col overflow-hidden animate-in slide-in-from-bottom duration-200">
        {/* Sheet Handle */}
        <div className="w-12 h-1.5 bg-slate-300 rounded-full mx-auto my-3 flex-shrink-0" />

        {/* Sheet Header */}
        <div className="flex items-center justify-between px-5 pb-3 border-b border-slate-100">
          <h3 className="text-base font-bold text-slate-900">{roleTitle}</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all"
            aria-label="Close sheet"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Sheet Links Grid */}
        <div className="p-4 overflow-y-auto grid grid-cols-2 gap-2.5">
          {items.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 p-3 rounded-xl border text-xs sm:text-sm font-medium transition-all ${
                  isActive
                    ? `border-transparent ${activeColorClass}`
                    : 'border-slate-200/80 bg-white text-slate-700 hover:bg-slate-50'
                }`
              }
            >
              <span className="p-2 rounded-lg bg-slate-100 text-slate-600 flex-shrink-0">
                {item.icon}
              </span>
              <span className="truncate">{item.label}</span>
            </NavLink>
          ))}
        </div>

        {/* Logout Action */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <button
            onClick={() => {
              onClose();
              logout();
            }}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold text-red-600 bg-red-50 hover:bg-red-100 active:scale-98 transition-all"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default MoreSheet;
