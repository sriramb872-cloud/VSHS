import React from "react";
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
import Login from "../pages/auth/Login";

// Common
import Unauthorized from "../pages/common/Unauthorized";
import NotFound from "../pages/common/NotFound";

// Super Admin Pages
import AdminDashboard from "../pages/superadmin/Dashboard";
import AdminSchools from "../pages/superadmin/Schools";
import AdminCreateSchool from "../pages/superadmin/CreateSchool";
import AdminEditSchool from "../pages/superadmin/EditSchool";
import AdminSchoolDetails from "../pages/superadmin/SchoolDetails";
import AdminUsers from "../pages/superadmin/Users";
import AdminPrincipals from "../pages/superadmin/Principals";
import AdminRoles from "../pages/superadmin/Roles";
import AdminPermissions from "../pages/superadmin/Permissions";
import AdminAnalytics from "../pages/superadmin/Analytics";
import AdminReports from "../pages/superadmin/Reports";
import AdminSubscriptions from "../pages/superadmin/Subscriptions";
import AdminSystemSettings from "../pages/superadmin/SystemSettings";
import AdminAuditLogs from "../pages/superadmin/AuditLogs";
import AdminNotifications from "../pages/superadmin/Notifications";
import AdminProfile from "../pages/superadmin/Profile";

// Principal Pages
import PrincipalDashboard from "../pages/principal/Dashboard";
import PrincipalStudents from "../pages/principal/Students";
import PrincipalStudentProfile from "../pages/principal/StudentProfile";
import PrincipalTeachers from "../pages/principal/Teachers";
import PrincipalTeacherProfile from "../pages/principal/TeacherProfile";
import PrincipalGrades from "../pages/principal/Grades";
import PrincipalSections from "../pages/principal/Sections";
import PrincipalSubjects from "../pages/principal/Subjects";
import PrincipalAcademicYears from "../pages/principal/AcademicYears";
import PrincipalTimetable from "../pages/principal/Timetable";
import PrincipalExams from "../pages/principal/Exams";
import PrincipalMarks from "../pages/principal/Marks";
import PrincipalReportCards from "../pages/principal/ReportCards";
import PrincipalHomework from "../pages/principal/Homework";
import PrincipalHomeworkDetails from "../pages/principal/HomeworkDetails";
import PrincipalAttendance from "../pages/principal/Attendance";
import PrincipalAttendanceReports from "../pages/principal/AttendanceReports";
import PrincipalAnnouncements from "../pages/principal/Announcements";
import PrincipalCalendar from "../pages/principal/Calendar";
import PrincipalNotifications from "../pages/principal/Notifications";
import PrincipalSettings from "../pages/principal/Settings";
import PrincipalProfile from "../pages/principal/Profile";
import PrincipalAnalytics from "../pages/principal/Analytics";
import PrincipalEnrollments from "../pages/principal/Enrollments";

// Teacher Pages
import TeacherDashboard from "../pages/teacher/Dashboard";
import TeacherStudents from "../pages/teacher/Students";
import TeacherStudentProfile from "../pages/teacher/StudentProfile";
import TeacherTimetable from "../pages/teacher/Timetable";
import TeacherExams from "../pages/teacher/Exams";
import TeacherExamDetails from "../pages/teacher/ExamDetails";
import TeacherMarksEntry from "../pages/teacher/MarksEntry";
import TeacherHomework from "../pages/teacher/Homework";
import TeacherCreateHomework from "../pages/teacher/CreateHomework";
import TeacherEditHomework from "../pages/teacher/EditHomework";
import TeacherHomeworkDetails from "../pages/teacher/HomeworkDetails";
import TeacherAttendance from "../pages/teacher/Attendance";
import TeacherAttendanceHistory from "../pages/teacher/AttendanceHistory";
import TeacherAnnouncements from "../pages/teacher/Announcements";
import TeacherCalendar from "../pages/teacher/Calendar";
import TeacherReportCards from "../pages/teacher/ReportCards";
import TeacherNotifications from "../pages/teacher/Notifications";
import TeacherSettings from "../pages/teacher/Settings";
import TeacherProfile from "../pages/teacher/Profile";

// Student Pages
import StudentDashboard from "../pages/student/Dashboard";
import StudentTimetable from "../pages/student/Timetable";
import StudentExams from "../pages/student/Exams";
import StudentMarks from "../pages/student/Marks";
import StudentReportCards from "../pages/student/ReportCards";
import StudentHomework from "../pages/student/Homework";
import StudentHomeworkDetails from "../pages/student/HomeworkDetails";
import StudentAttendance from "../pages/student/Attendance";
import StudentAnnouncements from "../pages/student/Announcements";
import StudentCalendar from "../pages/student/Calendar";
import StudentNotifications from "../pages/student/Notifications";
import StudentSettings from "../pages/student/Settings";
import StudentProfile from "../pages/student/Profile";

const AppRoutes: React.FC = () => {
  return (
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
  );
};

export default AppRoutes;