// src/services/attendance.ts
import api from './api';
import { AttendanceRecord, AttendanceMarkPayload } from '../types';
import { AttendanceReport } from '../types/attendance-report';

export interface AttendanceParams {
  section_id?: number;
  attendance_date?: string;
  student_id?: number;
  skip?: number;
  limit?: number;
}

export interface AttendanceSummary {
  student_id: number;
  total_days: number;
  present_days: number;
  absent_days: number;
  late_days: number;
  leave_days: number;
  percentage: number;
  records: Array<{ id: number; date: string; status: string; remarks?: string | null }>;
}

export interface AttendanceReportParams {
  start_date: string;
  end_date: string;
  grade_id?: number;
  section_id?: number;
}

export const attendanceService = {
  async getAttendance(params?: AttendanceParams): Promise<AttendanceRecord[]> {
    const response = await api.get<AttendanceRecord[]>('/attendance', { params });
    return response.data;
  },

  async markAttendance(payload: AttendanceMarkPayload): Promise<AttendanceRecord> {
    const response = await api.post<AttendanceRecord>('/attendance', payload);
    return response.data;
  },

  async markBulkAttendance(records: AttendanceMarkPayload[]): Promise<AttendanceRecord[]> {
    const results: AttendanceRecord[] = [];
    for (const record of records) {
      const r = await api.post<AttendanceRecord>('/attendance', record);
      results.push(r.data);
    }
    return results;
  },

  async getStudentAttendance(studentId: number): Promise<AttendanceRecord[]> {
    const response = await api.get<AttendanceRecord[]>('/attendance', {
      params: { student_id: studentId },
    });
    return response.data;
  },

  async getStudentAttendanceSummary(studentId: number): Promise<AttendanceSummary> {
    const response = await api.get<AttendanceSummary>(`/attendance/student/${studentId}`);
    return response.data;
  },

  /**
   * Aggregated attendance over a date range, scoped server-side to the
   * caller's tenant. Available to SUPER_ADMIN, PRINCIPAL and TEACHER.
   */
  async getAttendanceReport(params: AttendanceReportParams): Promise<AttendanceReport> {
    const response = await api.get<AttendanceReport>('/attendance/reports/summary', { params });
    return response.data;
  },

  async updateAttendance(id: number, payload: { status?: string; remarks?: string }): Promise<AttendanceRecord> {
    const response = await api.patch<AttendanceRecord>(`/attendance/${id}`, payload);
    return response.data;
  },
  async voidAttendance(id: number): Promise<AttendanceRecord> {
    const response = await api.post<AttendanceRecord>(`/attendance/${id}/void`);
    return response.data;
  },
};

export default attendanceService;
