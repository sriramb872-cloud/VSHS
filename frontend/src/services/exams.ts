// src/services/exams.ts
import api from './api';
import { Exam, ExamCreatePayload, ExamUpdatePayload, ExamListResponse } from '../types';

export interface ExamParams {
  academic_year_id?: number;
  exam_type?: string;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  teacher_id?: number;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
}

export const examsService = {
  async listExams(params?: ExamParams): Promise<ExamListResponse> {
    const response = await api.get<ExamListResponse>('/exams/', { params });
    return response.data;
  },

  async getExam(id: number): Promise<Exam> {
    const response = await api.get<Exam>(`/exams/${id}`);
    return response.data;
  },

  async createExam(payload: ExamCreatePayload): Promise<Exam> {
    const response = await api.post<Exam>('/exams/', payload);
    return response.data;
  },

  async updateExam(id: number, payload: ExamUpdatePayload): Promise<Exam> {
    const response = await api.patch<Exam>(`/exams/${id}`, payload);
    return response.data;
  },

  async deleteExam(id: number): Promise<void> {
    await api.delete(`/exams/${id}`);
  },
};
