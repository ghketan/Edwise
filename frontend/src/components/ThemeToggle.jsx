import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle({ className = '', showLabel = false }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}
      title={`Switch to ${isDark ? 'light' : 'dark'} theme`}
      className={`inline-flex items-center gap-2 p-2 rounded-xl transition-all duration-200 border cursor-pointer select-none ${
        isDark
          ? 'bg-slate-800/80 border-slate-700/80 text-amber-400 hover:bg-slate-700 hover:text-amber-300 shadow-sm'
          : 'bg-white/80 border-slate-200/80 text-slate-700 hover:bg-slate-100 hover:text-indigo-600 shadow-sm'
      } ${className}`}
    >
      <div className="relative w-4 h-4 flex items-center justify-center">
        {isDark ? (
          <Sun className="w-4 h-4 transition-transform duration-200 rotate-0 scale-100 text-amber-400" />
        ) : (
          <Moon className="w-4 h-4 transition-transform duration-200 rotate-0 scale-100 text-slate-700" />
        )}
      </div>
      {showLabel && (
        <span className="text-xs font-semibold capitalize font-mono">
          {isDark ? 'Light' : 'Dark'}
        </span>
      )}
    </button>
  );
}
