// src/services/marks.ts
import api from './api';
import { Mark, MarksEntryCreatePayload, MarksListResponse } from '../types';

export interface MarksParams {
  exam_id?: number;
  student_id?: number;
  grade_id?: number;
  section_id?: number;
  subject_id?: number;
  academic_year_id?: number;
  teacher_id?: number;
  skip?: number;
  limit?: number;
}

export const marksService = {
  async listMarks(params?: MarksParams): Promise<MarksListResponse> {
    const response = await api.get<MarksListResponse>('/marks/', { params });
    return response.data;
  },

  async saveMarks(payload: MarksEntryCreatePayload): Promise<Mark[]> {
    const response = await api.post<Mark[]>('/marks/', payload);
    return response.data;
  },
};