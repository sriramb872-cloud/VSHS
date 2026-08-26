import React, { useEffect, useState } from 'react';
import { timetableService } from '../../services/timetable';
import { TimetableSlot } from '../../types';
import { Calendar, Clock, BookOpen, Layers, CheckCircle2, ArrowRight } from 'lucide-react';
import { LoadingSkeleton, EmptyState } from '../../components/shared';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

export const TeacherTimetablePage: React.FC = () => {
  const [slots, setSlots] = useState<TimetableSlot[]>([]);
  const [dayFilter, setDayFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    timetableService
      .listTimetables()
      .then(data => setSlots(data.items || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const todayName = new Date().toLocaleDateString('en-US', { weekday: 'long' });
  const todaysSlots = slots.filter(
    s => (s.day_of_week || '').toString().toLowerCase() === todayName.toLowerCase()
  );

  // Find next upcoming class
  const nextClass = todaysSlots.length > 0 ? todaysSlots[0] : slots.length > 0 ? slots[0] : null;

  const displayDays = dayFilter ? [dayFilter] : DAYS;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">My Teaching Timetable</h1>
          <p className="text-xs text-slate-500">Your personal class schedule assigned by the Principal</p>
        </div>
        <select
          value={dayFilter}
          onChange={e => setDayFilter(e.target.value)}
          className="h-10 px-3 rounded-xl border border-slate-300 bg-white text-slate-900 text-xs font-semibold focus:ring-2 focus:ring-blue-500 focus:outline-none"
        >
          <option value="">All Days</option>
          {DAYS.map(day => (
            <option key={day} value={day}>
              {day}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : (
        <>
          {/* Today's Schedule Card */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xs">
                  <Calendar className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Today's Schedule ({todayName})</h2>
                  <p className="text-xs text-slate-500">{todaysSlots.length} class(es) scheduled for today</p>
                </div>
              </div>
            </div>

            {todaysSlots.length === 0 ? (
              <div className="py-6 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                No classes scheduled for today.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                {todaysSlots.map((slot, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-blue-50/50 border border-blue-100 rounded-xl space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs font-semibold text-blue-700">
                      <span>{slot.subject_name || `Subject #${slot.subject_id}`}</span>
                      <span className="flex items-center gap-1 text-[11px] text-slate-500">
                        <Clock className="w-3 h-3" /> {slot.start_time} - {slot.end_time}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 flex items-center gap-2">
                      <span className="font-semibold text-slate-900">
                        {slot.grade_name || `Grade ${slot.grade_id}`} {slot.section_name ? `- Section ${slot.section_name}` : ''}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Next Upcoming Class */}
          {nextClass && (
            <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-4 text-white shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center flex-shrink-0">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Next Upcoming Class</p>
                  <p className="text-sm font-bold mt-0.5">
                    {nextClass.subject_name || 'Class'} ({nextClass.grade_name || `Grade ${nextClass.grade_id}`})
                  </p>
                  <p className="text-xs text-slate-300">
                    {nextClass.day_of_week} • {nextClass.start_time} – {nextClass.end_time}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Weekly Timetable */}
          <div className="space-y-4">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Weekly Timetable</h2>
            {displayDays.map(day => {
              const daySlots = slots.filter(
                s => (s.day_of_week || '').toString().toLowerCase() === day.toLowerCase()
              );

              if (daySlots.length === 0 && dayFilter) {
                return (
                  <EmptyState
                    key={day}
                    title={`No Classes on ${day}`}
                    description="You have no periods assigned for this day."
                  />
                );
              }

              if (daySlots.length === 0) return null;

              return (
                <div key={day} className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-4 space-y-3">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-blue-600" /> {day}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {daySlots.map((s, i) => (
                      <div key={i} className="bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-lg border border-blue-100">
                            {s.subject_name || `Subject #${s.subject_id}`}
                          </span>
                          <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5" /> {s.start_time} - {s.end_time}
                          </span>
                        </div>
                        <div className="text-xs text-slate-700 font-semibold flex items-center gap-1.5 pt-1">
                          <Layers className="w-3.5 h-3.5 text-slate-400" />
                          <span>
                            {s.grade_name || `Grade ${s.grade_id}`}
                            {s.section_name ? ` (Section ${s.section_name})` : ''}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default TeacherTimetablePage;
/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
