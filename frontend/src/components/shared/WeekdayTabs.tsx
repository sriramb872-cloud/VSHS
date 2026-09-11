import React from 'react';

export const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

export const WeekdayTabs: React.FC<{
  selectedDay: string;
  onChange: (day: string) => void;
}> = ({ selectedDay, onChange }) => (
  <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Weekdays">
    {WEEKDAYS.map(day => (
      <button
        key={day}
        type="button"
        role="tab"
        aria-selected={selectedDay === day}
        onClick={() => onChange(day)}
        className={`px-3 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${selectedDay === day ? 'bg-indigo-600 text-white' : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'}`}
      >
        {day}
      </button>
    ))}
  </div>
);

export default WeekdayTabs;
