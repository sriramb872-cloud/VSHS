import React from 'react';
import { WEEKDAYS } from '../../utils/date';

/** Re-exported for existing imports - one source of truth lives in utils/date. */
export { WEEKDAYS };

export const WeekdayTabs: React.FC<{
  selectedDay: string;
  onChange: (day: string) => void;
  /** Optional id of the element the tabs control (for `aria-controls`). */
  id?: string;
}> = ({ selectedDay, onChange, id }) => (
  <div
    className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 snap-x"
    role="tablist"
    aria-label="Weekdays"
  >
    {WEEKDAYS.map(day => (
      <button
        key={day}
        id={id ? `${id}-tab-${day}` : undefined}
        type="button"
        role="tab"
        aria-selected={selectedDay === day}
        onClick={() => onChange(day)}
        className={`snap-start px-3 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
          selectedDay === day
            ? 'bg-[var(--brand)] text-white shadow-xs'
            : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
        }`}
      >
        {day}
      </button>
    ))}
  </div>
);

export default WeekdayTabs;
