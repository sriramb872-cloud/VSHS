// src/pages/superadmin/Reports.tsx
import React, { useState, useEffect } from 'react';
import { FileText, Download } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton } from '../../components/shared';

export const SuperAdminReports: React.FC = () => {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch reports
    setLoading(false);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">System Reports</h1>
        <p className="text-xs text-slate-500">Generated platform & audit exports</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : reports.length === 0 ? (
        <EmptyState
          title="No Reports Generated"
          description="There are no system reports available for download."
          icon={<FileText className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {reports.map((rep, idx) => (
            <MobileListItem
              key={idx}
              title={rep.name}
              subtitle={`Generated: ${rep.date || 'Today'}`}
              icon={<FileText className="w-5 h-5 text-indigo-600" />}
              avatarBg="bg-indigo-50 text-indigo-600"
              actions={
                <button className="p-2 rounded-lg bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition-all">
                  <Download className="w-4 h-4" />
                </button>
              }
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminReports;