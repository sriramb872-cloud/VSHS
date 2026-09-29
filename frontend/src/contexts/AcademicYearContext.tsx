// frontend/src/contexts/AcademicYearContext.tsx
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from 'react';
import { AcademicYear } from '../types';
import { academicYearsService } from '../services/academicYears';
import {
  ACADEMIC_YEAR_CHANGE_EVENT,
  getStoredAcademicYearId,
  storeAcademicYearId,
} from '../services/academicYearStorage';

export {
  ACADEMIC_YEAR_CHANGE_EVENT,
  ACADEMIC_YEAR_STORAGE_KEY,
  getStoredAcademicYearId,
  storeAcademicYearId,
} from '../services/academicYearStorage';

interface AcademicYearContextType {
  /** Every year of the signed-in user's school, newest first. */
  academicYears: AcademicYear[];
  /** The school's ACTIVE year (never null once loaded, if one exists). */
  activeYear: AcademicYear | null;
  /** The year currently being viewed (falls back to the active year). */
  selectedYear: AcademicYear | null;
  selectedYearId: number | null;
  /** True while the first load is in flight. */
  loading: boolean;
  /** Last refresh error, if any. */
  error: string | null;
  /** Viewing a CLOSED/ARCHIVED year -> screens are read-only. */
  isHistorical: boolean;
  /** Viewing the ACTIVE year (the default working mode). */
  isActiveYear: boolean;
  selectYear: (id: number) => void;
  activateYear: (id: number) => Promise<AcademicYear>;
  refreshYears: () => Promise<AcademicYear[]>;
}

const AcademicYearContext = createContext<AcademicYearContextType | undefined>(undefined);

export const AcademicYearProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [selectedYearId, setSelectedYearId] = useState<number | null>(getStoredAcademicYearId());
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshYears = useCallback(async (): Promise<AcademicYear[]> => {
    if (!localStorage.getItem('scholaris_access_token')) {
      // Signed out: don't fire an unauthenticated request (it would 401 and
      // bounce the user to /login).
      setAcademicYears([]);
      setSelectedYearId(null);
      storeAcademicYearId(null);
      setLoading(false);
      return [];
    }
    try {
      const years = await academicYearsService.listAcademicYears();
      setAcademicYears(years);
      setError(null);
      return years;
    } catch (err) {
      setError('Failed to load academic years');
      return [];
    }
  }, []);

  // Load on mount, then re-load whenever auth changes (login has no reload).
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      const years = await refreshYears();
      if (cancelled) return;
      const stored = getStoredAcademicYearId();
      const storedExists = stored !== null && years.some((y) => y.id === stored);
      if (!storedExists) {
        const fallback = years.find((y) => y.is_active) ?? years[0] ?? null;
        const nextId = fallback?.id ?? null;
        storeAcademicYearId(nextId);
        setSelectedYearId(nextId);
      }
      setLoading(false);
    };
    load();
    window.addEventListener('scholaris:auth-changed', load);
    return () => {
      cancelled = true;
      window.removeEventListener('scholaris:auth-changed', load);
    };
  }, [refreshYears]);

  const selectYear = useCallback((id: number) => {
    storeAcademicYearId(id);
    setSelectedYearId(id);
    window.dispatchEvent(new CustomEvent(ACADEMIC_YEAR_CHANGE_EVENT, { detail: id }));
  }, []);

  /**
   * Activate a year. The backend closes the previously ACTIVE year in the same
   * transaction, so a full refresh is enough to keep the UI consistent.
   */
  const activateYear = useCallback(
    async (id: number): Promise<AcademicYear> => {
      const updated = await academicYearsService.activateAcademicYear(id);
      await refreshYears();
      selectYear(updated.id);
      return updated;
    },
    [refreshYears, selectYear]
  );

  const activeYear = useMemo(
    () => academicYears.find((y) => y.is_active) ?? null,
    [academicYears]
  );

  const selectedYear = useMemo(() => {
    if (academicYears.length === 0) return null;
    return (
      academicYears.find((y) => y.id === selectedYearId) ??
      activeYear ??
      academicYears[0] ??
      null
    );
  }, [academicYears, selectedYearId, activeYear]);

  const isHistorical =
    !!selectedYear && (selectedYear.status === 'CLOSED' || selectedYear.status === 'ARCHIVED');

  const value: AcademicYearContextType = {
    academicYears,
    activeYear,
    selectedYear,
    selectedYearId: selectedYear?.id ?? null,
    loading,
    error,
    isHistorical,
    isActiveYear: !!selectedYear && selectedYear.status === 'ACTIVE',
    selectYear,
    activateYear,
    refreshYears,
  };

  return <AcademicYearContext.Provider value={value}>{children}</AcademicYearContext.Provider>;
};

export const useAcademicYear = (): AcademicYearContextType => {
  const context = useContext(AcademicYearContext);
  if (!context) {
    throw new Error('useAcademicYear must be used within an AcademicYearProvider');
  }
  return context;
};

export default AcademicYearProvider;
