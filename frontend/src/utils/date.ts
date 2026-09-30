// src/utils/date.ts
/**
 * Single source of truth for the calendar/time maths used by the timetable,
 * attendance, homework and dashboard screens.
 *
 * Every helper works on the **browser-local** calendar: the school day, the
 * "current class" and the weekday tabs must agree with the wall clock the user
 * is actually looking at. `Date.prototype.toISOString()` is deliberately avoided
 * here - it converts to UTC, which can push the date a day backwards/forwards
 * around midnight and is the classic source of "my timetable shows yesterday"
 * bugs.
 *
 * Timetable times arrive from the API either as a display string
 * ("09:00 AM" - `serialize_timetable()` uses `%I:%M %p`) or as a raw time
 * ("09:00:00" / "13:30"). Both are parsed by `parseTimeToMinutes()`.
 */

/** Timetable day order used by every weekday tab in the app. */
export const WEEKDAYS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
] as const;

export type Weekday = (typeof WEEKDAYS)[number];

/** Timetable slot lifecycle, derived from the wall clock. */
export type TimetableSlotStatus = 'NOW' | 'UPCOMING' | 'COMPLETED';

/**
 * The real weekday name for the given (default: current) local date.
 * Always one of `WEEKDAYS`, so it can be compared directly against the
 * `day_of_week` column the backend stores (`"Monday"`, `"TUESDAY"`, ...).
 */
export function getCurrentWeekday(date: Date = new Date()): string {
  return date.toLocaleDateString('en-US', { weekday: 'long' });
}

/** `true` when `value` is one of the six timetable weekdays. */
export function isWeekday(value: unknown): value is Weekday {
  return typeof value === 'string' && (WEEKDAYS as readonly string[]).includes(value);
}

/**
 * Local calendar date as `YYYY-MM-DD` (never UTC).
 * Safe to send as `attendance_date` or to compare against stored record dates.
 */
export function getLocalDateString(date: Date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** Minutes elapsed since local midnight, e.g. 09:07 -> 547. */
export function getCurrentTimeMinutes(date: Date = new Date()): number {
  return date.getHours() * 60 + date.getMinutes();
}

/**
 * Parse any of "9:05", "09:05", "09:05:00", "9:05 PM", "09:05 am" into minutes
 * since midnight. Returns `null` when the value cannot be understood so callers
 * can distinguish "unknown time" from "midnight".
 */
export function parseTimeToMinutes(value?: string | number | null): number | null {
  if (value === null || value === undefined) return null;
  const raw = String(value).trim();
  if (!raw) return null;

  const match = raw.match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i);
  if (!match) return null;

  let hours = Number(match[1]);
  const minutes = Number(match[2]);
  const meridiem = (match[3] || '').toUpperCase();

  if (meridiem === 'PM' && hours < 12) hours += 12;
  if (meridiem === 'AM' && hours === 12) hours = 0;

  if (hours > 23 || minutes > 59) return null;
  return hours * 60 + minutes;
}

/**
 * Status of a timetable period against the current local time:
 *   - before `start_time`            -> `UPCOMING`
 *   - between `start_time`/`end_time`-> `NOW`   (inclusive of both bounds)
 *   - after `end_time`               -> `COMPLETED`
 *
 * A slot with an unparseable start time is reported as `UPCOMING` rather than
 * silently claiming the class already finished.
 */
export function getTimetableSlotStatus(
  start?: string | null,
  end?: string | null,
  now: Date = new Date()
): TimetableSlotStatus {
  const startMinutes = parseTimeToMinutes(start);
  if (startMinutes === null) return 'UPCOMING';

  const endMinutes = parseTimeToMinutes(end);
  const currentMinutes = getCurrentTimeMinutes(now);

  if (currentMinutes < startMinutes) return 'UPCOMING';
  if (endMinutes !== null && currentMinutes > endMinutes) return 'COMPLETED';
  return 'NOW';
}

/** Convenience wrapper: is this period running at `now`? */
export function isCurrentTimetableSlot(
  start?: string | null,
  end?: string | null,
  now: Date = new Date()
): boolean {
  return getTimetableSlotStatus(start, end, now) === 'NOW';
}

/**
 * The date of `weekday` inside the week that contains `now` (Monday-first).
 * Used to turn a weekday tab into a concrete `attendance_date` without ever
 * reaching outside the current week.
 *
 * Weekdays later than today in the current week resolve to a future date
 * (attendance cannot exist yet); earlier ones resolve to a past date.
 */
export function getDateForWeekday(weekday: string, now: Date = new Date()): Date {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const todayIndex = (today.getDay() + 6) % 7; // Monday = 0 ... Sunday = 6
  const targetIndex = WEEKDAYS.indexOf(weekday as Weekday);

  if (targetIndex < 0) return today;

  const result = new Date(today);
  result.setDate(result.getDate() + (targetIndex - todayIndex));
  return result;
}

/** Sort timetable rows ascending by start time (unparseable rows last). */
export function sortByStartTime<T extends { start_time?: string | null }>(slots: T[]): T[] {
  return [...slots].sort((a, b) => {
    const left = parseTimeToMinutes(a.start_time);
    const right = parseTimeToMinutes(b.start_time);
    if (left === null && right === null) return 0;
    if (left === null) return 1;
    if (right === null) return -1;
    return left - right;
  });
}

/** `true` when `date` (default: today) is the same local calendar day as `now`. */
export function isToday(date: Date, now: Date = new Date()): boolean {
  return getLocalDateString(date) === getLocalDateString(now);
}

export default {
  WEEKDAYS,
  getCurrentWeekday,
  isWeekday,
  getLocalDateString,
  getCurrentTimeMinutes,
  parseTimeToMinutes,
  getTimetableSlotStatus,
  isCurrentTimetableSlot,
  getDateForWeekday,
  sortByStartTime,
  isToday,
};
