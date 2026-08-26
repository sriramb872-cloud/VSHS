// src/layouts/PrincipalLayout.tsx
import React from 'react';
import AppShell, { NavItem, LayoutDashboard, Users, BookOpen, BarChart3, CalendarDays, Settings, Bell, FileText, ClipboardList, User, Award, School } from './AppShell';

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/principal/dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { label: 'Students', path: '/principal/students', icon: <Users className="w-4 h-4" /> },
  { label: 'Teachers', path: '/principal/teachers', icon: <User className="w-4 h-4" /> },
  { label: 'Reports', path: '/principal/report-cards', icon: <BarChart3 className="w-4 h-4" /> },
  { label: 'Grades', path: '/principal/grades', icon: <Award className="w-4 h-4" /> },
  { label: 'Sections', path: '/principal/sections', icon: <School className="w-4 h-4" /> },
  { label: 'Subjects', path: '/principal/subjects', icon: <BookOpen className="w-4 h-4" /> },
  { label: 'Timetable', path: '/principal/timetable', icon: <CalendarDays className="w-4 h-4" /> },
  { label: 'Exams', path: '/principal/exams', icon: <FileText className="w-4 h-4" /> },
  { label: 'Attendance', path: '/principal/attendance', icon: <ClipboardList className="w-4 h-4" /> },
  { label: 'Homework', path: '/principal/homework', icon: <BookOpen className="w-4 h-4" /> },
  { label: 'Announcements', path: '/principal/announcements', icon: <Bell className="w-4 h-4" /> },
  { label: 'Calendar', path: '/principal/calendar', icon: <CalendarDays className="w-4 h-4" /> },
  { label: 'Settings', path: '/principal/settings', icon: <Settings className="w-4 h-4" /> },
  { label: 'Profile', path: '/principal/profile', icon: <User className="w-4 h-4" /> },
];

export const PrincipalLayout: React.FC = () => (
  <AppShell
    role="PRINCIPAL"
    roleLabel="Principal Portal"
    accentColor="bg-emerald-950"
    navItems={navItems}
    notificationsPath="/principal/notifications"
    activeColorClass="text-emerald-600"
    indicatorColor="bg-emerald-600"
  />
);

export default PrincipalLayout;