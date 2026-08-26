// src/services/auditLogs.ts
import api from './api';

export interface AuditLog {
  id?: number;
  action?: string;
  user_id?: number;
  resource?: string;
  resource_id?: number;
  details?: string;
  created_at?: string;
}

export const auditLogsService = {
  async listAuditLogs(params?: { skip?: number; limit?: number }): Promise<AuditLog[]> {
    const response = await api.get<AuditLog[]>('/audit-logs', { params });
    return response.data;
  },
};
