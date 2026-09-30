// src/hooks/useClock.ts
import { useEffect, useState } from 'react';
import { getCurrentWeekday, getLocalDateString } from '../utils/date';

/**
 * A `Date` that re-reads the wall clock on a timer.
 *
 * The tick is aligned to the next minute boundary, then repeats once a minute:
 * timetable periods change status only on whole minutes, so this is accurate to
 * the second a class starts/ends while doing effectively no work. It also
 * resynchronises as soon as the tab becomes visible again (a laptop waking up
 * or a backgrounded PWA tab can otherwise be minutes stale).
 *
 * No network requests happen on this timer - the caller already has the day's
 * timetable in memory.
 */
export function useCurrentTime(): Date {
  const [now, setNow] = useState<Date>(() => new Date());

  useEffect(() => {
    let handle: number;
    const tick = () => setNow(new Date());

    // Wake exactly when the next minute turns over, then keep the cadence.
    const msToNextMinute = 60_000 - (Date.now() % 60_000);
    handle = window.setTimeout(() => {
      tick();
      handle = window.setInterval(tick, 60_000);
    }, msToNextMinute + 50);

    const onVisibilityChange = () => {
      if (!document.hidden) tick();
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      window.clearTimeout(handle);
      window.clearInterval(handle);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);

  return now;
}

/**
 * Today's real weekday name ("Monday" ... "Saturday").
 *
 * The state only changes when the calendar day actually rolls over, so the
 * interval costs a comparison instead of a re-render every minute. Weekday tabs
 * therefore open on - and stay on - the real current day.
 */
export function useCurrentWeekday(): string {
  const [weekday, setWeekday] = useState<string>(() => getCurrentWeekday());

  useEffect(() => {
    const check = () => {
      const next = getCurrentWeekday();
      setWeekday((previous) => (previous === next ? previous : next));
    };
    const interval = window.setInterval(check, 60_000);
    window.addEventListener('focus', check);
    window.addEventListener('visibilitychange', check);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener('focus', check);
      window.removeEventListener('visibilitychange', check);
    };
  }, []);

  return weekday;
}

/**
 * Today's local calendar date (`YYYY-MM-DD`). Updates when the day changes.
 */
export function useToday(): string {
  const [today, setToday] = useState<string>(() => getLocalDateString());

  useEffect(() => {
    const check = () => {
      const next = getLocalDateString();
      setToday((previous) => (previous === next ? previous : next));
    };
    const interval = window.setInterval(check, 60_000);
    window.addEventListener('focus', check);
    window.addEventListener('visibilitychange', check);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener('focus', check);
      window.removeEventListener('visibilitychange', check);
    };
  }, []);

  return today;
}

export default useCurrentTime;
