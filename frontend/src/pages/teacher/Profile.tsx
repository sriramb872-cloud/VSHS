// src/pages/teacher/Profile.tsx
import React, { useEffect, useState } from 'react';
import {
  UserCircle,
  Phone,
  Shield,
  Mail,
  School,
  User as UserIcon,
  BookOpen,
  Briefcase,
  GraduationCap,
  Calendar,
  Layers,
  Edit3,
  CheckCircle,
  AlertCircle,
  Save,
  X,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { teachersService } from '../../services/teachers';
import { LoadingSkeleton } from '../../components/shared';
import { Teacher } from '../../types';

export const TeacherProfile: React.FC = () => {
  const { user: authUser } = useAuth();
  const [profileData, setProfileData] = useState<Teacher | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    display_name: '',
    email: '',
    mobile: '',
    qualification: '',
    department: '',
  });

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await teachersService.getMyTeacherProfile();
      setProfileData(data);
      setFormData({
        display_name: data.display_name || data.full_name || '',
        email: data.email || '',
        mobile: data.mobile || '',
        qualification: data.qualification || '',
        department: data.department || '',
      });
    } catch (err) {
      console.error('Failed to load teacher profile, fallback to auth data', err);
      if (authUser) {
        setProfileData({
          id: authUser.id,
          school_id: authUser.school_id || 1,
          user_id: authUser.id,
          display_name: authUser.display_name,
          email: authUser.email,
          mobile: authUser.mobile,
          is_active: typeof authUser.is_active === 'boolean' ? authUser.is_active : authUser.is_active === 'ACTIVE',
        });
        setFormData({
          display_name: authUser.display_name || '',
          email: authUser.email || '',
          mobile: authUser.mobile || '',
          qualification: '',
          department: '',
        });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.display_name.trim()) {
      setFeedback({ type: 'error', message: 'Full name cannot be empty.' });
      return;
    }
    if (!formData.mobile.trim()) {
      setFeedback({ type: 'error', message: 'Mobile phone cannot be empty.' });
      return;
    }

    try {
      setSaving(true);
      setFeedback(null);
      const updated = await teachersService.updateMyTeacherProfile({
        display_name: formData.display_name.trim(),
        full_name: formData.display_name.trim(),
        email: formData.email.trim() || undefined,
        mobile: formData.mobile.trim(),
        qualification: formData.qualification.trim() || undefined,
        department: formData.department.trim() || undefined,
      });
      setProfileData(updated);
      setFeedback({ type: 'success', message: 'Teacher profile updated successfully!' });
      setIsEditing(false);
    } catch (err: any) {
      console.error('Failed to update teacher profile', err);
      setFeedback({
        type: 'error',
        message: err?.response?.data?.detail || 'Failed to update profile. Please verify your inputs.',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (profileData) {
      setFormData({
        display_name: profileData.display_name || profileData.full_name || '',
        email: profileData.email || '',
        mobile: profileData.mobile || '',
        qualification: profileData.qualification || '',
        department: profileData.department || '',
      });
    }
    setIsEditing(false);
    setFeedback(null);
  };

  return (
    <div className="space-y-4 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Teacher Profile</h1>
          <p className="text-xs text-slate-500">Manage your faculty credentials, contact info, and qualifications</p>
        </div>
        {!isEditing && (
          <button
            onClick={() => {
              setIsEditing(true);
              setFeedback(null);
            }}
            className="h-10 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
          >
            <Edit3 className="w-4 h-4" />
            Edit Profile
          </button>
        )}
      </div>

      {/* Feedback banner */}
      {feedback && (
        <div
          className={`p-4 rounded-2xl border text-xs font-medium flex items-center gap-2.5 ${
            feedback.type === 'success'
              ? 'bg-blue-50 border-blue-200 text-blue-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle className="w-4 h-4 text-blue-600 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          )}
          <span>{feedback.message}</span>
        </div>
      )}

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : !profileData ? (
        <div className="p-8 bg-white rounded-3xl border border-slate-200 shadow-xs text-center text-slate-500 text-sm">
          Profile information unavailable.
        </div>
      ) : (
        <div className="space-y-4">
          {/* Hero Profile Header */}
          <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="h-28 bg-gradient-to-r from-blue-600 via-sky-600 to-indigo-700" />
            <div className="px-6 pb-6">
              <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 -mt-10 mb-2">
                <div className="flex items-end gap-3.5">
                  <div className="w-20 h-20 rounded-2xl bg-white border-4 border-white shadow-md flex items-center justify-center flex-shrink-0">
                    <UserCircle className="w-12 h-12 text-blue-600" />
                  </div>
                  <div className="mb-1">
                    <h2 className="text-lg font-bold text-slate-900">
                      {profileData.display_name || profileData.full_name || 'Faculty Member'}
                    </h2>
                    <p className="text-xs text-slate-500 font-medium">
                      {profileData.department ? `${profileData.department} Dept • ` : ''}
                      {profileData.school_name || `School #${profileData.school_id || 'N/A'}`}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {profileData.employee_id && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                      ID: {profileData.employee_id}
                    </span>
                  )}
                  {profileData.role_type && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">
                      {profileData.role_type}
                    </span>
                  )}
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
                    TEACHER
                  </span>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                    {profileData.status || (profileData.is_active ? 'Active' : 'Inactive')}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Edit Form or View Information */}
          {isEditing ? (
            <div className="bg-white rounded-3xl border border-blue-200 shadow-xs p-6 space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Edit Teacher Profile Information
                </h3>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
                  aria-label="Cancel editing"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSave} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Full Name */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.display_name}
                      onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                      placeholder="e.g. John Doe"
                      className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  {/* Phone Number */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Phone Number *
                    </label>
                    <input
                      type="tel"
                      required
                      value={formData.mobile}
                      onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                      placeholder="Mobile Phone"
                      className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  {/* Email */}
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Email Address
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="teacher@school.edu"
                      className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  {/* Qualification */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Qualification / Degrees
                    </label>
                    <input
                      type="text"
                      value={formData.qualification}
                      onChange={(e) => setFormData({ ...formData, qualification: e.target.value })}
                      placeholder="e.g. M.Sc. Mathematics, B.Ed."
                      className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>

                  {/* Department */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Department
                    </label>
                    <input
                      type="text"
                      value={formData.department}
                      onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                      placeholder="e.g. Science, Mathematics, English"
                      className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="flex gap-2.5 pt-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex-1 h-11 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
                  >
                    <Save className="w-4 h-4" />
                    {saving ? 'Saving Changes...' : 'Save Profile'}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="px-6 h-11 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold active:scale-95 transition-all"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Personal & Contact Info */}
              <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-5 space-y-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Personal & Contact Info</h3>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <UserIcon className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Full Name</p>
                    <p className="text-sm font-bold text-slate-900 truncate">
                      {profileData.display_name || profileData.full_name || 'Not provided'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <Phone className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Mobile Phone</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">{profileData.mobile}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <Mail className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Email Address</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.email || 'No email registered'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <School className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Institution</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.school_name || `School #${profileData.school_id || 'N/A'}`}
                    </p>
                  </div>
                </div>
              </div>

              {/* Faculty & Academic Qualifications */}
              <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-5 space-y-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Faculty Details</h3>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <Briefcase className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Employee ID</p>
                    <p className="text-sm font-bold text-slate-900 truncate">
                      {profileData.employee_id || 'Not assigned'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <GraduationCap className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Qualification</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.qualification || 'Not specified'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <Layers className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Department</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.department || 'General'}
                    </p>
                  </div>
                </div>

                {profileData.joining_date && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                      <Calendar className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs text-slate-500">Joining Date</p>
                      <p className="text-sm font-semibold text-slate-900">{profileData.joining_date}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Teaching Assignments */}
              {(profileData.assigned_subjects?.length || profileData.assigned_sections?.length) ? (
                <div className="md:col-span-2 bg-white rounded-3xl border border-slate-200/80 shadow-xs p-5 space-y-3">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Assigned Subjects & Sections
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {profileData.assigned_subjects?.map((sub, i) => (
                      <span
                        key={`sub-${i}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200"
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        {sub}
                      </span>
                    ))}
                    {profileData.assigned_sections?.map((sec, i) => (
                      <span
                        key={`sec-${i}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200"
                      >
                        <Layers className="w-3.5 h-3.5" />
                        {sec}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TeacherProfile;