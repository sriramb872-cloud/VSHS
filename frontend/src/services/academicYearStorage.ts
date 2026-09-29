// src/services/academicYearStorage.ts
/**
 * The *selected* academic year id, persisted across reloads.
 *
 * Kept in its own module (rather than inside `AcademicYearContext`) so the
 * axios request interceptor in `services/api.ts` can read it synchronously
 * without importing the context - importing the context there would create an
 * import cycle (api -> context -> services -> api).
 */

export const ACADEMIC_YEAR_STORAGE_KEY = 'scholaris_academic_year_id';

/** Fired whenever the selected year changes, so the UI can react. */
export const ACADEMIC_YEAR_CHANGE_EVENT = 'scholaris:academic-year-change';

/** Synchronous read used by the request interceptor. */
export function getStoredAcademicYearId(): number | null {
  try {
    const raw = localStorage.getItem(ACADEMIC_YEAR_STORAGE_KEY);
    if (!raw) return null;
    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  } catch {
    // Storage can throw in private-mode/quota situations; fall back to
    // "no explicit year" which makes the backend use the school's ACTIVE year.
    return null;
  }
}

/** Synchronous write so the next request picks the new year immediately. */
export function storeAcademicYearId(id: number | null): void {
  try {
    if (id === null) {
      localStorage.removeItem(ACADEMIC_YEAR_STORAGE_KEY);
    } else {
      localStorage.setItem(ACADEMIC_YEAR_STORAGE_KEY, String(id));
    }
  } catch {
    /* ignore - selection simply won't survive a reload */
  }
}
