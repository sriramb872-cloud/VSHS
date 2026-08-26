// src/services/academicYears.ts
import api from './api';
import { AcademicYear, AcademicYearCreatePayload, AcademicYearUpdatePayload } from '../types';

export const academicYearsService = {
  async listAcademicYears(params?: { skip?: number; limit?: number }): Promise<AcademicYear[]> {
    const response = await api.get<AcademicYear[]>('/academic-years', { params });
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
};
