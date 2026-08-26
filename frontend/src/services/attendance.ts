// src/services/attendance.ts
import api from './api';
import { AttendanceRecord, AttendanceMarkPayload } from '../types';

export interface AttendanceParams {
  section_id?: number;
  attendance_date?: string;
  student_id?: number;
  skip?: number;
  limit?: number;
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

  async getStudentAttendanceSummary(studentId: number): Promise<{
    student_id: number;
    total_days: number;
    present_days: number;
    absent_days: number;
    late_days: number;
    leave_days: number;
    percentage: number;
    records: Array<{ id: number; date: string; status: string; remarks?: string }>;
  }> {
    const response = await api.get(`/attendance/student/${studentId}`);
    return response.data;
  },
};

export default attendanceService;
