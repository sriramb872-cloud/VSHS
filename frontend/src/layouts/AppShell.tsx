// src/layouts/AppShell.tsx
import React, { useState } from 'react';
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  GraduationCap,
  Menu,
  LogOut,
  Bell,
  ChevronDown,
  User,
  LayoutDashboard,
  Users,
  BookOpen,
  ClipboardList,
  CalendarDays,
  BarChart3,
  Settings,
  School,
  FileText,
  MessageSquare,
  Award,
  Clock,
  Shield,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import BottomNav, { PrimaryNavItem } from '../components/shared/BottomNav';
import { SecondaryNavItem } from '../components/shared/MoreSheet';

export interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

interface AppShellProps {
  role: string;
  roleLabel: string;
  accentColor: string;
  navItems: NavItem[];
  notificationsPath?: string;
  activeColorClass?: string;
  indicatorColor?: string;
}

export const AppShell: React.FC<AppShellProps> = ({
  role,
  roleLabel,
  accentColor,
  navItems,
  notificationsPath,
  activeColorClass = 'text-indigo-600',
  indicatorColor = 'bg-indigo-600',
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { logout, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
  };

  // Primary bottom nav items (first 4 items) & secondary items for More drawer
  const primaryNav: PrimaryNavItem[] = navItems.slice(0, 4);
  const moreNav: SecondaryNavItem[] = navItems.slice(4);

  // Get current active title for mobile header
  const currentNav = navItems.find((item) => location.pathname.startsWith(item.path));
  const pageTitle = currentNav ? currentNav.label : roleLabel;

  const SidebarContent = () => (
    <div className={`flex flex-col h-full ${accentColor} text-white`}>
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/10">
        <div className="w-9 h-9 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center flex-shrink-0 shadow-xs">
          <GraduationCap className="w-5 h-5 text-white" />
        </div>
        <div className="min-w-0">
          <div className="font-extrabold text-base tracking-wide leading-tight text-white">SCHOLARIS</div>
          <div className="text-white/60 text-xs mt-0.5 truncate">{roleLabel}</div>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? 'bg-white/20 text-white font-semibold shadow-2xs'
                  : 'text-white/70 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <span className="flex-shrink-0 w-4 h-4">{item.icon}</span>
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User Info & Logout */}
      <div className="p-3 border-t border-white/10 bg-black/10">
        <div className="flex items-center gap-2.5 px-2 py-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold text-xs">
            {user?.display_name ? user.display_name.slice(0, 2).toUpperCase() : (user as any)?.name ? (user as any).name.slice(0, 2).toUpperCase() : <User className="w-4 h-4" />}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-white truncate">{user?.display_name || (user as any)?.name || roleLabel}</p>
            <p className="text-[11px] text-white/60 truncate">{user?.mobile || (user as any)?.email || role}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-xs font-semibold text-rose-200 hover:bg-rose-500/20 hover:text-white transition-all"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign out</span>
        </button>
      </div>
    </div>
  );

  return (
    <div data-role={role} className="min-h-screen bg-[var(--color-background)] flex flex-col md:flex-row font-sans">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col w-64 flex-shrink-0 shadow-lg z-30 sticky top-0 h-screen">
        <SidebarContent />
      </aside>

      {/* Mobile Drawer Overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative z-50 flex flex-col w-72 h-full shadow-2xl animate-in slide-in-from-left duration-200">
            <SidebarContent />
          </aside>
        </div>
      )}

      {/* Main Content Container */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen pb-20 md:pb-6">
        {/* Header Bar */}
        <header className="sticky top-0 z-30 h-14 bg-white/90 backdrop-blur border-b border-slate-200/80 flex items-center justify-between px-4 gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="md:hidden p-2 rounded-xl text-slate-600 hover:bg-slate-100 active:scale-95 transition-all"
              aria-label="Open sidebar menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="truncate">
              <h1 className="text-sm md:text-base font-bold text-slate-900 truncate leading-snug">{pageTitle}</h1>
              <p className="hidden md:block text-xs text-slate-500 truncate">SCHOLARIS ERP</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {notificationsPath && (
              <button
                onClick={() => navigate(notificationsPath)}
                className="p-2 rounded-full text-slate-600 hover:bg-slate-100 active:scale-95 transition-all relative"
                aria-label="View notifications"
              >
                <Bell className="w-5 h-5" />
              </button>
            )}

            {/* Profile Dropdown */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 p-1.5 sm:px-3 sm:py-1.5 rounded-full hover:bg-slate-100 transition-all border border-slate-200/60 bg-white"
              >
                <div className="w-7 h-7 rounded-full bg-[var(--color-primary-light)] text-[var(--color-primary)] flex items-center justify-center font-bold text-xs">
                  {user?.display_name ? user.display_name.slice(0, 2).toUpperCase() : (user as any)?.name ? (user as any).name.slice(0, 2).toUpperCase() : <User className="w-4 h-4" />}
                </div>
                <span className="hidden sm:block text-xs font-semibold text-slate-700 truncate max-w-[120px]">
                  {user?.display_name || (user as any)?.name || roleLabel}
                </span>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-2xl shadow-xl border border-slate-200/80 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                  <div className="px-4 py-2 border-b border-slate-100">
                    <p className="text-xs font-bold text-slate-900 truncate">{user?.display_name || (user as any)?.name || roleLabel}</p>
                    <p className="text-[11px] text-slate-500 truncate">{user?.role || role}</p>
                  </div>
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      handleLogout();
                    }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs font-semibold text-rose-600 hover:bg-rose-50 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Sign out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page Main Content Area */}
        <main className="flex-1 p-3.5 sm:p-5 md:p-6 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <BottomNav
        primaryItems={primaryNav}
        moreItems={moreNav}
        activeColorClass={activeColorClass}
        indicatorColor={indicatorColor}
        roleTitle={`${roleLabel} Navigation`}
      />
    </div>
  );
};

export {
  LayoutDashboard,
  Users,
  BookOpen,
  ClipboardList,
  CalendarDays,
  BarChart3,
  Settings,
  School,
  FileText,
  MessageSquare,
  Award,
  Clock,
  Shield,
  Bell,
  User,
};

export default AppShell;
