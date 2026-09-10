import api from './api';
import { TeacherSubject, TeacherSubjectCreatePayload } from '../types';

export const teacherSubjectsService = {
  async listBySchool(): Promise<TeacherSubject[]> {
    const res = await api.get<TeacherSubject[]>('/teacher-subjects');
    return res.data; // no teacher_id param → backend returns all assignments for current_user.school_id
  },
  async listByTeacher(teacherId: number): Promise<TeacherSubject[]> {
    const res = await api.get<TeacherSubject[]>('/teacher-subjects', { params: { teacher_id: teacherId } });
    return res.data;
  },
  async assign(payload: TeacherSubjectCreatePayload): Promise<TeacherSubject> {
    const res = await api.post<TeacherSubject>('/teacher-subjects', payload);
    return res.data;
  },
  async remove(id: number): Promise<void> {
    await api.delete(`/teacher-subjects/${id}`);
  },
};
