// src/services/roles.ts
import api from './api';
import { AppUser } from '../types';
import { RoleAssignmentResult, RoleListResponse } from '../types/roles';

export const rolesService = {
  /** The assignable role catalogue with live user counts. SUPER_ADMIN only. */
  async listRoles(): Promise<RoleListResponse> {
    const response = await api.get<RoleListResponse>('/roles');
    return response.data;
  },

  /** Plain role-name list, for populating a role picker. */
  async listAssignableRoles(): Promise<string[]> {
    const response = await api.get<string[]>('/roles/assignable');
    return response.data;
  },

  /** Users, optionally filtered by role, for the assignment table. */
  async listRoleAssignments(params?: { role?: string; skip?: number; limit?: number }): Promise<AppUser[]> {
    const response = await api.get<AppUser[]>('/roles/users', { params });
    return response.data;
  },

  /** Change a user's role. */
  async assignRole(userId: number, role: string, reason?: string): Promise<RoleAssignmentResult> {
    const response = await api.patch<RoleAssignmentResult>(`/roles/users/${userId}`, {
      role,
      reason,
    });
    return response.data;
  },
};

export default rolesService;
