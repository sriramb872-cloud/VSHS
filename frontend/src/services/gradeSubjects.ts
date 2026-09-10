import api from './api';
import { GradeSubject, GradeSubjectCreatePayload } from '../types';

export const gradeSubjectsService = {
  async listByGrade(gradeId: number): Promise<GradeSubject[]> {
    const res = await api.get<GradeSubject[]>('/grade-subjects', { params: { grade_id: gradeId } });
    return res.data;
  },
  async assign(payload: GradeSubjectCreatePayload): Promise<GradeSubject> {
    const res = await api.post<GradeSubject>('/grade-subjects', payload);
    return res.data;
  },
  async remove(id: number): Promise<void> {
    await api.delete(`/grade-subjects/${id}`);
  },
};
