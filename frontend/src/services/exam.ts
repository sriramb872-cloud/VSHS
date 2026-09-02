// src/services/exam.ts
import api from './api';
import {
  Exam,
  ExamListResponse,
  ExamQueryParams,
  ExamCreatePayload,
  ExamUpdatePayload,
  ExamSubject,
  MarksStatusResponse,
  ExamPublishResponse,
} from '../types/exam';

export const examService = {
  async listExams(params?: ExamQueryParams): Promise<ExamListResponse> {
    const response = await api.get<ExamListResponse>('/exams/', { params });
    return response.data;
  },

  async getExamById(id: number): Promise<Exam> {
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

  async getExamSubjects(examId: number): Promise<ExamSubject[]> {
    const response = await api.get<ExamSubject[]>(`/exams/${examId}/subjects`);
    return response.data;
  },

  async getMarksStatus(examId: number): Promise<MarksStatusResponse> {
    const response = await api.get<MarksStatusResponse>(`/exams/${examId}/marks-status`);
    return response.data;
  },

  async publishExam(examId: number): Promise<ExamPublishResponse> {
    const response = await api.post<ExamPublishResponse>(`/exams/${examId}/publish`);
    return response.data;
  },
};