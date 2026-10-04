import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardService } from '../../services/dashboard';
import { StudentDashboard } from '../../types/dashboard';
import { StatCard, LoadingSkeleton, ErrorState, EmptyState } from '../../components/shared';
import { Calendar, BookOpen, Award, Bell, Clock, MapPin, User, ClipboardCheck } from 'lucide-react';
import { usePet } from '../../pet/PetContext';
import { useCurrentTime } from '../../hooks/useClock';
import {
  getTimetableSlotStatus,
  parseTimeToMinutes,
  sortByStartTime,
  TimetableSlotStatus,
} from '../../utils/date';

/** Human "starts in 12 min" / "ends in 5 min" label from the wall clock. */
const relativeMinutesLabel = (target: string | null | undefined, now: Date): string | null => {
  const targetMinutes = parseTimeToMinutes(target);
  if (targetMinutes === null) return null;
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  const diff = targetMinutes - nowMinutes;
  if (diff === 0) return 'right now';
  if (diff > 0) return `in ${diff} min`;
  return `${Math.abs(diff)} min ago`;
};

const STATUS_LABEL: Record<TimetableSlotStatus, string> = {
  NOW: 'Now',
  UPCOMING: 'Upcoming',
  COMPLETED: 'Done',
};

const STATUS_CLASS: Record<TimetableSlotStatus, string> = {
  NOW: 'bg-[var(--brand)] text-white',
  UPCOMING: 'bg-[var(--brand-light)] text-[var(--brand-strong)]',
  COMPLETED: 'bg-slate-100 text-slate-500',
};

