import React from 'react';
import { useAuth } from '../context/AuthContext';
import { GraduationCap, LogOut, Calendar } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

export default function Navbar() {
  const { user, role, sessions, activeSession, setActiveSession, logout } = useAuth();

  const roleBadge = {
    ADMINISTRATOR: 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/50 dark:text-purple-300 dark:border-purple-700',
    TEACHER: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/50 dark:text-blue-300 dark:border-blue-700',
    STUDENT: 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/50 dark:text-emerald-300 dark:border-emerald-700',
  }[role] || 'bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700';

  return (
    <header className="sticky top-0 z-40 bg-surface-container-lowest/80 dark:bg-slate-900/80 backdrop-blur-xl border-b border-glass-border dark:border-slate-800 h-16 shadow-[0_1px_8px_rgba(0,0,0,0.03)] transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary-container flex items-center justify-center text-white shadow-md shadow-indigo-300 dark:shadow-indigo-950">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-on-surface dark:text-white tracking-tight text-lg">EDWISE</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-status-sky-bg text-status-sky-text dark:bg-sky-950/60 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
                v1.0
              </span>
            </div>
            <p className="text-[10px] text-on-surface-variant dark:text-slate-400 font-medium hidden sm:block">
              Evidence-Grounded Learning Analytics Platform
            </p>
          </div>
        </div>

        {/* Right Session, Theme Toggle & Profile Actions */}
        <div className="flex items-center gap-2.5 sm:gap-4">
          {/* Academic Session Selector */}
          {sessions && sessions.length > 0 && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-on-surface-variant dark:text-slate-300 bg-surface-container-low dark:bg-slate-800/80 border border-glass-border dark:border-slate-700 px-3 py-1.5 rounded-full shadow-xs">
              <Calendar className="w-3.5 h-3.5 text-secondary dark:text-cyan-400" />
              <span className="font-medium text-outline dark:text-slate-400">Session:</span>
              <select
                value={activeSession?.id || ''}
                onChange={(e) => {
                  const selected = sessions.find((s) => s.id === parseInt(e.target.value));
                  if (selected) setActiveSession(selected);
                }}
                className="bg-transparent font-semibold text-on-surface dark:text-slate-100 focus:outline-none cursor-pointer"
              >
                {sessions.map((s) => (
                  <option key={s.id} value={s.id} className="dark:bg-slate-800 dark:text-slate-100">
                    {s.name} {s.is_active ? '• Active' : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Theme Toggle (Dark / Light) */}
          <ThemeToggle />

          {/* User profile & Role Badge */}
          {user && (
            <div className="flex items-center gap-2.5 pl-2 sm:pl-4 sm:border-l border-slate-200 dark:border-slate-800">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-semibold text-on-surface dark:text-white leading-tight">
                  {user.student_profile?.full_name || user.teacher_profile?.full_name || user.username}
                </div>
                <div className="text-[10px] text-outline dark:text-slate-400 font-mono">
                  {user.student_profile?.admission_number || user.teacher_profile?.employee_id || user.username}
                </div>
              </div>

              <span
                className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${roleBadge}`}
              >
                {role}
              </span>

              {/* Logout button */}
              <button
                onClick={logout}
                title="Sign Out"
                className="p-1.5 text-outline dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-status-rose-bg dark:hover:bg-rose-950/40 rounded-lg transition-colors ml-1 cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
