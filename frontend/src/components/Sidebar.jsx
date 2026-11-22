import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  CalendarCheck,
  Award,
  BarChart3,
  Users,
  Settings,
  ShieldCheck,
  BrainCircuit,
  BookOpen,
  Sparkles,
  UserCheck,
  Activity,
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
    <aside className="w-full md:w-64 shrink-0 bg-sidebar-surface md:rounded-2xl shadow-[0_8px_32px_rgba(12,40,54,0.35)] my-0 md:my-4 p-3 md:p-4 flex flex-col justify-between text-slate-300 border border-slate-700/40">
      <div>
        <div className="px-3 mb-3 text-[10px] font-bold uppercase tracking-wider text-secondary-fixed-dim">
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
                  `flex items-center gap-2.5 md:gap-3 px-3 py-2 md:py-2.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-primary-container text-white shadow-[0_0_16px_rgba(79,70,229,0.45)] font-semibold'
                      : 'text-slate-300 hover:bg-white/10 hover:text-white'
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

      <div className="hidden md:flex flex-col gap-2 p-3 bg-white/5 rounded-xl border border-white/10 text-[11px] text-slate-300 mt-6">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase font-bold text-secondary-fixed tracking-wider">
            Network Engine
          </span>
          <span className="w-2 h-2 rounded-full bg-status-emerald-text shadow-[0_0_8px_rgba(4,120,87,0.8)]"></span>
        </div>
        <p className="text-slate-300 font-medium">ML Models Active</p>
        <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
          <Activity className="w-3 h-3 text-secondary-fixed" />
          <span>BOLA Guard Active</span>
        </div>
      </div>
    </aside>
  );
}
