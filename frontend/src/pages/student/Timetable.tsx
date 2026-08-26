// src/pages/student/Timetable.tsx
import React, { useEffect, useState } from 'react';
import { timetableService } from '../../services/timetable';
import { Timetable } from '../../types/timetable';
import { TimetableGrid } from '../../components/timetable';

export const StudentTimetablePage: React.FC = () => {
  const [timetable, setTimetable] = useState<Timetable | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    // Assuming student belongs to Grade 10, Section 1 (Timetable ID 1 for mock)
    timetableService
      .listTimetables({ grade_id: 10, section_id: 1 })
      .then(data => {
        if (data.items.length > 0) {
          setTimetable(data.items[0]);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Class Timetable</h1>
        <p className="text-sm text-gray-500 mt-1">View your weekly class schedule and period breakdown.</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading schedule...</div>
      ) : timetable ? (
        <TimetableGrid timetable={timetable} />
      ) : (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200 text-gray-500">
          No class timetable available.
        </div>
      )}
    </div>
  );
};

export default StudentTimetablePage;/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
