import React from 'react';
import { useAuth } from '../context/AuthContext';
import { GraduationCap, LogOut, User, Calendar } from 'lucide-react';

export default function Navbar() {
  const { user, role, sessions, activeSession, setActiveSession, logout } = useAuth();

  const roleBadge = {
    ADMINISTRATOR: 'bg-purple-100 text-purple-800 border-purple-200',
    TEACHER: 'bg-blue-100 text-blue-800 border-blue-200',
    STUDENT: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  }[role] || 'bg-slate-100 text-slate-800 border-slate-200';

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-xs border-b border-slate-200 h-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-sm shadow-indigo-200">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 tracking-tight text-lg">EDWISE</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                v1.0
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium hidden sm:block">
              Evidence-Grounded Learning Analytics Platform
            </p>
          </div>
        </div>

        {/* Right Session & Profile Actions */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Academic Session Selector */}
          {sessions && sessions.length > 0 && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-600 bg-slate-50 border border-slate-200 px-2.5 py-1.5 rounded-lg">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-medium text-slate-500">Session:</span>
              <select
                value={activeSession?.id || ''}
                onChange={(e) => {
                  const selected = sessions.find((s) => s.id === parseInt(e.target.value));
                  if (selected) setActiveSession(selected);
                }}
                className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
              >
                {sessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} {s.is_active ? '• Active' : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* User profile & Role Badge */}
          {user && (
            <div className="flex items-center gap-2.5 pl-2 sm:pl-4 sm:border-l border-slate-200">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-semibold text-slate-900 leading-tight">
                  {user.student_profile?.full_name || user.teacher_profile?.full_name || user.username}
                </div>
                <div className="text-[10px] text-slate-400 font-mono">
                  {user.student_profile?.admission_number || user.teacher_profile?.employee_id || user.username}
                </div>
              </div>

              <span
                className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${roleBadge}`}
              >
                {role}
              </span>

              {/* Logout button */}
              <button
                onClick={logout}
                title="Sign Out"
                className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors ml-1"
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