export const StudentDashboardPage: React.FC = () => {
  const [data, setData] = useState<StudentDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const navigate = useNavigate();
  const { setDashboardData } = usePet();

  // Ticks once a minute (aligned to the minute boundary) - no API calls, the
  // timetable below is already in memory. Drives the "Now / Up next" badges.
  const now = useCurrentTime();

  const fetchDashboard = () => {
    setLoading(true);
    setError(false);
    dashboardService.getStudentDashboard()
      .then(next => { setData(next); setDashboardData('STUDENT', { attendancePercentage: next.attendance_percentage, overdueHomework: next.pending_homework.filter((item: any) => new Date(item.due_date) < new Date()).length, unreadAnnouncements: next.announcements.length }); })
      .catch((err) => { console.error(err); setError(true); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchDashboard(); }, []);

  // Today's periods, sorted by start time and classified against the wall clock.
  const daySlots = useMemo(() => {
    const slots = sortByStartTime((data?.todays_timetable || []) as any[]);
    return slots.map(slot => ({
      slot,
      status: getTimetableSlotStatus(slot.start_time, slot.end_time, now),
    }));
  }, [data, now]);

  const currentSlot = daySlots.find(entry => entry.status === 'NOW');
  const upcomingSlots = daySlots.filter(entry => entry.status === 'UPCOMING');
  const completedCount = daySlots.filter(entry => entry.status === 'COMPLETED').length;
  const heroSlot = currentSlot || upcomingSlots[0];
  // Remaining upcoming periods after the one highlighted in the hero card.
  const restUpcoming = heroSlot ? upcomingSlots.filter(entry => entry !== heroSlot) : upcomingSlots;

  if (loading) return <LoadingSkeleton type="metrics" count={4} />;
  if (error || !data) return <ErrorState title="Dashboard Error" message="Unable to load your dashboard." onRetry={fetchDashboard} />;

  return (
    <div className="space-y-5">
      <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-[var(--brand)] to-[var(--brand-hover)] text-white shadow-md relative overflow-hidden">
        <div className="absolute right-0 top-0 translate-x-4 -translate-y-4 w-40 h-40 rounded-full bg-white/10 blur-2xl pointer-events-none" />
        <div className="relative z-10">
          <h1 className="text-lg sm:text-xl font-bold">My Dashboard</h1>
          <p className="text-xs sm:text-sm text-white/80 mt-1">Here's where things stand today.</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Attendance Rate" value={`${data.attendance_percentage}%`} icon={<Award className="w-5 h-5" />} iconBgClass="bg-emerald-50 text-emerald-600" onClick={() => navigate('/student/attendance')} />
        <StatCard label="Pending Homework" value={data.pending_homework.length} icon={<BookOpen className="w-5 h-5" />} iconBgClass="bg-amber-50 text-amber-600" onClick={() => navigate('/student/homework')} />
        <StatCard label="Upcoming Exams" value={data.upcoming_exams.length} icon={<Calendar className="w-5 h-5" />} iconBgClass="bg-rose-50 text-rose-600" onClick={() => navigate('/student/exams')} />
        <StatCard label="Announcements" value={data.announcements.length} icon={<Bell className="w-5 h-5" />} iconBgClass="bg-[var(--brand-light)] text-[var(--brand)]" onClick={() => navigate('/student/announcements')} />
        {/* Slip tests: still-scheduled tests for this student's own section. */}
        <StatCard
          label="Upcoming Slip Tests"
          value={data.upcoming_slip_tests ?? 0}
          icon={<ClipboardCheck className="w-5 h-5" />}
          iconBgClass="bg-sky-50 text-sky-600"
          onClick={() => navigate('/student/slip-tests')}
        />
      </div>

      {/* Current / Upcoming class - derived from today's timetable + local clock */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Current & Upcoming Class</h3>
          <span className="text-[11px] font-semibold text-slate-400 tabular-nums">
            {now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </span>
        </div>

        {daySlots.length === 0 ? (
          <div className="px-4 pb-4">
            <EmptyState
              title="No Classes Today"
              description="There are no periods scheduled for today. Check your timetable for the rest of the week."
              icon={<Calendar className="w-10 h-10 text-slate-300" />}
              action={{ label: 'View Full Timetable', onClick: () => navigate('/student/timetable') }}
            />
          </div>
        ) : (
          <>
            {heroSlot && (
              <div className="mx-4 mb-3 rounded-xl border-2 border-[var(--brand-border)] bg-[var(--brand-light)]/60 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${STATUS_CLASS[heroSlot.status]}`}>
                        {heroSlot.status === 'NOW' ? 'Happening now' : 'Next up'}
                      </span>
                      <span className="text-[11px] font-semibold text-slate-500">
                        {relativeMinutesLabel(heroSlot.status === 'NOW' ? heroSlot.slot.end_time : heroSlot.slot.start_time, now)}
                      </span>
                    </div>
                    <p className="text-base font-bold text-slate-900 truncate">
                      {heroSlot.slot.subject_name || 'Class'}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" /> {heroSlot.slot.start_time} – {heroSlot.slot.end_time}
                      </span>
                      {heroSlot.slot.teacher_name && (
                        <span className="inline-flex items-center gap-1">
                          <User className="w-3.5 h-3.5" /> {heroSlot.slot.teacher_name}
                        </span>
                      )}
                      {heroSlot.slot.room_number && (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5" /> {heroSlot.slot.room_number}
                        </span>
                      )}
                    </div>
                    {(heroSlot.slot.grade_name || heroSlot.slot.section_name) && (
                      <p className="mt-1 text-[11px] text-slate-400">
                        {[heroSlot.slot.grade_name, heroSlot.slot.section_name].filter(Boolean).join(' · ')}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div className="divide-y divide-slate-100">
              {restUpcoming.slice(0, 5).map((entry, i) => (
                <div key={entry.slot.id ?? i} className="flex items-center gap-3 px-4 py-3">
                  <div className="w-9 h-9 rounded-xl bg-[var(--brand-light)] flex items-center justify-center flex-shrink-0">
                    <Clock className="w-4 h-4 text-[var(--brand)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">{entry.slot.subject_name || 'Class'}</p>
                    <p className="text-xs text-slate-500">
                      {entry.slot.start_time} – {entry.slot.end_time}
                      {entry.slot.teacher_name ? ` · ${entry.slot.teacher_name}` : ''}
                    </p>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${STATUS_CLASS[entry.status]}`}>
                    {relativeMinutesLabel(entry.slot.start_time, now) || STATUS_LABEL[entry.status]}
                  </span>
                </div>
              ))}

              {completedCount > 0 && completedCount === daySlots.length ? (
                <div className="px-4 py-3 text-xs text-slate-400">All classes finished for today.</div>
              ) : completedCount > 0 ? (
                <div className="px-4 py-3 text-xs text-slate-400">
                  {completedCount} of {daySlots.length} period{daySlots.length === 1 ? '' : 's'} completed today
                </div>
              ) : null}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default StudentDashboardPage;
