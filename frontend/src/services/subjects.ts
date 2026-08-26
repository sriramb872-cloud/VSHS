// src/services/subjects.ts
import api from './api';
import { Subject, SubjectCreatePayload, SubjectUpdatePayload } from '../types';

export const subjectsService = {
  async listSubjects(params?: { skip?: number; limit?: number }): Promise<Subject[]> {
    const response = await api.get<Subject[]>('/subjects', { params });
    return response.data;
  },

  async getSubject(id: number): Promise<Subject> {
    const response = await api.get<Subject>(`/subjects/${id}`);
    return response.data;
  },

  async createSubject(payload: SubjectCreatePayload): Promise<Subject> {
    const response = await api.post<Subject>('/subjects', payload);
    return response.data;
  },

  async updateSubject(id: number, payload: SubjectUpdatePayload): Promise<Subject> {
    const response = await api.patch<Subject>(`/subjects/${id}`, payload);
    return response.data;
  },
};
