// src/services/enrollments.ts
import api from './api';
import { StudentEnrollment, EnrollmentCreatePayload } from '../types';

export interface EnrollmentParams {
  academic_year_id?: number;
  grade_id?: number;
  section_id?: number;
  skip?: number;
  limit?: number;
}

export const enrollmentsService = {
  async listEnrollments(params?: EnrollmentParams): Promise<StudentEnrollment[]> {
    const response = await api.get<StudentEnrollment[]>('/student-enrollments', { params });
    return response.data;
  },

  async createEnrollment(payload: EnrollmentCreatePayload): Promise<StudentEnrollment> {
    const response = await api.post<StudentEnrollment>('/student-enrollments', payload);
    return response.data;
  },

  async deleteEnrollment(id: number): Promise<void> {
    await api.delete(`/student-enrollments/${id}`);
  },
};
