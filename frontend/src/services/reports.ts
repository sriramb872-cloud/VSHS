// src/services/reports.ts
import api from './api';
import { PlatformReport } from '../types/reports';

export interface PlatformReportParams {
  start_date?: string;
  end_date?: string;
  school_id?: number;
  include_inactive_schools?: boolean;
}

export const reportsService = {
  /** Cross-school platform report. SUPER_ADMIN only. */
  async getPlatformReport(params?: PlatformReportParams): Promise<PlatformReport> {
    const response = await api.get<PlatformReport>('/reports/platform', { params });
    return response.data;
  },
};

export default reportsService;
