import api from './api';
import { Teacher, TeacherCreatePayload, TeacherUpdatePayload } from '../types';

export const teachersService = {
  async listTeachers(params?: { skip?: number; limit?: number }): Promise<Teacher[]> {
    const response = await api.get<Teacher[]>('/teachers', { params });
    return response.data;
  },

  async createTeacher(payload: TeacherCreatePayload): Promise<Teacher> {
    const response = await api.post<Teacher>('/teachers', payload);
    return response.data;
  },

  async getTeacher(id: number): Promise<Teacher> {
    const response = await api.get<Teacher>(`/teachers/${id}`);
    return response.data;
  },

  async getMyTeacherProfile(): Promise<Teacher> {
    const response = await api.get<Teacher>('/teachers/me');
    return response.data;
  },

  async updateMyTeacherProfile(payload: TeacherUpdatePayload): Promise<Teacher> {
    const response = await api.patch<Teacher>('/teachers/me', payload);
    return response.data;
  },

  async updateTeacher(id: number, payload: TeacherUpdatePayload): Promise<Teacher> {
    const response = await api.patch<Teacher>(`/teachers/${id}`, payload);
    return response.data;
  },

  async assignMeAsClassTeacher(sectionId: number): Promise<Teacher> {
    const response = await api.post<Teacher>('/teachers/me/assign-class-teacher', { section_id: sectionId });
    return response.data;
  },
};

export default teachersService;

