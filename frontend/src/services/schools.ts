// src/services/schools.ts
import api from './api';
import { School, SchoolCreatePayload, SchoolUpdatePayload } from '../types';

export const schoolsService = {
  async listSchools(params?: { skip?: number; limit?: number }): Promise<School[]> {
    const response = await api.get<School[]>('/schools', { params });
    return response.data;
  },

  async getSchool(id: number): Promise<School> {
    const response = await api.get<School>(`/schools/${id}`);
    return response.data;
  },

  async createSchool(payload: SchoolCreatePayload): Promise<School> {
    const response = await api.post<School>('/schools', payload);
    return response.data;
  },

  async updateSchool(id: number, payload: SchoolUpdatePayload): Promise<School> {
    const response = await api.patch<School>(`/schools/${id}`, payload);
    return response.data;
  },
};
