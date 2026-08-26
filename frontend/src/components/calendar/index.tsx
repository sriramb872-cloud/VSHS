// src/components/calendar/index.tsx
import React, { useState } from 'react';
import { CalendarEvent, CalendarEventCreatePayload, CalendarEventUpdatePayload } from '../../types/calendar';
import {
  Calendar as CalendarIcon,
  Clock,
  Trash2,
  Edit3,
  Eye,
  X,
  ChevronLeft,
  ChevronRight,
  Info,
  Sparkles,
} from 'lucide-react';

export const getEventTypeBadgeClass = (type: string) => {
  const t = type.toLowerCase();
  if (t.includes('holiday')) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (t.includes('exam')) return 'bg-rose-50 text-rose-700 border-rose-200';
  if (t.includes('parent') || t.includes('ptm')) return 'bg-purple-50 text-purple-700 border-purple-200';
  if (t.includes('sport')) return 'bg-cyan-50 text-cyan-700 border-cyan-200';
  if (t.includes('cultural')) return 'bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200';
  if (t.includes('school') || t.includes('event')) return 'bg-amber-50 text-amber-700 border-amber-200';
  if (t.includes('meeting')) return 'bg-blue-50 text-blue-700 border-blue-200';
  if (t.includes('academic')) return 'bg-indigo-50 text-indigo-700 border-indigo-200';
  return 'bg-slate-100 text-slate-700 border-slate-200';
};

export const formatEventDate = (startDateStr: string, endDateStr?: string | null): string => {
  if (!startDateStr) return '';
  const start = new Date(startDateStr.includes('T') ? startDateStr : `${startDateStr}T00:00:00`);
  const startFormatted = start.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  if (!endDateStr || startDateStr.slice(0, 10) === endDateStr.slice(0, 10)) {
    return startFormatted;
  }

  const end = new Date(endDateStr.includes('T') ? endDateStr : `${endDateStr}T00:00:00`);
  const endFormatted = end.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  const diffTime = Math.abs(end.getTime() - start.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;

  return `${startFormatted} – ${endFormatted} (${diffDays} days)`;
};

export const isMultiDayEvent = (startDateStr: string, endDateStr?: string | null): boolean => {
  if (!endDateStr) return false;
  return startDateStr.slice(0, 10) !== endDateStr.slice(0, 10);
};

// ─── EVENT CARD ─────────────────────────────────────────────────────────────
interface CalendarEventCardProps {
  event: CalendarEvent;
  onEdit?: (event: CalendarEvent) => void;
  onDelete?: (id: number) => void;
  onViewDetails?: (event: CalendarEvent) => void;
  isPrincipal?: boolean;
}

export const CalendarEventCard: React.FC<CalendarEventCardProps> = ({
  event,
  onEdit,
  onDelete,
  onViewDetails,
  isPrincipal = false,
}) => {
  const isMulti = isMultiDayEvent(event.start_date, event.end_date);

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 p-4 sm:p-5 shadow-xs hover:shadow-md transition-all space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getEventTypeBadgeClass(event.event_type)}`}>
              {event.event_type}
            </span>
            {isMulti && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                Multi-day
              </span>
            )}
          </div>
          <h3 className="text-base font-bold text-slate-900 break-words">{event.title}</h3>
        </div>

        {/* Action Buttons for Principal */}
        {isPrincipal && (
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {onEdit && (
              <button
                onClick={() => onEdit(event)}
                className="p-2 rounded-xl text-slate-600 hover:text-emerald-700 hover:bg-emerald-50 transition-colors"
                title="Edit Event"
                aria-label="Edit Event"
              >
                <Edit3 className="w-4 h-4" />
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => onDelete(event.id)}
                className="p-2 rounded-xl text-slate-600 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                title="Delete Event"
                aria-label="Delete Event"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>

      {event.description && (
        <p className="text-xs sm:text-sm text-slate-600 line-clamp-2 leading-relaxed">
          {event.description}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between pt-3 border-t border-slate-100 gap-2 text-xs text-slate-500">
        <div className="flex items-center gap-1.5 font-medium text-slate-700">
          <CalendarIcon className="w-4 h-4 text-slate-400 flex-shrink-0" />
          <span>{formatEventDate(event.start_date, event.end_date)}</span>
        </div>

        {onViewDetails && (
          <button
            onClick={() => onViewDetails(event)}
            className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 hover:text-emerald-800 transition-colors py-1 px-2 rounded-lg hover:bg-emerald-50"
          >
            <Eye className="w-3.5 h-3.5" />
            Details
          </button>
        )}
      </div>
    </div>
  );
};

// ─── EVENT DETAILS MODAL ─────────────────────────────────────────────────────
interface EventDetailModalProps {
  event: CalendarEvent | null;
  onClose: () => void;
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose }) => {
  if (!event) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${getEventTypeBadgeClass(event.event_type)}`}>
              {event.event_type}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900">{event.title}</h2>
          </div>

          <div className="bg-slate-50 rounded-2xl p-4 space-y-2.5 border border-slate-100">
            <div className="flex items-center gap-2 text-sm text-slate-700">
              <Clock className="w-4 h-4 text-slate-400" />
              <span className="font-semibold text-slate-900">Date & Duration:</span>
              <span>{formatEventDate(event.start_date, event.end_date)}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Info className="w-3.5 h-3.5 text-slate-400" />
              <span>Event Type: {event.event_type}</span>
            </div>
          </div>

          <div>
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Description</h4>
            <p className="text-sm text-slate-700 whitespace-pre-line leading-relaxed bg-white rounded-xl p-3 border border-slate-100 min-h-[70px]">
              {event.description || 'No description provided for this event.'}
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="h-10 px-5 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 transition-all"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── EVENT CREATE / EDIT FORM MODAL ──────────────────────────────────────────
const STANDARD_EVENT_TYPES = [
  'Holiday',
  'Examination',
  'Parent-Teacher Meeting',
  'School Event',
  'Meeting',
  'Academic Event',
  'Sports',
  'Cultural Event',
  'Result Day',
  'Other / Custom',
];

