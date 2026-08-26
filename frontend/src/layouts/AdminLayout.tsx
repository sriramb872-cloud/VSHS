// src/layouts/AdminLayout.tsx
import React from 'react';
import AppShell, { NavItem, LayoutDashboard, School, Users, BarChart3, Settings, Shield, Bell, FileText, User } from './AppShell';

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/superadmin/dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { label: 'Schools', path: '/superadmin/schools', icon: <School className="w-4 h-4" /> },
  { label: 'Users', path: '/superadmin/users', icon: <Users className="w-4 h-4" /> },
  { label: 'Reports', path: '/superadmin/reports', icon: <BarChart3 className="w-4 h-4" /> },
  { label: 'Principals', path: '/superadmin/principals', icon: <User className="w-4 h-4" /> },
  { label: 'Analytics', path: '/superadmin/analytics', icon: <BarChart3 className="w-4 h-4" /> },
  { label: 'Roles', path: '/superadmin/roles', icon: <Shield className="w-4 h-4" /> },
  { label: 'Permissions', path: '/superadmin/permissions', icon: <Shield className="w-4 h-4" /> },
  { label: 'Subscriptions', path: '/superadmin/subscriptions', icon: <FileText className="w-4 h-4" /> },
  { label: 'Audit Logs', path: '/superadmin/audit-logs', icon: <FileText className="w-4 h-4" /> },
  { label: 'Notifications', path: '/superadmin/notifications', icon: <Bell className="w-4 h-4" /> },
  { label: 'Settings', path: '/superadmin/settings', icon: <Settings className="w-4 h-4" /> },
  { label: 'Profile', path: '/superadmin/profile', icon: <User className="w-4 h-4" /> },
];

export const AdminLayout: React.FC = () => (
  <AppShell
    role="SUPER_ADMIN"
    roleLabel="Super Admin"
    accentColor="bg-indigo-950"
    navItems={navItems}
    notificationsPath="/superadmin/notifications"
    activeColorClass="text-indigo-600"
    indicatorColor="bg-indigo-600"
  />
);

export default AdminLayout;