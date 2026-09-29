// src/services/academicYears.ts
import api from './api';
import { AcademicYear, AcademicYearCreatePayload, AcademicYearUpdatePayload } from '../types';

export const academicYearsService = {
  async listAcademicYears(params?: { skip?: number; limit?: number }): Promise<AcademicYear[]> {
    // Explicit `allow_all` sentinel is not needed here: this endpoint is the
    // school's own year catalogue and must never be narrowed by the header.
    const response = await api.get<AcademicYear[]>('/academic-years', {
      params,
      // Listing years must NOT be filtered by the currently selected year.
      headers: { 'X-Academic-Year-Id': '' },
    });
    return response.data;
  },

  /** The school's ACTIVE year (or the year selected via the header). */
  async getActiveAcademicYear(): Promise<AcademicYear> {
    const response = await api.get<AcademicYear>('/academic-years/active');
    return response.data;
  },

  async getAcademicYear(id: number): Promise<AcademicYear> {
    const response = await api.get<AcademicYear>(`/academic-years/${id}`);
    return response.data;
  },

  async createAcademicYear(payload: AcademicYearCreatePayload): Promise<AcademicYear> {
    const response = await api.post<AcademicYear>('/academic-years', payload);
    return response.data;
  },

  async updateAcademicYear(id: number, payload: AcademicYearUpdatePayload): Promise<AcademicYear> {
    const response = await api.patch<AcademicYear>(`/academic-years/${id}`, payload);
    return response.data;
  },

  /** Make this year the school's single ACTIVE year (previous one is closed). */
  async activateAcademicYear(id: number): Promise<AcademicYear> {
    const response = await api.post<AcademicYear>(`/academic-years/${id}/activate`);
    return response.data;
  },

  /** Move a year to ARCHIVED (kept visible, no longer writable). */
  async archiveAcademicYear(id: number): Promise<AcademicYear> {
    const response = await api.post<AcademicYear>(`/academic-years/${id}/archive`);
    return response.data;
  },

  /** Only succeeds for years that are not active and hold no data (409 else). */
  async deleteAcademicYear(id: number): Promise<void> {
    await api.delete(`/academic-years/${id}`);
  },
};
