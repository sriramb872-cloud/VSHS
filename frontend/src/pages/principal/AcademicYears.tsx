// src/pages/principal/AcademicYears.tsx
import React from 'react';
import { AcademicYearSection } from '../../components/settings/AcademicYearSection';

/**
 * Dedicated management page for the school's Academic Years.
 *
 * The whole experience lives in the shared `AcademicYearSection` so this page
 * and Settings → Academic Year always behave identically (one implementation,
 * one service, one context). `heading={null}` suppresses the card heading
 * because this page already renders its own page title.
 */
export const AcademicYears: React.FC = () => {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Academic Years</h1>
        <p className="text-xs text-slate-500">
          One year per school is active. Switching years re-scopes every screen; archived years
          stay readable.
        </p>
      </div>

      <AcademicYearSection heading={null} />
    </div>
  );
};

export default AcademicYears;
