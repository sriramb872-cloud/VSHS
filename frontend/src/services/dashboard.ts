// src/services/dashboard.ts
import api from './api';
import {
  SuperAdminDashboard,
  PrincipalDashboard,
  TeacherDashboard,
  StudentDashboard,
} from '../types/dashboard';

export const dashboardService = {
  async getSuperAdminDashboard(): Promise<SuperAdminDashboard> {
    const response = await api.get<SuperAdminDashboard>('/dashboard/super-admin');
    return response.data;
  },

  async getPrincipalDashboard(): Promise<PrincipalDashboard> {
    const response = await api.get<PrincipalDashboard>('/dashboard/principal');
    return response.data;
  },

  async getTeacherDashboard(): Promise<TeacherDashboard> {
    const response = await api.get<TeacherDashboard>('/dashboard/teacher');
    return response.data;
  },

  async getStudentDashboard(): Promise<StudentDashboard> {
    const response = await api.get<StudentDashboard>('/dashboard/student');
    return response.data;
  },
};