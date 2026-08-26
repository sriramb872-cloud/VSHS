// src/services/sections.ts
import api from './api';
import { Section, SectionCreatePayload, SectionUpdatePayload } from '../types';

export const sectionsService = {
  async listSections(params?: { grade_id?: number; skip?: number; limit?: number }): Promise<Section[]> {
    const response = await api.get<Section[]>('/sections', { params });
    return response.data;
  },

  async getSection(id: number): Promise<Section> {
    const response = await api.get<Section>(`/sections/${id}`);
    return response.data;
  },

  async createSection(payload: SectionCreatePayload): Promise<Section> {
    const response = await api.post<Section>('/sections', payload);
    return response.data;
  },

  async updateSection(id: number, payload: SectionUpdatePayload): Promise<Section> {
    const response = await api.patch<Section>(`/sections/${id}`, payload);
    return response.data;
  },
};
