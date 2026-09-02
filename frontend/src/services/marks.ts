// src/services/marks.ts
import api from './api';
import {
  Mark,
  MarksSubmitPayload,
  FormativeMarksSubmitPayload,
  MarksListResponse,
  MarksQueryParams,
  StudentMarksViewResponse,
} from '../types/marks';

export const marksService = {
  async listMarks(params?: MarksQueryParams): Promise<MarksListResponse> {
    const response = await api.get<MarksListResponse>('/marks/', { params });
    return response.data;
  },

  async submitMarks(payload: MarksSubmitPayload): Promise<Mark[]> {
    const response = await api.post<Mark[]>('/marks/submit', payload);
    return response.data;
  },

  async submitFormativeMarks(payload: FormativeMarksSubmitPayload): Promise<any> {
    const response = await api.post('/marks/submit-formative', payload);
    return response.data;
  },

  async saveMarks(payload: MarksSubmitPayload): Promise<Mark[]> {
    const response = await api.post<Mark[]>('/marks/submit', payload);
    return response.data;
  },

  async getMyMarks(): Promise<StudentMarksViewResponse> {
    const response = await api.get<StudentMarksViewResponse>('/marks/my-marks');
    return response.data;
  },
};