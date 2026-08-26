// src/pages/principal/Calendar.tsx
import React, { useEffect, useState, useMemo } from 'react';
import { calendarService } from '../../services/calendar';
import { CalendarEvent, CalendarEventCreatePayload, CalendarEventUpdatePayload } from '../../types/calendar';
import {
  CalendarEventCard,
  EventFormModal,
  EventDetailModal,
  MonthCalendarView,
} from '../../components/calendar';
import { CalendarDays, Plus, Search, Calendar as CalendarIcon, List, Filter } from 'lucide-react';
import { LoadingSkeleton, EmptyState, ConfirmDialog } from '../../components/shared';

const EVENT_CATEGORY_FILTERS = [
  'All',
  'Holiday',
  'Examination',
  'Parent-Teacher Meeting',
  'School Event',
  'Meeting',
  'Academic Event',
  'Sports',
  'Cultural Event',
];

export const PrincipalCalendarPage: React.FC = () => {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Views
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
  const [showMonthView, setShowMonthView] = useState<boolean>(true);

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);
  const [viewingEvent, setViewingEvent] = useState<CalendarEvent | null>(null);
  const [deleteEventId, setDeleteEventId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await calendarService.listEvents();
      setEvents(data.items || []);
    } catch (err: any) {
      console.error('Failed to load calendar events', err);
      setError('Unable to load calendar events. Please refresh.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleCreateSubmit = async (payload: CalendarEventCreatePayload | CalendarEventUpdatePayload) => {
    await calendarService.createEvent(payload as CalendarEventCreatePayload);
    await fetchEvents();
  };

  const handleEditSubmit = async (payload: CalendarEventCreatePayload | CalendarEventUpdatePayload) => {
    if (!editingEvent) return;
    await calendarService.updateEvent(editingEvent.id, payload as CalendarEventUpdatePayload);
    await fetchEvents();
  };

  const handleDeleteConfirm = async () => {
    if (!deleteEventId) return;
    try {
      setDeleting(true);
      await calendarService.deleteEvent(deleteEventId);
      setEvents((prev) => prev.filter((e) => e.id !== deleteEventId));
      setDeleteEventId(null);
    } catch (err) {
      console.error('Failed to delete event', err);
    } finally {
      setDeleting(false);
    }
  };

  // Filtered events
  const filteredEvents = useMemo(() => {
    return events.filter((ev) => {
      // Category filter
      if (selectedCategory !== 'All') {
        if (!ev.event_type.toLowerCase().includes(selectedCategory.toLowerCase())) {
          return false;
        }
      }

      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = ev.title.toLowerCase().includes(q);
        const matchesDesc = (ev.description || '').toLowerCase().includes(q);
        const matchesType = ev.event_type.toLowerCase().includes(q);
        if (!matchesTitle && !matchesDesc && !matchesType) return false;
      }

      // Date filter
      if (selectedDate) {
        const sDate = ev.start_date.slice(0, 10);
        const eDate = ev.end_date ? ev.end_date.slice(0, 10) : sDate;
        if (selectedDate < sDate || selectedDate > eDate) {
          return false;
        }
      }

      return true;
    });
  }, [events, selectedCategory, searchQuery, selectedDate]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Academic Calendar</h1>
          <p className="text-xs text-slate-500">
            Create and manage school-wide events, exams, holidays, and meetings
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowMonthView((v) => !v)}
            className="h-10 px-3.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-all"
          >
            {showMonthView ? <List className="w-4 h-4" /> : <CalendarIcon className="w-4 h-4" />}
            <span>{showMonthView ? 'Hide Month' : 'Show Month'}</span>
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="h-10 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all flex-shrink-0"
          >
            <Plus className="w-4 h-4" />
            Add Event
          </button>
        </div>
      </div>

      {/* Month Calendar Interactive View */}
      {showMonthView && (
        <MonthCalendarView
          currentMonth={currentMonth}
          onMonthChange={setCurrentMonth}
          events={events}
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
        />
      )}

      {/* Search Bar */}
      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search events by title, description, or type..."
          className="w-full h-11 pl-10 pr-4 rounded-xl border border-slate-200/80 bg-white text-slate-900 text-xs sm:text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none placeholder:text-slate-400 shadow-xs"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600 font-semibold"
          >
            Clear
          </button>
        )}
      </div>

      {/* Filter Pills */}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 no-scrollbar">
        {EVENT_CATEGORY_FILTERS.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`h-8 px-3.5 rounded-full text-xs font-semibold whitespace-nowrap flex-shrink-0 transition-all ${
              selectedCategory === cat
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Selected Date Indicator Banner */}
      {selectedDate && (
        <div className="bg-emerald-50 border border-emerald-200/80 rounded-xl p-3 flex items-center justify-between text-xs text-emerald-900">
          <div className="flex items-center gap-2">
            <CalendarIcon className="w-4 h-4 text-emerald-600" />
            <span>
              Showing events on <strong className="font-bold">{selectedDate}</strong>
            </span>
          </div>
          <button
            onClick={() => setSelectedDate(null)}
            className="font-bold text-emerald-700 hover:text-emerald-800 underline ml-2"
          >
            Clear Date Filter
          </button>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-700">
          {error}
        </div>
      )}

      {/* Events List */}
      {loading ? (
        <LoadingSkeleton type="card" count={4} />
      ) : filteredEvents.length === 0 ? (
        <EmptyState
          title="No Events Found"
          description={
            selectedDate
              ? `No events scheduled for ${selectedDate}.`
              : searchQuery || selectedCategory !== 'All'
              ? 'No events match your selected filters.'
              : 'No calendar events created yet. Start by creating a school event.'
          }
          icon={<CalendarDays className="w-10 h-10 text-slate-300" />}
          action={{ label: 'Add Event', onClick: () => setIsCreateOpen(true) }}
        />
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>
              Showing <strong className="font-semibold text-slate-800">{filteredEvents.length}</strong> event{filteredEvents.length === 1 ? '' : 's'}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filteredEvents.map((ev) => (
              <CalendarEventCard
                key={ev.id}
                event={ev}
                isPrincipal={true}
                onEdit={(event) => setEditingEvent(event)}
                onDelete={(id) => setDeleteEventId(id)}
                onViewDetails={(event) => setViewingEvent(event)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Create Event Modal */}
      <EventFormModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSubmit={handleCreateSubmit}
        title="Create Calendar Event"
      />

      {/* Edit Event Modal */}
      <EventFormModal
        isOpen={!!editingEvent}
        onClose={() => setEditingEvent(null)}
        initialEvent={editingEvent}
        onSubmit={handleEditSubmit}
        title="Edit Calendar Event"
      />

      {/* View Details Modal */}
      <EventDetailModal
        event={viewingEvent}
        onClose={() => setViewingEvent(null)}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!deleteEventId}
        onClose={() => setDeleteEventId(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Calendar Event"
        message="Are you sure you want to delete this event? This will remove it from the school calendar for all teachers and students."
        confirmLabel={deleting ? 'Deleting...' : 'Delete Event'}
        variant="danger"
      />
    </div>
  );
};

export default PrincipalCalendarPage;

