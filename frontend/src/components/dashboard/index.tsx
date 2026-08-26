// src/components/dashboard/index.tsx
import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  description?: string;
}

export const StatCard: React.FC<StatCardProps> = ({ title, value, icon, description }) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500">{title}</span>
        {icon && <div className="text-indigo-600">{icon}</div>}
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      {description && <p className="text-xs text-gray-400">{description}</p>}
    </div>
  );
};

export default StatCard;
/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
