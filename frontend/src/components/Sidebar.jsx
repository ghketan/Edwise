import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  CalendarCheck,
  Award,
  FileText,
  BarChart3,
  Users,
  Settings,
  ShieldCheck,
  BrainCircuit,
  BookOpen,
  Sparkles,
  UserCheck,
} from 'lucide-react';

export default function Sidebar() {
  const { role } = useAuth();

  const adminLinks = [
    { to: '/admin', label: 'Overview', icon: LayoutDashboard },
    { to: '/admin/users', label: 'User Accounts', icon: UserCheck },
    { to: '/admin/setup', label: 'Classes & Teachers', icon: Settings },
    { to: '/admin/roster', label: 'Student Rosters', icon: Users },
    { to: '/admin/rules', label: 'Recommendation Rules', icon: Sparkles },
    { to: '/admin/models', label: 'ML Model Registry', icon: BrainCircuit },
    { to: '/admin/audit', label: 'Audit Trail', icon: ShieldCheck },
  ];

  const teacherLinks = [
    { to: '/teacher', label: 'Teacher Dashboard', icon: LayoutDashboard },
    { to: '/teacher/attendance', label: 'Attendance Entry', icon: CalendarCheck },
    { to: '/teacher/marks', label: 'Exams & Marks', icon: Award },
    { to: '/teacher/assignments', label: 'Assignments', icon: BookOpen },
    { to: '/teacher/analytics', label: 'Analytics & Reports', icon: BarChart3 },
  ];

  const studentLinks = [
    { to: '/student', label: 'Academic Overview', icon: LayoutDashboard },
    { to: '/student/assignments', label: 'Assignments', icon: BookOpen },
  ];

  const links =
    role === 'ADMINISTRATOR'
      ? adminLinks
      : role === 'TEACHER'
      ? teacherLinks
      : studentLinks;

  return (
    <aside className="w-full md:w-64 shrink-0 bg-white border-b md:border-b-0 md:border-r border-slate-200 md:min-h-[calc(100vh-4rem)] p-3 md:p-4 flex flex-col justify-between">
      <div>
        <div className="px-3 mb-2 md:mb-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          {role} Workspace
        </div>
        <nav className="flex flex-wrap md:flex-col gap-1 md:space-y-1">
          {links.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/admin' || item.to === '/teacher' || item.to === '/student'}
                className={({ isActive }) =>
                  `flex items-center gap-2 md:gap-3 px-3 py-2 md:py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 font-semibold shadow-sm'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="hidden md:block p-3 bg-slate-50 rounded-xl border border-slate-200/60 text-[11px] text-slate-500">
        <p className="font-semibold text-slate-700">EDWISE Prototype</p>
        <p className="mt-0.5 text-slate-400">Offline-trained ML • Role-scoped</p>
      </div>
    </aside>
  );
}

