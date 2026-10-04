// src/types/slipTest.ts
/**
 * Mirrors the backend `app/schemas/slip_test.py`.
 *
 * "Marks" here means the MAXIMUM / TOTAL marks of the test - not what any
 * student obtained. Recording obtained marks is out of scope for V1.
 *
 * DATE HANDLING: `scheduled_date` is a plain school-local calendar day
 * ("2026-11-02") and is treated as a STRING everywhere in this feature.
 * `new Date(scheduled_date)` parses it as UTC midnight, which shifts it a day
 * backwards for anyone east of Greenwich - that is exactly the bug the project
 * already documents in `src/utils/date.ts`. Compare and format the string
 * instead (see `formatSlipTestDate` below).
 */

/** Lifecycle values, matching the MySQL ENUM on `slip_tests.status`. */
export type SlipTestStatus = 'scheduled' | 'cancelled' | 'completed';

export interface SlipTest {
  id: number;
  school_id: number;
  academic_year_id: number;
  grade_id: number;
  section_id: number;
  subject_id: number;
  teacher_id: number;

  title: string;
  description?: string | null;
  /** School-local `YYYY-MM-DD`. Never parse this with `new Date(...)`. */
  scheduled_date: string;
  /** `HH:MM:SS` or `HH:MM`, or null when the test has no fixed start time. */
  start_time?: string | null;
  duration_minutes?: number | null;
  max_marks: number;
  status: SlipTestStatus | string;

  created_at: string;
  updated_at?: string | null;

  // Resolved server-side in bulk (never N+1).
  grade_name?: string | null;
  section_name?: string | null;
  subject_name?: string | null;
  teacher_name?: string | null;

  /** Derived per request from the school-local today. */
  is_past: boolean;
  /** Advisory only - set when another test already exists on the same slot/date. */
  duplicate_warning?: string | null;
}

export interface SlipTestListResponse {
  total: number;
  items: SlipTest[];
}

/** One "10-A - Mathematics" card on the teacher's landing page. */
export interface SlipTestClassCard {
  grade_id: number;
  grade_name?: string | null;
  section_id: number;
  section_name?: string | null;
  subject_id: number;
  subject_name?: string | null;
  display_name: string;
  upcoming_count: number;
  total_count: number;
}

export interface SlipTestClassListResponse {
  total: number;
  items: SlipTestClassCard[];
}

export interface SlipTestCreatePayload {
  grade_id: number;
  section_id: number;
  subject_id: number;
  title: string;
  description?: string | null;
  scheduled_date: string;
  start_time?: string | null;
  duration_minutes?: number | null;
  max_marks: number;
  /** Optional: the backend falls back to the selected/active academic year. */
  academic_year_id?: number | null;
}

/** PATCH-shaped: only the fields present are applied. */
export interface SlipTestUpdatePayload {
  title?: string;
  description?: string | null;
  scheduled_date?: string;
  start_time?: string | null;
  duration_minutes?: number | null;
  max_marks?: number;
}

export interface SlipTestTeacherQueryParams {
  /** Section (class) id. Must be a class the teacher is assigned to. */
  class?: number;
  /** Explicit alias for `class`. */
  section_id?: number;
  subject?: number;
  /** Explicit alias for `subject`. */
  subject_id?: number;
  status?: SlipTestStatus | string;
  academic_year_id?: number;
  skip?: number;
  limit?: number;
}

export type SlipTestTimeFilter = 'upcoming' | 'past' | 'all';

/** Mirrors the backend's MAX_MARKS_LIMIT. */
export const SLIP_TEST_MAX_MARKS = 1000;
/** Mirrors the backend's MAX_DURATION_MINUTES. */
export const SLIP_TEST_MAX_DURATION = 600;
/** Mirrors the backend's MAX_DESCRIPTION_LENGTH. */
export const SLIP_TEST_MAX_DESCRIPTION = 1000;

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/**
 * Format `YYYY-MM-DD` for display WITHOUT a timezone round trip.
 *
 * Splits the string and reads the parts directly, so a student in any timezone
 * sees the date the school wrote down.
 */
export function formatSlipTestDate(isoDate?: string | null): string {
  if (!isoDate) return '';
  const match = String(isoDate).slice(0, 10).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return String(isoDate);
  const [, year, month, day] = match;
  return `${Number(day)} ${MONTHS[Number(month) - 1]} ${year}`;
}

/** `2026-11-02` -> `Mon` - again, pure string arithmetic. */
export function slipTestWeekday(isoDate?: string | null): string | null {
  if (!isoDate) return null;
  const match = String(isoDate).slice(0, 10).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  // Construct at UTC noon so the local `getDay()` cannot roll over a day.
  const parsed = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]), 12));
  return parsed.toLocaleDateString('en-US', { weekday: 'short', timeZone: 'UTC' });
}

/**
 * `HH:MM` / `HH:MM:SS` -> `9:30 AM`.
 *
 * `<input type="time">` gives `HH:MM` on every modern browser, so this only has
 * to normalise the shape - no timezone maths involved.
 */
export function formatSlipTestTime(value?: string | null): string | null {
  if (!value) return null;
  const raw = String(value).trim();
  const match = raw.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) return raw;
  let hours = Number(match[1]);
  const minutes = match[2];
  const meridiem = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12;
  if (hours === 0) hours = 12;
  return `${hours}:${minutes} ${meridiem}`;
}

/**
 * Today as `YYYY-MM-DD` in the browser's own timezone.
 *
 * Reuses the project-wide helper (`src/utils/date.ts`) rather than
 * `toISOString()`, which would return the UTC day.
 */
export function todaySlipTestDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** True when the test's date is strictly before today (string comparison). */
export function isSlipTestPast(isoDate?: string | null): boolean {
  if (!isoDate) return false;
  return String(isoDate).slice(0, 10) < todaySlipTestDate();
}