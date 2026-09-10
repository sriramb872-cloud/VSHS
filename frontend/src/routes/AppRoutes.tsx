import React, { Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import AuthLayout from "../layouts/AuthLayout";
import AdminLayout from "../layouts/AdminLayout";
import PrincipalLayout from "../layouts/PrincipalLayout";
import TeacherLayout from "../layouts/TeacherLayout";
import StudentLayout from "../layouts/StudentLayout";

import { ProtectedRoute } from "./ProtectedRoute";
import { RoleRoute } from "./RoleRoute";
import { RoleBasedRedirect } from "./RoleBasedRedirect";

// Auth
const Login = React.lazy(() => import("../pages/auth/Login"));

// Common
const Unauthorized = React.lazy(() => import("../pages/common/Unauthorized"));
const NotFound = React.lazy(() => import("../pages/common/NotFound"));

// Super Admin Pages
const AdminDashboard = React.lazy(() => import("../pages/superadmin/Dashboard"));
const AdminSchools = React.lazy(() => import("../pages/superadmin/Schools"));
const AdminCreateSchool = React.lazy(() => import("../pages/superadmin/CreateSchool"));
const AdminEditSchool = React.lazy(() => import("../pages/superadmin/EditSchool"));
const AdminSchoolDetails = React.lazy(() => import("../pages/superadmin/SchoolDetails"));
const AdminUsers = React.lazy(() => import("../pages/superadmin/Users"));
const AdminPrincipals = React.lazy(() => import("../pages/superadmin/Principals"));
const AdminRoles = React.lazy(() => import("../pages/superadmin/Roles"));
const AdminPermissions = React.lazy(() => import("../pages/superadmin/Permissions"));
const AdminAnalytics = React.lazy(() => import("../pages/superadmin/Analytics"));
const AdminReports = React.lazy(() => import("../pages/superadmin/Reports"));
const AdminSubscriptions = React.lazy(() => import("../pages/superadmin/Subscriptions"));
const AdminSystemSettings = React.lazy(() => import("../pages/superadmin/SystemSettings"));
const AdminAuditLogs = React.lazy(() => import("../pages/superadmin/AuditLogs"));
const AdminNotifications = React.lazy(() => import("../pages/superadmin/Notifications"));
const AdminProfile = React.lazy(() => import("../pages/superadmin/Profile"));

// Principal Pages
const PrincipalDashboard = React.lazy(() => import("../pages/principal/Dashboard"));
const PrincipalStudents = React.lazy(() => import("../pages/principal/Students"));
const PrincipalStudentProfile = React.lazy(() => import("../pages/principal/StudentProfile"));
const PrincipalTeachers = React.lazy(() => import("../pages/principal/Teachers"));
const PrincipalTeacherProfile = React.lazy(() => import("../pages/principal/TeacherProfile"));
const PrincipalGrades = React.lazy(() => import("../pages/principal/Grades"));
const PrincipalSections = React.lazy(() => import("../pages/principal/Sections"));
const PrincipalSubjects = React.lazy(() => import("../pages/principal/Subjects"));
const PrincipalAcademicYears = React.lazy(() => import("../pages/principal/AcademicYears"));
const PrincipalTimetable = React.lazy(() => import("../pages/principal/Timetable"));
const PrincipalExams = React.lazy(() => import("../pages/principal/Exams"));
const PrincipalMarks = React.lazy(() => import("../pages/principal/Marks"));
const PrincipalReportCards = React.lazy(() => import("../pages/principal/ReportCards"));
const PrincipalHomework = React.lazy(() => import("../pages/principal/Homework"));
const PrincipalHomeworkDetails = React.lazy(() => import("../pages/principal/HomeworkDetails"));
const PrincipalAttendance = React.lazy(() => import("../pages/principal/Attendance"));
const PrincipalAttendanceReports = React.lazy(() => import("../pages/principal/AttendanceReports"));
const PrincipalAnnouncements = React.lazy(() => import("../pages/principal/Announcements"));
const PrincipalCalendar = React.lazy(() => import("../pages/principal/Calendar"));
const PrincipalNotifications = React.lazy(() => import("../pages/principal/Notifications"));
const PrincipalSettings = React.lazy(() => import("../pages/principal/Settings"));
const PrincipalProfile = React.lazy(() => import("../pages/principal/Profile"));
const PrincipalAnalytics = React.lazy(() => import("../pages/principal/Analytics"));
const PrincipalEnrollments = React.lazy(() => import("../pages/principal/Enrollments"));
const PrincipalTeachingAssignments = React.lazy(() => import("../pages/principal/TeachingAssignments"));

// Teacher Pages
const TeacherDashboard = React.lazy(() => import("../pages/teacher/Dashboard"));
const TeacherStudents = React.lazy(() => import("../pages/teacher/Students"));
const TeacherStudentProfile = React.lazy(() => import("../pages/teacher/StudentProfile"));
const TeacherTimetable = React.lazy(() => import("../pages/teacher/Timetable"));
const TeacherExams = React.lazy(() => import("../pages/teacher/Exams"));
const TeacherExamDetails = React.lazy(() => import("../pages/teacher/ExamDetails"));
const TeacherMarksEntry = React.lazy(() => import("../pages/teacher/MarksEntry"));
const TeacherHomework = React.lazy(() => import("../pages/teacher/Homework"));
const TeacherCreateHomework = React.lazy(() => import("../pages/teacher/CreateHomework"));
const TeacherEditHomework = React.lazy(() => import("../pages/teacher/EditHomework"));
const TeacherHomeworkDetails = React.lazy(() => import("../pages/teacher/HomeworkDetails"));
const TeacherAttendance = React.lazy(() => import("../pages/teacher/Attendance"));
const TeacherAttendanceHistory = React.lazy(() => import("../pages/teacher/AttendanceHistory"));
const TeacherAnnouncements = React.lazy(() => import("../pages/teacher/Announcements"));
const TeacherCalendar = React.lazy(() => import("../pages/teacher/Calendar"));
const TeacherReportCards = React.lazy(() => import("../pages/teacher/ReportCards"));
const TeacherNotifications = React.lazy(() => import("../pages/teacher/Notifications"));
const TeacherSettings = React.lazy(() => import("../pages/teacher/Settings"));
const TeacherProfile = React.lazy(() => import("../pages/teacher/Profile"));

// Student Pages
const StudentDashboard = React.lazy(() => import("../pages/student/Dashboard"));
const StudentTimetable = React.lazy(() => import("../pages/student/Timetable"));
const StudentExams = React.lazy(() => import("../pages/student/Exams"));
const StudentMarks = React.lazy(() => import("../pages/student/Marks"));
const StudentReportCards = React.lazy(() => import("../pages/student/ReportCards"));
const StudentHomework = React.lazy(() => import("../pages/student/Homework"));
const StudentHomeworkDetails = React.lazy(() => import("../pages/student/HomeworkDetails"));
const StudentAttendance = React.lazy(() => import("../pages/student/Attendance"));
const StudentAnnouncements = React.lazy(() => import("../pages/student/Announcements"));
const StudentCalendar = React.lazy(() => import("../pages/student/Calendar"));
const StudentNotifications = React.lazy(() => import("../pages/student/Notifications"));
const StudentSettings = React.lazy(() => import("../pages/student/Settings"));
const StudentProfile = React.lazy(() => import("../pages/student/Profile"));

const AppRoutes: React.FC = () => {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-3 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
      </div>
    }>
      <Routes>
      {/* ==================== AUTH ==================== */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
      </Route>

      {/* ==================== SUPER ADMIN ==================== */}
      <Route element={<ProtectedRoute />}>
        <Route element={<RoleRoute allowedRoles={["SUPER_ADMIN"]} />}>
          <Route element={<AdminLayout />}>
            <Route path="/superadmin" element={<Navigate to="/superadmin/dashboard" replace />} />
            <Route path="/superadmin/dashboard" element={<AdminDashboard />} />
            <Route path="/superadmin/schools" element={<AdminSchools />} />
            <Route path="/superadmin/schools/create" element={<AdminCreateSchool />} />
            <Route path="/superadmin/schools/:id/edit" element={<AdminEditSchool />} />
            <Route path="/superadmin/schools/:id" element={<AdminSchoolDetails />} />
            <Route path="/superadmin/users" element={<AdminUsers />} />
            <Route path="/superadmin/principals" element={<AdminPrincipals />} />
            <Route path="/superadmin/roles" element={<AdminRoles />} />
            <Route path="/superadmin/permissions" element={<AdminPermissions />} />
            <Route path="/superadmin/analytics" element={<AdminAnalytics />} />
            <Route path="/superadmin/reports" element={<AdminReports />} />
            <Route path="/superadmin/subscriptions" element={<AdminSubscriptions />} />
            <Route path="/superadmin/settings" element={<AdminSystemSettings />} />
            <Route path="/superadmin/audit-logs" element={<AdminAuditLogs />} />
            <Route path="/superadmin/notifications" element={<AdminNotifications />} />
            <Route path="/superadmin/profile" element={<AdminProfile />} />
          </Route>
        </Route>
      </Route>

      {/* ==================== PRINCIPAL ==================== */}
      <Route element={<ProtectedRoute />}>
        <Route element={<RoleRoute allowedRoles={["PRINCIPAL"]} />}>
          <Route element={<PrincipalLayout />}>
            <Route path="/principal" element={<Navigate to="/principal/dashboard" replace />} />
            <Route path="/principal/dashboard" element={<PrincipalDashboard />} />
            <Route path="/principal/students" element={<PrincipalStudents />} />
            <Route path="/principal/students/:id" element={<PrincipalStudentProfile />} />
            <Route path="/principal/teachers" element={<PrincipalTeachers />} />
            <Route path="/principal/teachers/:id" element={<PrincipalTeacherProfile />} />
            <Route path="/principal/grades" element={<PrincipalGrades />} />
            <Route path="/principal/sections" element={<PrincipalSections />} />
            <Route path="/principal/subjects" element={<PrincipalSubjects />} />
            <Route path="/principal/academic-years" element={<PrincipalAcademicYears />} />
            <Route path="/principal/timetable" element={<PrincipalTimetable />} />
            <Route path="/principal/exams" element={<PrincipalExams />} />
            <Route path="/principal/marks" element={<PrincipalMarks />} />
            <Route path="/principal/report-cards" element={<PrincipalReportCards />} />
            <Route path="/principal/homework" element={<PrincipalHomework />} />
            <Route path="/principal/homework/:id" element={<PrincipalHomeworkDetails />} />
            <Route path="/principal/attendance" element={<PrincipalAttendance />} />
            <Route path="/principal/attendance/reports" element={<PrincipalAttendanceReports />} />
            <Route path="/principal/announcements" element={<PrincipalAnnouncements />} />
            <Route path="/principal/calendar" element={<PrincipalCalendar />} />
            <Route path="/principal/notifications" element={<PrincipalNotifications />} />
            <Route path="/principal/settings" element={<PrincipalSettings />} />
            <Route path="/principal/profile" element={<PrincipalProfile />} />
            <Route path="/principal/analytics" element={<PrincipalAnalytics />} />
            <Route path="/principal/enrollments" element={<PrincipalEnrollments />} />
            <Route path="/principal/teaching-assignments" element={<PrincipalTeachingAssignments />} />
          </Route>
        </Route>
      </Route>

      {/* ==================== TEACHER ==================== */}
      <Route element={<ProtectedRoute />}>
        <Route element={<RoleRoute allowedRoles={["TEACHER"]} />}>
          <Route element={<TeacherLayout />}>
            <Route path="/teacher" element={<Navigate to="/teacher/dashboard" replace />} />
            <Route path="/teacher/dashboard" element={<TeacherDashboard />} />
            <Route path="/teacher/students" element={<TeacherStudents />} />
            <Route path="/teacher/students/:id" element={<TeacherStudentProfile />} />
            <Route path="/teacher/timetable" element={<TeacherTimetable />} />
            <Route path="/teacher/exams" element={<TeacherExams />} />
            <Route path="/teacher/exams/:id" element={<TeacherExamDetails />} />
            <Route path="/teacher/exams/:examId/marks/:examSubjectId" element={<TeacherMarksEntry />} />
            <Route path="/teacher/exams/:examId/subjects/:examSubjectId/marks" element={<TeacherMarksEntry />} />
            <Route path="/teacher/marks" element={<TeacherMarksEntry />} />
            <Route path="/teacher/homework" element={<TeacherHomework />} />
            <Route path="/teacher/homework/create" element={<TeacherCreateHomework />} />
            <Route path="/teacher/homework/:id/edit" element={<TeacherEditHomework />} />
            <Route path="/teacher/homework/edit/:id" element={<TeacherEditHomework />} />
            <Route path="/teacher/homework/:id" element={<TeacherHomeworkDetails />} />
            <Route path="/teacher/attendance" element={<TeacherAttendance />} />
            <Route path="/teacher/attendance/history" element={<TeacherAttendanceHistory />} />
            <Route path="/teacher/announcements" element={<TeacherAnnouncements />} />
            <Route path="/teacher/calendar" element={<TeacherCalendar />} />
            <Route path="/teacher/report-cards" element={<TeacherReportCards />} />
            <Route path="/teacher/notifications" element={<TeacherNotifications />} />
            <Route path="/teacher/settings" element={<TeacherSettings />} />
            <Route path="/teacher/profile" element={<TeacherProfile />} />
          </Route>
        </Route>
      </Route>

      {/* ==================== STUDENT ==================== */}
      <Route element={<ProtectedRoute />}>
        <Route element={<RoleRoute allowedRoles={["STUDENT"]} />}>
          <Route element={<StudentLayout />}>
            <Route path="/student" element={<Navigate to="/student/dashboard" replace />} />
            <Route path="/student/dashboard" element={<StudentDashboard />} />
            <Route path="/student/timetable" element={<StudentTimetable />} />
            <Route path="/student/exams" element={<StudentExams />} />
            <Route path="/student/marks" element={<StudentMarks />} />
            <Route path="/student/report-cards" element={<StudentReportCards />} />
            <Route path="/student/homework" element={<StudentHomework />} />
            <Route path="/student/homework/:id" element={<StudentHomeworkDetails />} />
            <Route path="/student/attendance" element={<StudentAttendance />} />
            <Route path="/student/announcements" element={<StudentAnnouncements />} />
            <Route path="/student/calendar" element={<StudentCalendar />} />
            <Route path="/student/notifications" element={<StudentNotifications />} />
            <Route path="/student/settings" element={<StudentSettings />} />
            <Route path="/student/profile" element={<StudentProfile />} />
          </Route>
        </Route>
      </Route>

      {/* ==================== OTHER ==================== */}
      <Route path="/unauthorized" element={<Unauthorized />} />
      <Route path="/" element={<RoleBasedRedirect />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
    </Suspense>
  );
};

export default AppRoutes;