// src/pages/principal/StudentProfile.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  User,
  Phone,
  Mail,
  GraduationCap,
  Calendar,
  Heart,
  MapPin,
  Users,
  Award,
  CheckCircle,
  Percent,
  Layers,
  BookOpen,
  Clock,
  FileText,
} from 'lucide-react';
import { studentsService } from '../../services/students';
import { marksService } from '../../services/marks';
import { reportCardService } from '../../services/reportcard';
import { attendanceService } from '../../services/attendance';
import { Student, Mark, ReportCard } from '../../types';
import { EmptyState, LoadingSkeleton, StatusBadge, ErrorState } from '../../components/shared';

export const StudentProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [student, setStudent] = useState<Student | null>(null);
  const [marks, setMarks] = useState<Mark[]>([]);
  const [reportCards, setReportCards] = useState<ReportCard[]>([]);
  const [attendanceSummary, setAttendanceSummary] = useState<any | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadStudentData = async () => {
    if (!id) return;
    const studentId = Number(id);
    try {
      setLoading(true);
      setError(null);

      const [studentData, marksData, reportCardsData, attendanceData] = await Promise.allSettled([
        studentsService.getStudent(studentId),
        marksService.listMarks({ student_id: studentId, limit: 10 }),
        reportCardService.listReportCards({ student_id: studentId, limit: 5 }),
        attendanceService.getStudentAttendanceSummary(studentId),
      ]);

      if (studentData.status === 'fulfilled') {
        setStudent(studentData.value);
      } else {
        throw new Error('Student profile not found');
      }

      if (marksData.status === 'fulfilled') {
        setMarks(marksData.value.items || []);
      }
      if (reportCardsData.status === 'fulfilled') {
        setReportCards(reportCardsData.value.items || []);
      }
      if (attendanceData.status === 'fulfilled') {
        setAttendanceSummary(attendanceData.value);
      }
    } catch (err) {
      console.error('Failed to load student profile', err);
      setError('Unable to load student record.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStudentData();
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-4 max-w-3xl mx-auto">
        <LoadingSkeleton type="card" count={3} />
      </div>
    );
  }

  if (error || !student) {
    return (
      <div className="space-y-4 max-w-3xl mx-auto">
        <ErrorState
          title="Student Record Error"
          message={error || 'Unable to locate student record.'}
          onRetry={loadStudentData}
        />
      </div>
    );
  }

  const latestReportCard = reportCards.length > 0 ? reportCards[0] : null;

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      {/* Back Button & Title */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-xl text-slate-600 hover:bg-slate-100 active:scale-95 transition-all"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-900">Student Record</h1>
          <p className="text-xs text-slate-500">Comprehensive student profile & performance</p>
        </div>
      </div>

      {/* 1. STUDENT OVERVIEW CARD */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="h-20 bg-gradient-to-r from-teal-700 via-emerald-700 to-teal-800" />
        <div className="px-5 pb-5">
          <div className="flex items-end justify-between gap-3 -mt-8 mb-3">
            <div className="w-16 h-16 rounded-2xl bg-white border-4 border-white shadow-md flex items-center justify-center font-bold text-lg text-teal-800 bg-teal-50 flex-shrink-0">
              {(student.display_name || student.full_name || 'ST').slice(0, 2).toUpperCase()}
            </div>
            <div className="mb-1">
              <StatusBadge status={student.is_active ? 'ACTIVE' : 'INACTIVE'} />
            </div>
          </div>

          <div className="space-y-1">
            <h2 className="text-lg font-bold text-slate-900 leading-tight">
              {student.display_name || student.full_name || 'Student Name'}
            </h2>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
              <span>Adm No: <strong className="text-slate-800 font-semibold">{student.admission_number || '-'}</strong></span>
              {student.roll_number && (
                <>
                  <span>•</span>
                  <span>Roll No: <strong className="text-slate-800 font-semibold">{student.roll_number}</strong></span>
                </>
              )}
              <span>•</span>
              <span>
                Class:{' '}
                <strong className="text-teal-700 font-semibold">
                  {student.grade_name || '-'} {student.section_name ? `(${student.section_name})` : ''}
                </strong>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. PERSONAL INFORMATION */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <User className="w-3.5 h-3.5 text-slate-400" />
          <span>Personal Information</span>
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Date of Birth</span>
            <span className="font-semibold text-slate-900">{student.date_of_birth || '-'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Age</span>
            <span className="font-semibold text-slate-900">{student.age !== null && student.age !== undefined ? `${student.age} yrs` : '-'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Gender</span>
            <span className="font-semibold text-slate-900">{student.gender || '-'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Blood Group</span>
            <span className="font-semibold text-slate-900">{student.blood_group || '-'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Mobile</span>
            <span className="font-semibold text-slate-900">{student.mobile || '-'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Email</span>
            <span className="font-semibold text-slate-900 truncate block">{student.email || '-'}</span>
          </div>
          {student.address && (
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 col-span-2 sm:col-span-3">
              <span className="text-[11px] text-slate-500 block">Address</span>
              <span className="font-semibold text-slate-900">{student.address}</span>
            </div>
          )}
        </div>
      </div>

      {/* 3. PARENT / GUARDIAN INFORMATION */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5 text-slate-400" />
          <span>Parent & Guardian Information</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {/* Father Details */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
            <span className="text-[11px] text-slate-400 block font-medium">Father's Details</span>
            <p className="font-bold text-slate-900 text-sm">{student.father_name || 'Not available'}</p>
            <p className="text-slate-600 flex items-center gap-1 mt-1">
              <Phone className="w-3 h-3 text-slate-400" />
              <span>{student.father_mobile || 'No Mobile'}</span>
            </p>
          </div>

          {/* Mother Details */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
            <span className="text-[11px] text-slate-400 block font-medium">Mother's Details</span>
            <p className="font-bold text-slate-900 text-sm">{student.mother_name || 'Not available'}</p>
            <p className="text-slate-600 flex items-center gap-1 mt-1">
              <Phone className="w-3 h-3 text-slate-400" />
              <span>{student.mother_mobile || 'No Mobile'}</span>
            </p>
          </div>

          {/* Guardian Mobile */}
          {student.guardian_mobile && (
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 sm:col-span-2 space-y-1">
              <span className="text-[11px] text-slate-400 block font-medium">Guardian Emergency Mobile</span>
              <p className="text-slate-900 font-semibold flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-slate-400" />
                <span>{student.guardian_mobile}</span>
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 4. REPORT CARD */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-slate-400" />
            <span>Report Card</span>
          </h3>
          {latestReportCard && (
            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full">
              {latestReportCard.grade ? `Grade: ${latestReportCard.grade}` : ''}
              {latestReportCard.percentage !== undefined && latestReportCard.percentage !== null
                ? ` (${latestReportCard.percentage}%)`
                : ''}
            </span>
          )}
        </div>

        {!latestReportCard ? (
          <EmptyState
            title="No report card data available."
            description="Report card records have not been published for this student yet."
            icon={<FileText className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs text-center">
              {latestReportCard.percentage !== undefined && latestReportCard.percentage !== null && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-800">
                  <span className="text-[11px] block text-emerald-600">Percentage</span>
                  <span className="text-lg font-black">{latestReportCard.percentage}%</span>
                </div>
              )}
              {latestReportCard.obtained_marks !== undefined && latestReportCard.obtained_marks !== null && (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-slate-800">
                  <span className="text-[11px] block text-slate-500">Marks</span>
                  <span className="text-lg font-bold text-slate-900">
                    {latestReportCard.obtained_marks}
                    {latestReportCard.total_marks ? ` / ${latestReportCard.total_marks}` : ''}
                  </span>
                </div>
              )}
              {latestReportCard.grade && (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-slate-800">
                  <span className="text-[11px] block text-slate-500">Grade</span>
                  <span className="text-lg font-bold text-emerald-700">{latestReportCard.grade}</span>
                </div>
              )}
              {latestReportCard.rank !== undefined && latestReportCard.rank !== null && (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-slate-800">
                  <span className="text-[11px] block text-slate-500">Rank</span>
                  <span className="text-lg font-bold text-slate-900">#{latestReportCard.rank}</span>
                </div>
              )}
            </div>

            {latestReportCard.subjects && latestReportCard.subjects.length > 0 && (
              <div className="overflow-hidden rounded-xl border border-slate-200/70">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200/70">
                    <tr>
                      <th className="p-2.5">Subject</th>
                      <th className="p-2.5 text-center">Marks</th>
                      <th className="p-2.5 text-center">Max</th>
                      <th className="p-2.5 text-right">Grade</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {latestReportCard.subjects.map((sub, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="p-2.5 font-medium text-slate-900">{sub.subject_name || `Subject #${sub.subject_id}`}</td>
                        <td className="p-2.5 text-center font-bold text-emerald-700">{sub.marks_obtained ?? '-'}</td>
                        <td className="p-2.5 text-center text-slate-500">{sub.max_marks ?? 100}</td>
                        <td className="p-2.5 text-right font-semibold text-slate-800">{sub.grade || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {latestReportCard.teacher_remarks && (
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                <span className="text-[11px] font-bold text-slate-400 block uppercase tracking-wider mb-0.5">Teacher Remarks</span>
                <p className="text-slate-700">{latestReportCard.teacher_remarks}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 5. ATTENDANCE SUMMARY */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <CheckCircle className="w-3.5 h-3.5 text-slate-400" />
          <span>Attendance Record</span>
        </h3>

        {!attendanceSummary || attendanceSummary.total_days === 0 ? (
          <EmptyState
            title="No attendance data available."
            description="Attendance logs for this student have not been recorded yet."
            icon={<CheckCircle className="w-10 h-10 text-slate-300" />}
          />
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs text-center">
              <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-800">
                <span className="text-[11px] block text-emerald-600">Percentage</span>
                <span className="text-lg font-black">{attendanceSummary.percentage}%</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-slate-800">
                <span className="text-[11px] block text-slate-500">Present</span>
                <span className="text-lg font-bold text-emerald-700">{attendanceSummary.present_days}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-slate-800">
                <span className="text-[11px] block text-slate-500">Absent</span>
                <span className="text-lg font-bold text-rose-600">{attendanceSummary.absent_days}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-slate-800">
                <span className="text-[11px] block text-slate-500">Total Days</span>
                <span className="text-lg font-bold text-slate-900">{attendanceSummary.total_days}</span>
              </div>
            </div>

            {attendanceSummary.records && attendanceSummary.records.length > 0 && (
              <div>
                <span className="text-[11px] font-bold text-slate-500 block mb-1.5 uppercase tracking-wider">
                  Recent Attendance Logs
                </span>
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {attendanceSummary.records.slice(0, 10).map((r: any) => (
                    <div
                      key={r.id}
                      className="p-2.5 rounded-xl bg-slate-50/70 border border-slate-100 flex items-center justify-between text-xs"
                    >
                      <span className="text-slate-700 font-medium">{r.date}</span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                          r.status === 'PRESENT'
                            ? 'bg-emerald-100 text-emerald-800'
                            : r.status === 'ABSENT'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {r.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 6. ENROLLMENT DETAILS */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-slate-400" />
          <span>Enrollment Placement</span>
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Academic Year</span>
            <span className="font-semibold text-slate-900">{student.academic_year_name || 'Current'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Class / Grade</span>
            <span className="font-semibold text-slate-900">{student.grade_name || '-'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Section</span>
            <span className="font-semibold text-slate-900">{student.section_name || 'Direct'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[11px] text-slate-500 block">Roll Number</span>
            <span className="font-semibold text-slate-900">{student.roll_number || '-'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 col-span-2 sm:col-span-2">
            <span className="text-[11px] text-slate-500 block">Enrollment Date</span>
            <span className="font-semibold text-slate-900">{student.enrollment_date || '-'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentProfile;