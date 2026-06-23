import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";

import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import RoleRoute from "./components/RoleRoute";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ForgotPassword from "./pages/ForgotPassword";

import Dashboard from "./pages/Dashboard";
import Students from "./pages/Students";
import StudentDetail from "./pages/StudentDetail";
import Fees from "./pages/Fees";
import Finance from "./pages/Finance";
import Expenses from "./pages/Expenses";
import Reports from "./pages/Reports";
import Tiles from "./pages/Tiles";
import Settings from "./pages/Settings";
import Marks from "./pages/Marks";
import OwnerTeachers from "./pages/OwnerTeachers";
import OwnerApprovals from "./pages/OwnerApprovals";
import Notifications from "./pages/Notifications";
import OwnerAudit from "./pages/OwnerAudit";
import OwnerScanner from "./pages/OwnerScanner";
import OwnerAI from "./pages/OwnerAI";
import OwnerRecords from "./pages/OwnerRecords";
import OwnerAttendance from "./pages/OwnerAttendance";
import OwnerTimetable from "./pages/OwnerTimetable";

import StaffDashboard from "./pages/StaffDashboard";
import StaffStudents from "./pages/StaffStudents";
import StaffStudentDetail from "./pages/StaffStudentDetail";

import TeacherDashboard from "./pages/TeacherDashboard";
import TeacherClasses from "./pages/TeacherClasses";
import TeacherAssignments from "./pages/TeacherAssignments";
import TeacherAttendance from "./pages/TeacherAttendance";
import TeacherTimetable from "./pages/TeacherTimetable";

import StudentDashboard from "./pages/StudentDashboard";
import StudentMarks from "./pages/StudentMarks";
import StudentAssignments from "./pages/StudentAssignments";
import StudentAttendance from "./pages/StudentAttendance";
import StudentTimetable from "./pages/StudentTimetable";
import MindGames from "./pages/MindGames";

function Home() {
  const { user } = useAuth();
  if (!user) return null;
  return ({
    owner:   <Dashboard />,
    staff:   <StaffDashboard />,
    teacher: <TeacherDashboard />,
    student: <StudentDashboard />,
  })[user.role] || <Dashboard />;
}

function StudentsRouter() {
  const { user } = useAuth();
  if (user?.role === "owner") return <Students />;
  return <StaffStudents />;  // staff & any teacher who lands here
}

function StudentDetailRouter() {
  const { user } = useAuth();
  if (user?.role === "owner") return <StudentDetail />;
  return <StaffStudentDetail />;
}

function AttendanceRouter() {
  const { user } = useAuth();
  if (user?.role === "owner") return <OwnerAttendance />;
  if (user?.role === "teacher") return <TeacherAttendance />;
  return <Navigate to="/" replace />;
}

function TimetableRouter() {
  const { user } = useAuth();
  if (user?.role === "owner") return <OwnerTimetable />;
  if (user?.role === "teacher") return <TeacherTimetable />;
  return <Navigate to="/" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login"   element={<Login />} />
          <Route path="/signup"  element={<Signup />} />
          <Route path="/forgot"  element={<ForgotPassword />} />

          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/"             element={<Home />} />
            <Route path="/settings"     element={<Settings />} />

            {/* Owner / Staff shared */}
            <Route path="/students"     element={<StudentsRouter />} />
            <Route path="/students/:id" element={<StudentDetailRouter />} />

            {/* Owner-only */}
            <Route path="/teachers"      element={<RoleRoute role="owner"><OwnerTeachers /></RoleRoute>} />
            <Route path="/approvals"     element={<RoleRoute role="owner"><OwnerApprovals /></RoleRoute>} />
            <Route path="/fees"          element={<RoleRoute role="owner"><Fees /></RoleRoute>} />
            <Route path="/finance"       element={<RoleRoute role="owner"><Finance /></RoleRoute>} />
            <Route path="/expenses"      element={<RoleRoute role="owner"><Expenses /></RoleRoute>} />
            <Route path="/reports"       element={<RoleRoute role="owner"><Reports /></RoleRoute>} />
            <Route path="/tiles"         element={<RoleRoute role="owner"><Tiles /></RoleRoute>} />
            <Route path="/marks"         element={<RoleRoute role="owner"><Marks /></RoleRoute>} />

            {/* Owner + Teacher: attendance & timetable (component swaps by role) */}
            <Route path="/attendance"    element={<AttendanceRouter />} />
            <Route path="/timetable"     element={<TimetableRouter />} />
            <Route path="/notifications" element={<RoleRoute role="owner"><Notifications /></RoleRoute>} />
            <Route path="/audit"         element={<RoleRoute role="owner"><OwnerAudit /></RoleRoute>} />
            <Route path="/scanner"       element={<RoleRoute role="owner"><OwnerScanner /></RoleRoute>} />
            <Route path="/assistant"     element={<RoleRoute role="owner"><OwnerAI /></RoleRoute>} />
            <Route path="/records"       element={<RoleRoute role="owner"><OwnerRecords /></RoleRoute>} />

            {/* Teacher-only */}
            <Route path="/my-classes"   element={<RoleRoute role="teacher"><TeacherClasses /></RoleRoute>} />
            <Route path="/assignments"  element={<RoleRoute role="teacher"><TeacherAssignments /></RoleRoute>} />
            <Route path="/quick-entry"  element={<RoleRoute role="teacher"><StaffDashboard /></RoleRoute>} />

            {/* Student-only */}
            <Route path="/my-marks"        element={<RoleRoute role="student"><StudentMarks /></RoleRoute>} />
            <Route path="/my-attendance"   element={<RoleRoute role="student"><StudentAttendance /></RoleRoute>} />
            <Route path="/my-timetable"    element={<RoleRoute role="student"><StudentTimetable /></RoleRoute>} />
            <Route path="/my-assignments"  element={<RoleRoute role="student"><StudentAssignments /></RoleRoute>} />
            <Route path="/games"           element={<RoleRoute role="student"><MindGames /></RoleRoute>} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
