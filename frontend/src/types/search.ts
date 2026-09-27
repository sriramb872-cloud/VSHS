// src/types/search.ts
/**
 * Result shapes returned by `GET /search`.
 *
 * The endpoint is role-scoped on the server: a Super Admin searches every
 * school, a Principal their own, a Teacher their own sections, and a Student
 * only themselves. The client does not filter - it renders what it is given.
 */

export interface StudentSearchHit {
  id: number;
  name?: string | null;
  admission_number?: string | null;
  roll_number?: string | null;
  school_id?: number | null;
}

export interface TeacherSearchHit {
  id: number;
  name?: string | null;
  employee_id?: string | null;
  school_id?: number | null;
}

export interface SubjectSearchHit {
  id: number;
  name?: string | null;
  code?: string | null;
  school_id?: number | null;
}

export interface SectionSearchHit {
  id: number;
  name?: string | null;
  grade_id?: number | null;
  grade_name?: string | null;
  school_id?: number | null;
}

export interface GlobalSearchResults {
  query: string;
  students: StudentSearchHit[];
  teachers: TeacherSearchHit[];
  subjects: SubjectSearchHit[];
  sections: SectionSearchHit[];
}

export const EMPTY_SEARCH_RESULTS: GlobalSearchResults = {
  query: '',
  students: [],
  teachers: [],
  subjects: [],
  sections: [],
};
