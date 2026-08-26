// src/services/grades.ts
import api from './api';
import { Grade, GradeCreatePayload, GradeUpdatePayload } from '../types';

export const gradesService = {
  async listGrades(params?: { skip?: number; limit?: number }): Promise<Grade[]> {
    const response = await api.get<Grade[]>('/grades', { params });
    return response.data;
  },

  async getGrade(id: number): Promise<Grade> {
    const response = await api.get<Grade>(`/grades/${id}`);
    return response.data;
  },

  async createGrade(payload: GradeCreatePayload): Promise<Grade> {
    const response = await api.post<Grade>('/grades', payload);
    return response.data;
  },

  async updateGrade(id: number, payload: GradeUpdatePayload): Promise<Grade> {
    const response = await api.patch<Grade>(`/grades/${id}`, payload);
    return response.data;
  },
};
