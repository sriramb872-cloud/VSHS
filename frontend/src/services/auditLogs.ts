// src/services/auditLogs.ts
import api from './api';

export interface AuditLog {
  id?: number;
  action?: string;
  user_id?: number;
  school_id?: number;
  resource_type?: string;
  resource_id?: string;
  details?: Record<string, any>;
  timestamp?: string;
}

export const auditLogsService = {
  async listAuditLogs(params?: { skip?: number; limit?: number }): Promise<AuditLog[]> {
    const response = await api.get<AuditLog[]>('/audit-logs', { params });
    return response.data;
  },
};