interface EventFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: CalendarEventCreatePayload | CalendarEventUpdatePayload) => Promise<void>;
  initialEvent?: CalendarEvent | null;
  title: string;
}

export const EventFormModal: React.FC<EventFormModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialEvent,
  title,
}) => {
  const [eventTitle, setEventTitle] = useState(initialEvent?.title || '');
  const [selectedType, setSelectedType] = useState(() => {
    if (!initialEvent) return 'School Event';
    return STANDARD_EVENT_TYPES.includes(initialEvent.event_type) ? initialEvent.event_type : 'Other / Custom';
  });
  const [customType, setCustomType] = useState(() => {
    if (!initialEvent) return '';
    return STANDARD_EVENT_TYPES.includes(initialEvent.event_type) ? '' : initialEvent.event_type;
  });
  const [description, setDescription] = useState(initialEvent?.description || '');
  const [startDate, setStartDate] = useState(() => {
    if (!initialEvent?.start_date) return new Date().toISOString().slice(0, 10);
    return initialEvent.start_date.slice(0, 10);
  });
  const [isMultiDay, setIsMultiDay] = useState(() => {
    if (!initialEvent) return false;
    return isMultiDayEvent(initialEvent.start_date, initialEvent.end_date);
  });
  const [endDate, setEndDate] = useState(() => {
    if (!initialEvent?.end_date) return new Date().toISOString().slice(0, 10);
    return initialEvent.end_date.slice(0, 10);
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync state if initialEvent changes
  React.useEffect(() => {
    if (initialEvent) {
      setEventTitle(initialEvent.title);
      const isStd = STANDARD_EVENT_TYPES.includes(initialEvent.event_type);
      setSelectedType(isStd ? initialEvent.event_type : 'Other / Custom');
      setCustomType(isStd ? '' : initialEvent.event_type);
      setDescription(initialEvent.description || '');
      setStartDate(initialEvent.start_date.slice(0, 10));
      const multi = isMultiDayEvent(initialEvent.start_date, initialEvent.end_date);
      setIsMultiDay(multi);
      setEndDate(initialEvent.end_date ? initialEvent.end_date.slice(0, 10) : initialEvent.start_date.slice(0, 10));
    } else {
      setEventTitle('');
      setSelectedType('School Event');
      setCustomType('');
      setDescription('');
      const today = new Date().toISOString().slice(0, 10);
      setStartDate(today);
      setIsMultiDay(false);
      setEndDate(today);
    }
    setError(null);
  }, [initialEvent, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventTitle.trim()) {
      setError('Event title is required.');
      return;
    }
    if (!startDate) {
      setError('Start date is required.');
      return;
    }

    const finalType = selectedType === 'Other / Custom' ? (customType.trim() || 'Custom Event') : selectedType;
    const finalEndDate = isMultiDay ? (endDate || startDate) : startDate;

    if (isMultiDay && finalEndDate < startDate) {
      setError('End date cannot be earlier than start date.');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      await onSubmit({
        title: eventTitle.trim(),
        event_type: finalType,
        description: description.trim() || undefined,
        start_date: startDate,
        end_date: finalEndDate,
      });
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save event. Please check inputs.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CalendarIcon className="w-5 h-5 text-emerald-600" />
            <h2 className="text-base font-bold text-slate-900">{title}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl">
              {error}
            </div>
          )}

          {/* Title */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Event Title *
            </label>
            <input
              type="text"
              required
              value={eventTitle}
              onChange={(e) => setEventTitle(e.target.value)}
              placeholder="e.g. Annual Sports Day, Mid-Term Exam, Diwali Break"
              className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
          </div>

          {/* Event Type */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Event Category / Type *
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full h-11 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none bg-white"
            >
              {STANDARD_EVENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>

            {selectedType === 'Other / Custom' && (
              <input
                type="text"
                value={customType}
                onChange={(e) => setCustomType(e.target.value)}
                placeholder="Enter custom category name (e.g. Science Fair, Workshop)"
                className="w-full h-11 px-4 rounded-xl border border-emerald-300 bg-emerald-50/40 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                required
              />
            )}
          </div>

          {/* Multi-Day Toggle */}
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200/80">
            <div>
              <p className="text-xs font-bold text-slate-900">Multi-Day Event</p>
              <p className="text-[11px] text-slate-500">Enable if event spans across multiple consecutive days</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isMultiDay}
                onChange={(e) => {
                  setIsMultiDay(e.target.checked);
                  if (!e.target.checked) {
                    setEndDate(startDate);
                  }
                }}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
            </label>
          </div>

          {/* Date Fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                {isMultiDay ? 'Start Date *' : 'Event Date *'}
              </label>
              <input
                type="date"
                required
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  if (!isMultiDay || endDate < e.target.value) {
                    setEndDate(e.target.value);
                  }
                }}
                className="w-full h-11 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>

            {isMultiDay && (
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  End Date *
                </label>
                <input
                  type="date"
                  required
                  min={startDate}
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full h-11 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Description (Optional)
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Additional details, schedule notes, guidelines..."
              className="w-full px-4 py-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 h-11 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold active:scale-95 transition-all disabled:opacity-60"
            >
              {saving ? 'Saving...' : initialEvent ? 'Update Event' : 'Create Event'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-5 h-11 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold active:scale-95 transition-all"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ─── MONTH / DATE CALENDAR NAVIGATION ─────────────────────────────────────────
interface MonthCalendarViewProps {
  currentMonth: Date;
  onMonthChange: (date: Date) => void;
  events: CalendarEvent[];
  selectedDate: string | null;
  onSelectDate: (dateStr: string | null) => void;
}

export const MonthCalendarView: React.FC<MonthCalendarViewProps> = ({
  currentMonth,
  onMonthChange,
  events,
  selectedDate,
  onSelectDate,
}) => {
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();

  const firstDayIndex = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const prevMonth = () => onMonthChange(new Date(year, month - 1, 1));
  const nextMonth = () => onMonthChange(new Date(year, month + 1, 1));
  const goToday = () => {
    const today = new Date();
    onMonthChange(new Date(today.getFullYear(), today.getMonth(), 1));
    onSelectDate(today.toISOString().slice(0, 10));
  };

  const monthName = currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  // Map events to date strings (YYYY-MM-DD)
  const eventDateMap: Record<string, CalendarEvent[]> = {};
  events.forEach((ev) => {
    const sDate = ev.start_date.slice(0, 10);
    const eDate = ev.end_date ? ev.end_date.slice(0, 10) : sDate;

    let cur = new Date(`${sDate}T00:00:00`);
    const end = new Date(`${eDate}T00:00:00`);

    while (cur <= end) {
      const key = cur.toISOString().slice(0, 10);
      if (!eventDateMap[key]) eventDateMap[key] = [];
      eventDateMap[key].push(ev);
      cur.setDate(cur.getDate() + 1);
    }
  });

  const todayStr = new Date().toISOString().slice(0, 10);

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-xs space-y-3">
      {/* Month navigation header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CalendarIcon className="w-4 h-4 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900">{monthName}</h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={goToday}
            className="px-2.5 py-1 text-[11px] font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-all"
          >
            Today
          </button>
          <button
            onClick={prevMonth}
            className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 transition-all"
            aria-label="Previous month"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={nextMonth}
            className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 transition-all"
            aria-label="Next month"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 text-center text-[11px] font-bold text-slate-400 border-b border-slate-100 pb-1.5">
        {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((d) => (
          <div key={d}>{d}</div>
        ))}
      </div>

      {/* Days grid */}
      <div className="grid grid-cols-7 gap-1 text-center text-xs">
        {Array.from({ length: firstDayIndex }).map((_, i) => (
          <div key={`empty-${i}`} className="h-9" />
        ))}

        {Array.from({ length: daysInMonth }).map((_, i) => {
          const dayNum = i + 1;
          const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
          const isToday = dateStr === todayStr;
          const isSelected = dateStr === selectedDate;
          const dayEvents = eventDateMap[dateStr] || [];
          const hasEvents = dayEvents.length > 0;

          return (
            <button
              key={dateStr}
              onClick={() => onSelectDate(isSelected ? null : dateStr)}
              className={`h-9 relative rounded-xl flex flex-col items-center justify-center transition-all ${
                isSelected
                  ? 'bg-emerald-600 text-white font-bold shadow-xs'
                  : isToday
                  ? 'bg-emerald-50 text-emerald-800 font-bold border border-emerald-300'
                  : hasEvents
                  ? 'hover:bg-slate-100 text-slate-900 font-medium'
                  : 'hover:bg-slate-50 text-slate-600'
              }`}
            >
              <span>{dayNum}</span>
              {hasEvents && (
                <span className="flex items-center gap-0.5 mt-0.5">
                  <span
                    className={`w-1 h-1 rounded-full ${
                      isSelected ? 'bg-white' : 'bg-emerald-500'
                    }`}
                  />
                  {dayEvents.length > 1 && (
                    <span
                      className={`w-1 h-1 rounded-full ${
                        isSelected ? 'bg-white' : 'bg-amber-500'
                      }`}
                    />
                  )}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {selectedDate && (
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
          <span className="text-slate-600">
            Selected: <span className="font-semibold text-slate-900">{formatEventDate(selectedDate)}</span>
          </span>
          <button
            onClick={() => onSelectDate(null)}
            className="text-emerald-600 hover:text-emerald-700 font-medium"
          >
            Show All Events
          </button>
        </div>
      )}
    </div>
  );
};

export default CalendarEventCard;

