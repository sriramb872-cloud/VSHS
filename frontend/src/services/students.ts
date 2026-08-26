import api from './api';
import { Student, StudentCreatePayload, StudentUpdatePayload } from '../types';

export interface StudentFilterParams {
  skip?: number;
  limit?: number;
  grade_id?: number;
  section_id?: number;
  academic_year_id?: number;
}

export const studentsService = {
  async listStudents(params?: StudentFilterParams): Promise<Student[]> {
    const response = await api.get<Student[]>('/students', { params });
    return response.data;
  },

  async createStudent(payload: StudentCreatePayload): Promise<Student> {
    const response = await api.post<Student>('/students', payload);
    return response.data;
  },

  async getStudent(id: number): Promise<Student> {
    const response = await api.get<Student>(`/students/${id}`);
    return response.data;
  },

  async getStudentById(id: number): Promise<Student> {
    return this.getStudent(id);
  },

  async getMyStudentProfile(): Promise<Student> {
    const response = await api.get<Student>('/students/me');
    return response.data;
  },

  async updateMyStudentProfile(payload: StudentUpdatePayload): Promise<Student> {
    const response = await api.patch<Student>('/students/me', payload);
    return response.data;
  },

  async updateStudent(id: number, payload: StudentUpdatePayload): Promise<Student> {
    const response = await api.patch<Student>(`/students/${id}`, payload);
    return response.data;
  },
};

export default studentsService;

