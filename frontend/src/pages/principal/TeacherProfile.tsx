// src/pages/principal/TeacherProfile.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  User,
  Phone,
  Mail,
  Briefcase,
  Calendar,
  Award,
  BookOpen,
  Layers,
  School,
} from 'lucide-react';
import { teachersService } from '../../services/teachers';
import { Teacher } from '../../types';
import { EmptyState, LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';

export const TeacherProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [teacher, setTeacher] = useState<Teacher | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTeacher = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await teachersService.getTeacher(Number(id));
      setTeacher(data);
    } catch (err) {
      console.error('Failed to load teacher profile', err);
      setError('Unable to load teacher profile.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeacher();
  }, [id]);

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <div className="flex items-center gap-2.5">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-xl text-slate-600 hover:bg-slate-100 active:scale-95 transition-all"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-900">Faculty Profile</h1>
          <p className="text-xs text-slate-500">Teacher credentials & school assignments</p>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={fetchTeacher} />}

      {loading ? (
        <LoadingSkeleton type="card" count={2} />
      ) : !teacher ? (
        <EmptyState
          title="Teacher Profile Not Found"
          description="The requested faculty record could not be retrieved."
          icon={<User className="w-10 h-10 text-slate-300" />}
          action={{
            label: 'Back to Faculty List',
            onClick: () => navigate('/principal/teachers'),
          }}
        />
      ) : (
        <div className="space-y-4">
          {/* Header Card */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="h-20 bg-gradient-to-r from-emerald-600 to-teal-600" />
            <div className="px-5 pb-5">
              <div className="flex items-end justify-between gap-3 -mt-8 mb-3">
                <div className="w-16 h-16 rounded-2xl bg-white border-4 border-white shadow-md flex items-center justify-center font-bold text-lg text-emerald-700 bg-emerald-50 flex-shrink-0">
                  {(teacher.display_name || teacher.full_name || 'TC').slice(0, 2).toUpperCase()}
                </div>
                <div className="flex items-center gap-2 mb-1">
                  {teacher.role_type && (
                    <span className="px-2.5 py-1 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold rounded-full">
                      {teacher.role_type}
                    </span>
                  )}
                  <StatusBadge status={teacher.status || (teacher.is_active ? 'ACTIVE' : 'INACTIVE')} />
                </div>
              </div>

              <h2 className="text-lg font-bold text-slate-900 leading-tight">
                {teacher.display_name || teacher.full_name || 'Faculty Member'}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {teacher.employee_id ? `Employee ID: ${teacher.employee_id}` : 'Employee ID: Pending'}
              </p>
            </div>
          </div>

          {/* Basic Information */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Basic Information</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 flex-shrink-0">
                  <User className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-[11px] text-slate-500">Full Name</p>
                  <p className="font-semibold text-slate-900">{teacher.display_name || teacher.full_name || '-'}</p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 flex-shrink-0">
                  <Phone className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-[11px] text-slate-500">Mobile Number</p>
                  <p className="font-semibold text-slate-900">{teacher.mobile || '-'}</p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 flex-shrink-0">
                  <Mail className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-[11px] text-slate-500">Email</p>
                  <p className="font-semibold text-slate-900">{teacher.email || '-'}</p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 flex-shrink-0">
                  <Award className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-[11px] text-slate-500">Employee ID</p>
                  <p className="font-semibold text-slate-900">{teacher.employee_id || '-'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Professional Information */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Professional Details</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 flex-shrink-0">
                  <Briefcase className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-[11px] text-slate-500">Qualification</p>
                  <p className="font-semibold text-slate-900">{teacher.qualification || '-'}</p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 flex-shrink-0">
                  <BookOpen className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-[11px] text-slate-500">Specialization / Department</p>
                  <p className="font-semibold text-slate-900">
                    {teacher.specialization || teacher.department || '-'}
                  </p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3 col-span-1 sm:col-span-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 flex-shrink-0">
                  <Calendar className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-[11px] text-slate-500">Joining Date</p>
                  <p className="font-semibold text-slate-900">{teacher.joining_date || '-'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Assigned Subjects / Sections */}
          {((teacher.assigned_subjects && teacher.assigned_subjects.length > 0) ||
            (teacher.assigned_sections && teacher.assigned_sections.length > 0)) && (
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Assignments</h3>
              <div className="space-y-2">
                {teacher.assigned_subjects && teacher.assigned_subjects.length > 0 && (
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Subjects</span>
                    <div className="flex flex-wrap gap-1.5">
                      {teacher.assigned_subjects.map((sub, i) => (
                        <span key={i} className="px-2.5 py-1 bg-emerald-50 text-emerald-700 text-xs rounded-lg font-medium">
                          {sub}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {teacher.assigned_sections && teacher.assigned_sections.length > 0 && (
                  <div className="pt-2">
                    <span className="text-[11px] text-slate-500 block mb-1">Classes / Sections</span>
                    <div className="flex flex-wrap gap-1.5">
                      {teacher.assigned_sections.map((sec, i) => (
                        <span key={i} className="px-2.5 py-1 bg-teal-50 text-teal-700 text-xs rounded-lg font-medium">
                          {sec}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TeacherProfile;
