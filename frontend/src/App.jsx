import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';

// Pages
import Login from './pages/Login';
import LegalDocument from './pages/LegalDocument';
import AdminDashboard from './pages/admin/AdminDashboard';
import UserManagement from './pages/admin/UserManagement';
import SetupClasses from './pages/admin/SetupClasses';
import RosterImport from './pages/admin/RosterImport';
import RecommendationRules from './pages/admin/RecommendationRules';
import ModelRegistry from './pages/admin/ModelRegistry';
import AuditLogs from './pages/admin/AuditLogs';

import TeacherDashboard from './pages/teacher/TeacherDashboard';
import AttendanceEntry from './pages/teacher/AttendanceEntry';
import MarksEntry from './pages/teacher/MarksEntry';
import StudentDetail from './pages/teacher/StudentDetail';
import TeacherAssignments from './pages/teacher/Assignments';
import AnalyticsReports from './pages/teacher/AnalyticsReports';

import StudentDashboard from './pages/student/StudentDashboard';
import StudentAssignments from './pages/student/StudentAssignments';

// Main App Layout with Navbar, Sidebar & Ambient Glow
function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-canvas-slate dark:bg-[#070e1b] text-on-surface dark:text-slate-100 overflow-x-hidden relative transition-colors duration-200">
      {/* Atmospheric depth glows from Academic Glass Analytics */}
      <div className="ambient-glow-cyan"></div>
      <div className="ambient-glow-indigo"></div>

      <Navbar />
      <div className="flex-1 flex flex-col md:flex-row max-w-7xl w-full mx-auto min-w-0 relative z-10">
        <Sidebar />
        <main className="flex-1 min-w-0 p-4 sm:p-6 overflow-y-auto overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// Root redirector based on authenticated user's role
function RoleRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === 'ADMINISTRATOR') return <Navigate to="/admin" replace />;
  if (user.role === 'TEACHER') return <Navigate to="/teacher" replace />;
  if (user.role === 'STUDENT') return <Navigate to="/student" replace />;
  return <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public login & student self-registration */}
          <Route path="/login" element={<Login />} />
          <Route path="/privacy" element={<LegalDocument defaultType="privacy" />} />
          <Route path="/terms" element={<LegalDocument defaultType="terms" />} />

          {/* Protected Application Routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<RoleRedirect />} />

              {/* Administrator routes */}
              <Route element={<ProtectedRoute allowedRoles={['ADMINISTRATOR']} />}>
                <Route path="/admin" element={<AdminDashboard />} />
                <Route path="/admin/users" element={<UserManagement />} />
                <Route path="/admin/setup" element={<SetupClasses />} />
                <Route path="/admin/roster" element={<RosterImport />} />
                <Route path="/admin/rules" element={<RecommendationRules />} />
                <Route path="/admin/models" element={<ModelRegistry />} />
                <Route path="/admin/audit" element={<AuditLogs />} />
              </Route>

              {/* Teacher routes (also accessible to admin) */}
              <Route element={<ProtectedRoute allowedRoles={['TEACHER', 'ADMINISTRATOR']} />}>
                <Route path="/teacher" element={<TeacherDashboard />} />
                <Route path="/teacher/attendance" element={<AttendanceEntry />} />
                <Route path="/teacher/marks" element={<MarksEntry />} />
                <Route path="/teacher/students/:studentId" element={<StudentDetail />} />
                <Route path="/teacher/assignments" element={<TeacherAssignments />} />
                <Route path="/teacher/analytics" element={<AnalyticsReports />} />
              </Route>

              {/* Student routes */}
              <Route element={<ProtectedRoute allowedRoles={['STUDENT']} />}>
                <Route path="/student" element={<StudentDashboard />} />
                <Route path="/student/assignments" element={<StudentAssignments />} />
              </Route>
            </Route>
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
