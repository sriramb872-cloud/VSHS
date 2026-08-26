// src/services/reportcard.ts
import api from './api';
import { ReportCard, ReportCardListResponse } from '../types';

export interface ReportCardParams {
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  student_id?: number;
  skip?: number;
  limit?: number;
}

export const reportCardService = {
  async listReportCards(params?: ReportCardParams): Promise<ReportCardListResponse> {
    const response = await api.get<ReportCardListResponse>('/report-cards/', { params });
    return response.data;
  },

  async getReportCard(studentId: number, academicYearId: number): Promise<ReportCard> {
    const response = await api.get<ReportCard>(`/report-cards/${studentId}`, {
      params: { academic_year_id: academicYearId },
    });
    return response.data;
  },

  async updateRemarks(
    studentId: number,
    academicYearId: number,
    teacherRemarks: string
  ): Promise<ReportCard> {
    const response = await api.patch<ReportCard>(`/report-cards/${studentId}/remarks`, {
      teacher_remarks: teacherRemarks,
      academic_year_id: academicYearId,
    });
    return response.data;
  },
};