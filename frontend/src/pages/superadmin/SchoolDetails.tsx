// src/pages/superadmin/SchoolDetails.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Building, Edit, Activity } from 'lucide-react';
import { schoolsService } from '../../services/schools';
import { School } from '../../types';
import { LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';

export const SuperAdminSchoolDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [school, setSchool] = useState<School | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchSchool = () => {
    if (!id) return;
    setLoading(true);
    setError(false);
    schoolsService.getSchool(Number(id))
      .then(setSchool)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchSchool(); }, [id]);

  if (loading) return <LoadingSkeleton type="form" count={3} />;
  if (error || !school) return <ErrorState title="School Not Found" message="Could not load school details." onRetry={fetchSchool} />;

  return (
    <div className="max-w-lg mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/superadmin/schools')} className="p-2 rounded-xl hover:bg-slate-100">
          <ArrowLeft className="w-5 h-5 text-slate-600" />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-slate-900">{school.name}</h1>
          <p className="text-xs text-slate-500">School Details</p>
        </div>
        <button
          onClick={() => navigate(`/superadmin/schools/${id}/edit`)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 text-white font-bold text-xs"
        >
          <Edit className="w-4 h-4" />
          <span>Edit</span>
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
        <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center">
            <Building className="w-6 h-6 text-indigo-600" />
          </div>
          <div>
            <p className="text-base font-bold text-slate-900">{school.name}</p>
            <p className="text-xs text-slate-500">Code: {school.code}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-slate-500 mb-1">Status</p>
            <StatusBadge status={school.is_active ? 'ACTIVE' : 'INACTIVE'} />
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-1">School Code</p>
            <p className="text-sm font-semibold text-slate-900">{school.code}</p>
          </div>
          {school.created_at && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Created</p>
              <p className="text-sm text-slate-700">{new Date(school.created_at).toLocaleDateString()}</p>
            </div>
          )}
          {school.updated_at && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Last Updated</p>
              <p className="text-sm text-slate-700">{new Date(school.updated_at).toLocaleDateString()}</p>
            </div>
          )}
        </div>

        <div className="pt-3 border-t border-slate-100">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Activity className="w-3.5 h-3.5" />
            <span>School ID: {school.id}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SuperAdminSchoolDetails;