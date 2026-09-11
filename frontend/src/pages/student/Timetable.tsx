// src/pages/student/Timetable.tsx
import React, { useEffect, useState } from 'react';
import { timetableService } from '../../services/timetable';
import { Timetable } from '../../types/timetable';
import { TimetableGrid } from '../../components/timetable';

export const StudentTimetablePage: React.FC = () => {
  const [timetable, setTimetable] = useState<Timetable | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDay, setSelectedDay] = useState('Monday');
  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  useEffect(() => {
    setLoading(true);
    timetableService.listTimetables()
      .then(data => {
        if (data.items.length > 0) {
          const first: any = data.items[0];
          setTimetable({
            id: first.id,
            academic_year_id: first.academic_year_id,
            grade_id: first.grade_id,
            section_id: first.section_id,
            entries: data.items as any,
          });
        } else {
          setTimetable(null);
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
      <div className="flex gap-2 overflow-x-auto pb-1">
        {DAYS.map(day => <button key={day} onClick={() => setSelectedDay(day)} className={`px-3 py-2 rounded-lg text-xs font-semibold whitespace-nowrap ${selectedDay === day ? 'bg-indigo-600 text-white' : 'bg-white border border-slate-200 text-slate-700'}`}>{day}</button>)}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading schedule...</div>
      ) : timetable ? (
        <TimetableGrid timetable={timetable} selectedDay={selectedDay} />
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
