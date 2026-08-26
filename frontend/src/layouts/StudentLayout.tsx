// src/layouts/StudentLayout.tsx
import React from 'react';
import AppShell, { NavItem, LayoutDashboard, ClipboardList, BookOpen, BarChart3, CalendarDays, FileText, Bell, Settings, User } from './AppShell';

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/student/dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { label: 'Attendance', path: '/student/attendance', icon: <ClipboardList className="w-4 h-4" /> },
  { label: 'Homework', path: '/student/homework', icon: <BookOpen className="w-4 h-4" /> },
  { label: 'Marks', path: '/student/marks', icon: <BarChart3 className="w-4 h-4" /> },
  { label: 'Timetable', path: '/student/timetable', icon: <CalendarDays className="w-4 h-4" /> },
  { label: 'Exams', path: '/student/exams', icon: <FileText className="w-4 h-4" /> },
  { label: 'Report Cards', path: '/student/report-cards', icon: <BarChart3 className="w-4 h-4" /> },
  { label: 'Announcements', path: '/student/announcements', icon: <Bell className="w-4 h-4" /> },
  { label: 'Calendar', path: '/student/calendar', icon: <CalendarDays className="w-4 h-4" /> },
  { label: 'Settings', path: '/student/settings', icon: <Settings className="w-4 h-4" /> },
  { label: 'Profile', path: '/student/profile', icon: <User className="w-4 h-4" /> },
];

export const StudentLayout: React.FC = () => (
  <AppShell
    role="STUDENT"
    roleLabel="Student Portal"
    accentColor="bg-orange-950"
    navItems={navItems}
    notificationsPath="/student/notifications"
    activeColorClass="text-orange-600"
    indicatorColor="bg-orange-600"
  />
);

export default StudentLayout;