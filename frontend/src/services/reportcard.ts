// src/services/reportcard.ts
import api from './api';
import type { ReportCardListResponse, ReportCardResponse } from '../types/reportcard';

export interface ReportCardParams {
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  student_id?: number;
  exam_id?: number;
  skip?: number;
  limit?: number;
}

export const reportCardService = {
  async generateReportCards(academicYearId: number, sectionId: number, examId?: number, termName = 'Term 1'): Promise<ReportCardListResponse> {
    const response = await api.post<ReportCardListResponse>('/report-cards/generate', null, {
      params: { academic_year_id: academicYearId, section_id: sectionId, exam_id: examId, term_name: termName },
    });
    return response.data;
  },
  async listReportCards(params?: ReportCardParams): Promise<ReportCardListResponse> {
    const response = await api.get<ReportCardListResponse>('/report-cards/', { params });
    return response.data;
  },

  async getReportCard(studentId: number, academicYearId: number, examId?: number): Promise<ReportCardResponse> {
    const response = await api.get<ReportCardResponse>(`/report-cards/${studentId}`, {
      params: { academic_year_id: academicYearId, exam_id: examId },
    });
    return response.data;
  },

  async updateRemarks(
    studentId: number,
    academicYearId: number,
    teacherRemarks: string,
    examId?: number
  ): Promise<ReportCardResponse> {
    const response = await api.patch<ReportCardResponse>(`/report-cards/${studentId}/remarks`, {
      teacher_remarks: teacherRemarks,
    }, {
      // academic_year_id (and the optional exam_id) are query parameters on
      // the backend route, not body fields - sending them in the body made
      // FastAPI answer 422 "Field required" for the missing query param.
      params: { academic_year_id: academicYearId, exam_id: examId },
    });
    return response.data;
  },
};
