// src/layouts/TeacherLayout.tsx
import React from 'react';
import AppShell, { NavItem, LayoutDashboard, Users, ClipboardList, BookOpen, CalendarDays, FileText, BarChart3, Settings, Bell, User } from './AppShell';

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/teacher/dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { label: 'Students', path: '/teacher/students', icon: <Users className="w-4 h-4" /> },
  { label: 'Attendance', path: '/teacher/attendance', icon: <ClipboardList className="w-4 h-4" /> },
  { label: 'Homework', path: '/teacher/homework', icon: <BookOpen className="w-4 h-4" /> },
  { label: 'Timetable', path: '/teacher/timetable', icon: <CalendarDays className="w-4 h-4" /> },
  { label: 'Exams', path: '/teacher/exams', icon: <FileText className="w-4 h-4" /> },
  { label: 'Marks Entry', path: '/teacher/marks', icon: <BarChart3 className="w-4 h-4" /> },
  { label: 'Report Cards', path: '/teacher/report-cards', icon: <BarChart3 className="w-4 h-4" /> },
  { label: 'Announcements', path: '/teacher/announcements', icon: <Bell className="w-4 h-4" /> },
  { label: 'Calendar', path: '/teacher/calendar', icon: <CalendarDays className="w-4 h-4" /> },
  { label: 'Settings', path: '/teacher/settings', icon: <Settings className="w-4 h-4" /> },
  { label: 'Profile', path: '/teacher/profile', icon: <User className="w-4 h-4" /> },
];

export const TeacherLayout: React.FC = () => (
  <AppShell
    role="TEACHER"
    roleLabel="Teacher Portal"
    accentColor="bg-blue-950"
    navItems={navItems}
    notificationsPath="/teacher/notifications"
    activeColorClass="text-blue-600"
    indicatorColor="bg-blue-600"
  />
);

export default TeacherLayout;