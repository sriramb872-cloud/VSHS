// src/services/slipTests.ts
/**
 * Slip test API client.
 *
 * Two namespaces because the backend has two role-prefixed routers:
 *   - `/teacher/slip-tests`  (TEACHER only)
 *   - `/student/slip-tests`  (STUDENT only, read-only)
 *
 * Principal and Super Admin have no slip test endpoints at all, so there is no
 * third namespace here on purpose.
 *
 * The academic year is applied automatically by the axios interceptor
 * (`services/api.ts` attaches `X-Academic-Year-Id`), so callers never pass it
 * unless they need to override the header selector for one call.
 */
import api from './api';
import {
  SlipTest,
  SlipTestClassListResponse,
  SlipTestCreatePayload,
  SlipTestListResponse,
  SlipTestTeacherQueryParams,
  SlipTestTimeFilter,
  SlipTestUpdatePayload,
} from '../types/slipTest';

export const TEACHER_SLIP_TESTS_PATH = '/teacher/slip-tests';
export const STUDENT_SLIP_TESTS_PATH = '/student/slip-tests';

export const slipTestsService = {
  // -- teacher -------------------------------------------------------------

  /** Cards for every class + subject the teacher is assigned to. */
  async listMyClasses(
    academicYearId?: number,
  ): Promise<SlipTestClassListResponse> {
    const response = await api.get<SlipTestClassListResponse>(
      `${TEACHER_SLIP_TESTS_PATH}/classes`,
      { params: academicYearId != null ? { academic_year_id: academicYearId } : undefined },
    );
    return response.data;
  },

  async listMine(params?: SlipTestTeacherQueryParams): Promise<SlipTestListResponse> {
    const response = await api.get<SlipTestListResponse>(TEACHER_SLIP_TESTS_PATH, {
      params,
    });
    return response.data;
  },

  async getOne(id: number): Promise<SlipTest> {
    const response = await api.get<SlipTest>(`${TEACHER_SLIP_TESTS_PATH}/${id}`);
    return response.data;
  },

  async create(payload: SlipTestCreatePayload): Promise<SlipTest> {
    const response = await api.post<SlipTest>(TEACHER_SLIP_TESTS_PATH, payload);
    return response.data;
  },

  async update(id: number, payload: SlipTestUpdatePayload): Promise<SlipTest> {
    const response = await api.put<SlipTest>(`${TEACHER_SLIP_TESTS_PATH}/${id}`, payload);
    return response.data;
  },

  /** Soft cancel - the row is never deleted. */
  async cancel(id: number): Promise<SlipTest> {
    const response = await api.post<SlipTest>(`${TEACHER_SLIP_TESTS_PATH}/${id}/cancel`);
    return response.data;
  },

  // -- student (read-only) -------------------------------------------------

  async listForStudent(filter: SlipTestTimeFilter = 'upcoming'): Promise<SlipTestListResponse> {
    const response = await api.get<SlipTestListResponse>(STUDENT_SLIP_TESTS_PATH, {
      params: { filter },
    });
    return response.data;
  },

  async getForStudent(id: number): Promise<SlipTest> {
    const response = await api.get<SlipTest>(`${STUDENT_SLIP_TESTS_PATH}/${id}`);
    return response.data;
  },
};

export default slipTestsService;