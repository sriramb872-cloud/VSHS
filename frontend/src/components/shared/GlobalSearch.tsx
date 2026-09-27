// src/components/shared/GlobalSearch.tsx
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, GraduationCap, UserCheck, BookOpen, LayoutGrid, Loader2 } from 'lucide-react';
import { searchService } from '../../services/search';
import { GlobalSearchResults } from '../../types/search';
import { EMPTY_SEARCH_RESULTS } from '../../types/search';
import errorMessage from '../../helpers/errorMessage';

interface ResultGroup {
  key: keyof Omit<GlobalSearchResults, 'query'>;
  label: string;
  icon: React.ReactNode;
  items: Array<{ id: number; primary: string; secondary?: string | null }>;
  /** Where tapping a result goes; `:id` is appended. */
  detailBase?: string;
}

/** Where each result type lives, per role. The server has already scoped the
 *  results to what this user may see, so the links are pure navigation. */
const DESTINATIONS: Record<string, { detailBase?: string; listBase?: string }> = {
  SUPER_ADMIN: {
    detailBase: '/superadmin/users',
    listBase: '/superadmin/users',
  },
  PRINCIPAL: {
    detailBase: '/principal/students',
    listBase: '/principal/students',
  },
  TEACHER: {
    detailBase: '/teacher/students',
    listBase: '/teacher/students',
  },
  STUDENT: {
    detailBase: '/student/dashboard',
    listBase: '/student/dashboard',
  },
};

const SECTION_DESTINATIONS: Record<string, string> = {
  SUPER_ADMIN: '/superadmin/dashboard',
  PRINCIPAL: '/principal/sections',
  TEACHER: '/teacher/timetable',
  STUDENT: '/student/timetable',
};

export const GlobalSearch: React.FC<{ role: string }> = ({ role }) => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [term, setTerm] = useState('');
  const [results, setResults] = useState<GlobalSearchResults>(EMPTY_SEARCH_RESULTS);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      // Focus after the dialog paints.
      const t = window.setTimeout(() => inputRef.current?.focus(), 30);
      return () => window.clearTimeout(t);
    }
    setTerm('');
    setResults(EMPTY_SEARCH_RESULTS);
    setError(null);
    setHasSearched(false);
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === 'Escape' && open) setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  // Debounced query.
  useEffect(() => {
    const q = term.trim();
    if (!open || q.length === 0) {
      setResults(EMPTY_SEARCH_RESULTS);
      setHasSearched(false);
      setError(null);
      return;
    }
    let cancelled = false;
    setSearching(true);
    const timer = window.setTimeout(() => {
      searchService
        .globalSearch({ q })
        .then((res) => {
          if (cancelled) return;
          setResults(res);
          setHasSearched(true);
          setError(null);
        })
        .catch((err) => {
          if (cancelled) return;
          setError(errorMessage(err, 'Search is unavailable right now.'));
          setResults(EMPTY_SEARCH_RESULTS);
          setHasSearched(true);
        })
        .finally(() => { if (!cancelled) setSearching(false); });
    }, 280);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [term, open]);

  const dest = DESTINATIONS[role] || DESTINATIONS.STUDENT;

  const groups: ResultGroup[] = [
    {
      key: 'students',
      label: 'Students',
      icon: <GraduationCap className="w-3.5 h-3.5" />,
      detailBase: dest.detailBase,
      items: results.students.map((s) => ({
        id: s.id,
        primary: s.name || s.admission_number || `Student #${s.id}`,
        secondary: s.admission_number,
      })),
    },
    {
      key: 'teachers',
      label: 'Teachers',
      icon: <UserCheck className="w-3.5 h-3.5" />,
      detailBase: dest.detailBase,
      items: results.teachers.map((t) => ({
        id: t.id,
        primary: t.name || t.employee_id || `Teacher #${t.id}`,
        secondary: t.employee_id,
      })),
    },
    {
      key: 'subjects',
      label: 'Subjects',
      icon: <BookOpen className="w-3.5 h-3.5" />,
      items: results.subjects.map((s) => ({
        id: s.id,
        primary: s.name || `Subject #${s.id}`,
        secondary: s.code,
      })),
    },
    {
      key: 'sections',
      label: 'Sections',
      icon: <LayoutGrid className="w-3.5 h-3.5" />,
      items: results.sections.map((s) => ({
        id: s.id,
        primary: s.grade_name ? `${s.grade_name} - ${s.name}` : (s.name || `Section #${s.id}`),
      })),
    },
  ];

  const totalHits = groups.reduce((sum, g) => sum + g.items.length, 0);

  const go = useCallback(
    (path: string) => {
      setOpen(false);
      navigate(path);
    },
    [navigate],
  );

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="p-2 rounded-full text-slate-600 hover:bg-slate-100 active:scale-95 transition-all"
        aria-label="Search"
        title="Search (Ctrl+K)"
      >
        <Search className="w-5 h-5" />
      </button>

      {open && (
        <div className="fixed inset-0 z-[70] flex items-start justify-center p-4 pt-[10vh]">
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs"
            onClick={() => setOpen(false)}
          />
          <div className="relative z-10 w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="flex items-center gap-2 px-4 border-b border-slate-100">
              <Search className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={term}
                onChange={(e) => setTerm(e.target.value)}
                placeholder="Search students, teachers, subjects, sections…"
                className="flex-1 h-12 text-sm text-slate-900 placeholder-slate-400 focus:outline-none bg-transparent"
                aria-label="Search query"
              />
              {searching && <Loader2 className="w-4 h-4 text-slate-400 animate-spin flex-shrink-0" />}
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex-shrink-0"
                aria-label="Close search"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="max-h-[55vh] overflow-y-auto">
              {error ? (
                <p className="p-4 text-xs text-rose-600">{error}</p>
              ) : term.trim().length === 0 ? (
                <p className="p-4 text-xs text-slate-400">
                  Type at least one character. Results are limited to what your role can access.
                </p>
              ) : hasSearched && totalHits === 0 && !searching ? (
                <p className="p-4 text-xs text-slate-400">
                  No matches for &ldquo;{term.trim()}&rdquo;.
                </p>
              ) : (
                groups.map((group) =>
                  group.items.length === 0 ? null : (
                    <div key={group.key} className="py-1.5">
                      <p className="px-4 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        {group.icon}
                        {group.label}
                      </p>
                      {group.items.map((item) => (
                        <button
                          key={`${group.key}-${item.id}`}
                          type="button"
                          onClick={() => {
                            if (group.key === 'sections') {
                              go(SECTION_DESTINATIONS[role] || '/');
                            } else if (group.detailBase) {
                              go(`${group.detailBase}/${item.id}`);
                            }
                          }}
                          className="w-full text-left px-4 py-2 hover:bg-slate-50 transition-colors"
                        >
                          <p className="text-sm text-slate-900 font-medium truncate">{item.primary}</p>
                          {item.secondary ? (
                            <p className="text-[11px] text-slate-500 truncate">{item.secondary}</p>
                          ) : null}
                        </button>
                      ))}
                    </div>
                  ),
                )
              )}
            </div>

            <div className="px-4 py-2 border-t border-slate-100 bg-slate-50 text-[10px] text-slate-400 flex items-center justify-between">
              <span>
                {hasSearched && !error ? `${totalHits} result${totalHits === 1 ? '' : 's'}` : 'Ctrl+K to open'}
              </span>
              <span>Esc to close</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default GlobalSearch;
