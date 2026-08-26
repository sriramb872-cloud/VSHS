// src/pages/student/Profile.tsx
import React, { useEffect, useState } from 'react';
import {
  UserCircle,
  Phone,
  Shield,
  School,
  User as UserIcon,
  Mail,
  Home,
  Users,
  GraduationCap,
  Calendar,
  Percent,
  Edit3,
  CheckCircle,
  AlertCircle,
  Save,
  X,
  Lock,
  Heart,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { studentsService } from '../../services/students';
import { LoadingSkeleton } from '../../components/shared';
import { Student } from '../../types';

export const StudentProfile: React.FC = () => {
  const { user: authUser } = useAuth();
  const [profileData, setProfileData] = useState<Student | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Form State for permitted fields
  const [formData, setFormData] = useState({
    display_name: '',
    email: '',
    date_of_birth: '',
    gender: '',
    blood_group: '',
    address: '',
    father_name: '',
    father_mobile: '',
    mother_name: '',
    mother_mobile: '',
    guardian_mobile: '',
  });

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await studentsService.getMyStudentProfile();
      setProfileData(data);
      setFormData({
        display_name: data.display_name || data.full_name || '',
        email: data.email || '',
        date_of_birth: data.date_of_birth ? String(data.date_of_birth).slice(0, 10) : '',
        gender: data.gender || '',
        blood_group: data.blood_group || '',
        address: data.address || '',
        father_name: data.father_name || '',
        father_mobile: data.father_mobile || '',
        mother_name: data.mother_name || '',
        mother_mobile: data.mother_mobile || '',
        guardian_mobile: data.guardian_mobile || '',
      });
    } catch (err) {
      console.error('Failed to load student profile, fallback to auth data', err);
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
          date_of_birth: '',
          gender: '',
          blood_group: '',
          address: '',
          father_name: '',
          father_mobile: '',
          mother_name: '',
          mother_mobile: '',
          guardian_mobile: '',
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
      setFeedback({ type: 'error', message: 'Student full name cannot be empty.' });
      return;
    }

    try {
      setSaving(true);
      setFeedback(null);
      const updated = await studentsService.updateMyStudentProfile({
        display_name: formData.display_name.trim(),
        full_name: formData.display_name.trim(),
        email: formData.email.trim() || undefined,
        date_of_birth: formData.date_of_birth || undefined,
        gender: formData.gender || undefined,
        blood_group: formData.blood_group || undefined,
        address: formData.address.trim() || undefined,
        father_name: formData.father_name.trim() || undefined,
        father_mobile: formData.father_mobile.trim() || undefined,
        mother_name: formData.mother_name.trim() || undefined,
        mother_mobile: formData.mother_mobile.trim() || undefined,
        guardian_mobile: formData.guardian_mobile.trim() || undefined,
      });
      setProfileData(updated);
      setFeedback({ type: 'success', message: 'Student profile updated successfully!' });
      setIsEditing(false);
    } catch (err: any) {
      console.error('Failed to update student profile', err);
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
        date_of_birth: profileData.date_of_birth ? String(profileData.date_of_birth).slice(0, 10) : '',
        gender: profileData.gender || '',
        blood_group: profileData.blood_group || '',
        address: profileData.address || '',
        father_name: profileData.father_name || '',
        father_mobile: profileData.father_mobile || '',
        mother_name: profileData.mother_name || '',
        mother_mobile: profileData.mother_mobile || '',
        guardian_mobile: profileData.guardian_mobile || '',
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
          <h1 className="text-xl font-bold text-slate-900">Student Profile</h1>
          <p className="text-xs text-slate-500">Personal details, academic enrollment, and contact records</p>
        </div>
        {!isEditing && (
          <button
            onClick={() => {
              setIsEditing(true);
              setFeedback(null);
            }}
            className="h-10 px-4 rounded-xl bg-orange-600 hover:bg-orange-700 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
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
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
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
          {/* Profile Hero Header Card */}
          <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="h-28 bg-gradient-to-r from-orange-500 via-amber-500 to-red-500" />
            <div className="px-6 pb-6">
              <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 -mt-10 mb-2">
                <div className="flex items-end gap-3.5">
                  <div className="w-20 h-20 rounded-2xl bg-white border-4 border-white shadow-md flex items-center justify-center flex-shrink-0">
                    <UserCircle className="w-12 h-12 text-orange-600" />
                  </div>
                  <div className="mb-1">
                    <h2 className="text-lg font-bold text-slate-900">
                      {profileData.display_name || profileData.full_name || 'Student'}
                    </h2>
                    <p className="text-xs text-slate-500 font-medium">
                      {profileData.grade_name ? `Grade ${profileData.grade_name}` : ''}
                      {profileData.section_name ? ` - Sec ${profileData.section_name} • ` : ' • '}
                      {profileData.school_name || `School #${profileData.school_id || 'N/A'}`}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {profileData.admission_number && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-orange-50 text-orange-800 border border-orange-200">
                      ID: {profileData.admission_number}
                    </span>
                  )}
                  {profileData.roll_number && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                      Roll: {profileData.roll_number}
                    </span>
                  )}
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-700">
                    STUDENT
                  </span>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {profileData.status || (profileData.is_active ? 'Active' : 'Inactive')}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Academic Records (Strictly Read-Only with Lock Indicators) */}
          <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div className="flex items-center gap-2">
                <GraduationCap className="w-4 h-4 text-orange-600" />
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Academic & Enrollment Information
                </h3>
              </div>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-md">
                <Lock className="w-3 h-3 text-slate-400" />
                Administrative Only
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
              <div className="bg-slate-50 rounded-2xl p-3 border border-slate-100">
                <p className="text-[11px] text-slate-500 font-medium">Grade & Section</p>
                <p className="text-sm font-bold text-slate-900 mt-0.5">
                  {profileData.grade_name ? `${profileData.grade_name}` : 'N/A'}{' '}
                  {profileData.section_name ? `(${profileData.section_name})` : ''}
                </p>
              </div>

              <div className="bg-slate-50 rounded-2xl p-3 border border-slate-100">
                <p className="text-[11px] text-slate-500 font-medium">Roll Number</p>
                <p className="text-sm font-bold text-slate-900 mt-0.5">
                  {profileData.roll_number || 'N/A'}
                </p>
              </div>

              <div className="bg-slate-50 rounded-2xl p-3 border border-slate-100">
                <p className="text-[11px] text-slate-500 font-medium">Admission No</p>
                <p className="text-sm font-bold text-slate-900 mt-0.5">
                  {profileData.admission_number || 'N/A'}
                </p>
              </div>

              <div className="bg-slate-50 rounded-2xl p-3 border border-slate-100">
                <p className="text-[11px] text-slate-500 font-medium">Attendance Rate</p>
                <p className="text-sm font-bold text-emerald-600 mt-0.5 flex items-center gap-1">
                  <Percent className="w-3.5 h-3.5" />
                  {profileData.attendance_percentage !== undefined && profileData.attendance_percentage !== null
                    ? `${profileData.attendance_percentage}%`
                    : 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Edit Form or View Information */}
          {isEditing ? (
            <div className="bg-white rounded-3xl border border-orange-200 shadow-xs p-6 space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Edit Personal & Contact Information
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
                {/* Personal Section */}
                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5">
                    Personal Details
                  </h4>
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
                        placeholder="Student Full Name"
                        className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>

                    {/* Email */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Email Address
                      </label>
                      <input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        placeholder="student@school.edu"
                        className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>

                    {/* DOB */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Date of Birth
                      </label>
                      <input
                        type="date"
                        value={formData.date_of_birth}
                        onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                        className="w-full h-11 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>

                    {/* Gender */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Gender
                      </label>
                      <select
                        value={formData.gender}
                        onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                        className="w-full h-11 px-3 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none bg-white"
                      >
                        <option value="">Select Gender</option>
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>

                    {/* Blood Group */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Blood Group
                      </label>
                      <input
                        type="text"
                        value={formData.blood_group}
                        onChange={(e) => setFormData({ ...formData, blood_group: e.target.value })}
                        placeholder="e.g. O+, A+, B+, AB-"
                        className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>

                    {/* Residential Address */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Residential Address
                      </label>
                      <input
                        type="text"
                        value={formData.address}
                        onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                        placeholder="Complete residential address"
                        className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>
                  </div>
                </div>

                {/* Parent / Guardian Section */}
                <div className="pt-2 border-t border-slate-100">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5">
                    Parent / Guardian Contact Info
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Father Name */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Father's Name
                      </label>
                      <input
                        type="text"
                        value={formData.father_name}
                        onChange={(e) => setFormData({ ...formData, father_name: e.target.value })}
                        placeholder="Father's Full Name"
                        className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>

                    {/* Father Mobile */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Father's Mobile
                      </label>
                      <input
                        type="tel"
                        value={formData.father_mobile}
                        onChange={(e) => setFormData({ ...formData, father_mobile: e.target.value })}
                        placeholder="Father's Phone"
                        className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>

                    {/* Mother Name */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Mother's Name
                      </label>
                      <input
                        type="text"
                        value={formData.mother_name}
                        onChange={(e) => setFormData({ ...formData, mother_name: e.target.value })}
                        placeholder="Mother's Full Name"
                        className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>

                    {/* Mother Mobile */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Mother's Mobile
                      </label>
                      <input
                        type="tel"
                        value={formData.mother_mobile}
                        onChange={(e) => setFormData({ ...formData, mother_mobile: e.target.value })}
                        placeholder="Mother's Phone"
                        className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>

                    {/* Guardian Mobile */}
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                        Guardian's Mobile (Optional)
                      </label>
                      <input
                        type="tel"
                        value={formData.guardian_mobile}
                        onChange={(e) => setFormData({ ...formData, guardian_mobile: e.target.value })}
                        placeholder="Emergency / Guardian Phone"
                        className="w-full h-11 px-4 rounded-xl border border-slate-300 text-slate-900 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex gap-2.5 pt-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex-1 h-11 rounded-xl bg-orange-600 hover:bg-orange-700 text-white text-xs font-bold active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
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
              {/* Personal & Basic Info */}
              <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-5 space-y-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Personal Information
                </h3>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                    <UserIcon className="w-5 h-5 text-orange-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Student Full Name</p>
                    <p className="text-sm font-bold text-slate-900 truncate">
                      {profileData.display_name || profileData.full_name || 'Not provided'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                    <Calendar className="w-5 h-5 text-orange-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Date of Birth / Age</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.date_of_birth ? String(profileData.date_of_birth).slice(0, 10) : 'Not specified'}
                      {profileData.age ? ` (${profileData.age} yrs)` : ''}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                    <Heart className="w-5 h-5 text-orange-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Gender & Blood Group</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.gender || 'Gender N/A'} • {profileData.blood_group || 'Blood Group N/A'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                    <Mail className="w-5 h-5 text-orange-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Email Address</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.email || 'No email registered'}
                    </p>
                  </div>
                </div>

                {profileData.address && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                      <Home className="w-5 h-5 text-orange-600" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs text-slate-500">Residential Address</p>
                      <p className="text-sm font-semibold text-slate-900 truncate">
                        {profileData.address}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Parents & Emergency Contact Info */}
              <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-5 space-y-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Parent / Guardian Details
                </h3>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                    <Users className="w-5 h-5 text-orange-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Father's Name & Phone</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.father_name || 'Not provided'}
                    </p>
                    {profileData.father_mobile && (
                      <p className="text-xs text-slate-500">{profileData.father_mobile}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                    <Users className="w-5 h-5 text-orange-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Mother's Name & Phone</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.mother_name || 'Not provided'}
                    </p>
                    {profileData.mother_mobile && (
                      <p className="text-xs text-slate-500">{profileData.mother_mobile}</p>
                    )}
                  </div>
                </div>

                {profileData.guardian_mobile && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                      <Phone className="w-5 h-5 text-orange-600" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs text-slate-500">Guardian / Emergency Mobile</p>
                      <p className="text-sm font-semibold text-slate-900">{profileData.guardian_mobile}</p>
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center flex-shrink-0">
                    <School className="w-5 h-5 text-orange-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">Enrolled Institution</p>
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {profileData.school_name || `School #${profileData.school_id || 'N/A'}`}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StudentProfile;