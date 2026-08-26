// src/services/homework.ts
import api from './api';
import { Homework, HomeworkCreatePayload, HomeworkUpdatePayload, HomeworkListResponse } from '../types';

export interface HomeworkParams {
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  teacher_id?: number;
  due_date?: string;
  skip?: number;
  limit?: number;
}

export const homeworkService = {
  async listHomework(params?: HomeworkParams): Promise<HomeworkListResponse> {
    const response = await api.get<HomeworkListResponse>('/homework/', { params });
    return response.data;
  },

  async getHomework(id: number): Promise<Homework> {
    const response = await api.get<Homework>(`/homework/${id}`);
    return response.data;
  },

  async getHomeworkById(id: number): Promise<Homework> {
    return this.getHomework(id);
  },

  async createHomework(payload: HomeworkCreatePayload): Promise<Homework> {
    const response = await api.post<Homework>('/homework/', payload);
    return response.data;
  },

  async updateHomework(id: number, payload: HomeworkUpdatePayload): Promise<Homework> {
    const response = await api.patch<Homework>(`/homework/${id}`, payload);
    return response.data;
  },

  async deleteHomework(id: number): Promise<void> {
    await api.delete(`/homework/${id}`);
  },
};