// src/components/shared/LoadingSkeleton.tsx
import React from 'react';

interface LoadingSkeletonProps {
  type?: 'card' | 'list' | 'metrics' | 'table';
  count?: number;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  type = 'list',
  count = 3,
}) => {
  const items = Array.from({ length: count });

  if (type === 'metrics') {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-4">
        {items.map((_, i) => (
          <div key={i} className="p-4 bg-white rounded-2xl border border-slate-100 shadow-2xs space-y-3">
            <div className="w-8 h-8 rounded-xl er-skeleton" />
            <div className="w-16 h-3 er-skeleton" />
            <div className="w-24 h-6 er-skeleton" />
          </div>
        ))}
      </div>
    );
  }

  if (type === 'card') {
    return (
      <div className="space-y-3 my-4">
        {items.map((_, i) => (
          <div key={i} className="p-4 bg-white rounded-2xl border border-slate-100 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="w-32 h-4 er-skeleton" />
              <div className="w-16 h-4 er-skeleton" />
            </div>
            <div className="w-full h-12 er-skeleton" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2.5 my-3">
      {items.map((_, i) => (
        <div key={i} className="flex items-center justify-between p-3.5 bg-white rounded-xl border border-slate-100">
          <div className="flex items-center gap-3 w-full">
            <div className="w-10 h-10 rounded-full er-skeleton flex-shrink-0" />
            <div className="space-y-1.5 flex-1">
              <div className="w-1/3 h-3.5 er-skeleton" />
              <div className="w-2/3 h-3 er-skeleton" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default LoadingSkeleton;
