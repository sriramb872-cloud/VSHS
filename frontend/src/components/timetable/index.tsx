// src/components/timetable/index.tsx
import React from 'react';
import { Timetable } from '../../types/timetable';
import { Calendar, Clock, MapPin, User, BookOpen } from 'lucide-react';

interface TimetableGridProps {
  timetable: Timetable;
  selectedDay?: string;
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

const timeToMinutes = (value?: string): number => {
  if (!value) return Number.MAX_SAFE_INTEGER;
  const match = value.trim().match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
  if (!match) return Number.MAX_SAFE_INTEGER;
  let hours = Number(match[1]);
  const minutes = Number(match[2]);
  const meridiem = (match[3] || '').toUpperCase();
  if (meridiem === 'PM' && hours < 12) hours += 12;
  if (meridiem === 'AM' && hours === 12) hours = 0;
  return hours * 60 + minutes;
};

export const TimetableGrid: React.FC<TimetableGridProps> = ({ timetable, selectedDay }) => {
  const filteredDays = selectedDay ? [selectedDay] : DAYS;

  return (
    <div className="space-y-6">
      {filteredDays.map(day => {
        const dayEntries = timetable.entries
          .filter(e => e.day_of_week.toLowerCase() === day.toLowerCase())
          .sort((a, b) => timeToMinutes(a.start_time) - timeToMinutes(b.start_time));

        if (dayEntries.length === 0 && selectedDay) {
          return (
            <div key={day} className="bg-white rounded-lg border border-gray-200 p-6 text-center text-gray-500">
              No classes scheduled for {day}.
            </div>
          );
        }

        if (dayEntries.length === 0) return null;

        return (
          <div key={day} className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
            <h3 className="text-md font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-600" /> {day}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {dayEntries.map(entry => (
                <div key={entry.id} className="bg-gray-50 rounded-md border border-gray-100 p-4 space-y-2">
                  <div className="flex justify-between items-start">
                    {entry.period_number != null && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 text-indigo-700">
                        Period {entry.period_number}
                      </span>
                    )}
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> {entry.start_time} - {entry.end_time}
                    </span>
                  </div>

                  <div className="text-sm font-semibold text-gray-800 flex items-center gap-1.5 pt-1">
                    <BookOpen className="w-4 h-4 text-gray-400" /> {entry.subject_name || `Subject #${entry.subject_id}`}
                  </div>

                  <div className="flex items-center justify-between text-xs text-gray-600 pt-1 border-t border-gray-200/60">
                    <span className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5" /> {entry.teacher_name || `Teacher #${entry.teacher_id}`}
                    </span>
                    {(entry.classroom || entry.room_number) && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5" /> {entry.classroom || entry.room_number}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default TimetableGrid;
