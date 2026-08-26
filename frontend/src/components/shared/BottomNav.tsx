// src/components/shared/BottomNav.tsx
import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { MoreHorizontal } from 'lucide-react';
import MoreSheet, { SecondaryNavItem } from './MoreSheet';

export interface PrimaryNavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

interface BottomNavProps {
  primaryItems: PrimaryNavItem[];
  moreItems?: SecondaryNavItem[];
  activeColorClass?: string;
  indicatorColor?: string;
  roleTitle?: string;
}

export const BottomNav: React.FC<BottomNavProps> = ({
  primaryItems,
  moreItems = [],
  activeColorClass = 'text-indigo-600',
  indicatorColor = 'bg-indigo-600',
  roleTitle = 'All Features',
}) => {
  const [moreOpen, setMoreOpen] = useState(false);
  const location = useLocation();

  const isMoreActive = moreItems.some((item) => location.pathname.startsWith(item.path));

  return (
    <>
      <nav className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur border-t border-slate-200/80 md:hidden pb-[env(safe-area-inset-bottom)] shadow-lg">
        <div className="flex items-center justify-around h-16 px-1">
          {primaryItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `relative flex flex-col items-center justify-center flex-1 h-full py-1 text-xs transition-all active:scale-95 ${
                  isActive ? `${activeColorClass} font-semibold` : 'text-slate-500 hover:text-slate-700'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className={`absolute top-0 w-8 h-0.5 rounded-b-full ${indicatorColor}`} />
                  )}
                  <span className="w-5 h-5 mb-0.5 flex items-center justify-center">{item.icon}</span>
                  <span className="text-[11px] leading-none truncate max-w-[64px]">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}

          {moreItems.length > 0 && (
            <button
              onClick={() => setMoreOpen(true)}
              className={`relative flex flex-col items-center justify-center flex-1 h-full py-1 text-xs transition-all active:scale-95 ${
                isMoreActive || moreOpen ? `${activeColorClass} font-semibold` : 'text-slate-500 hover:text-slate-700'
              }`}
              aria-label="More navigation options"
            >
              {(isMoreActive || moreOpen) && (
                <span className={`absolute top-0 w-8 h-0.5 rounded-b-full ${indicatorColor}`} />
              )}
              <MoreHorizontal className="w-5 h-5 mb-0.5" />
              <span className="text-[11px] leading-none">More</span>
            </button>
          )}
        </div>
      </nav>

      {moreItems.length > 0 && (
        <MoreSheet
          isOpen={moreOpen}
          onClose={() => setMoreOpen(false)}
          items={moreItems}
          roleTitle={roleTitle}
          activeColorClass={`${activeColorClass} bg-slate-50 font-semibold`}
        />
      )}
    </>
  );
};

export default BottomNav;
