// src/pages/superadmin/AuditLogs.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { FileText } from 'lucide-react';
import { LoadingSkeleton, EmptyState, ErrorState } from '../../components/shared';
import { auditLogsService, AuditLog } from '../../services/auditLogs';

export const SuperAdminAuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await auditLogsService.listAuditLogs();
      setLogs(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Audit Logs</h1>
        <p className="text-xs text-slate-500">System activity history</p>
      </div>

      {error && <ErrorState title="Load Error" message="Failed to load audit logs" onRetry={fetchLogs} />}

      {loading ? (
        <LoadingSkeleton type="list" count={5} />
      ) : logs.length === 0 ? (
        <EmptyState
          title="No Audit Logs"
          description="No system activity has been recorded yet."
          icon={<FileText className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2">
          {logs.map((log, idx) => (
            <div key={log.id || idx} className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{log.action || 'Action'}</p>
                  <p className="text-xs text-slate-500">{log.resource}{log.resource_id ? ` #${log.resource_id}` : ''}</p>
                  {log.details && <p className="text-xs text-slate-400 mt-1">{log.details}</p>}
                </div>
                {log.created_at && (
                  <p className="text-xs text-slate-400">{new Date(log.created_at).toLocaleDateString()}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminAuditLogs;