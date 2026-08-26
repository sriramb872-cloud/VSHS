// src/layouts/ParentLayout.tsx
import React from 'react';
import { Outlet } from 'react-router-dom';

export const ParentLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100 flex">
      <aside className="w-64 bg-purple-900 text-white hidden md:block">
        <div className="p-4 text-xl font-bold tracking-wider">Parent Portal</div>
        <nav className="mt-4 px-2 space-y-1">
          <a href="/parent/dashboard" className="block px-4 py-2 rounded hover:bg-purple-800">Dashboard</a>
          <a href="/parent/children" className="block px-4 py-2 rounded hover:bg-purple-800">Children</a>
          <a href="/parent/attendance" className="block px-4 py-2 rounded hover:bg-purple-800">Attendance</a>
          <a href="/parent/marks" className="block px-4 py-2 rounded hover:bg-purple-800">Marks</a>
        </nav>
      </aside>

      <div className="flex-1 flex flex-col">
        <header className="h-16 bg-white shadow-sm flex items-center justify-between px-6">
          <div className="text-lg font-semibold text-gray-800">Parent Dashboard</div>
        </header>

        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default ParentLayout;