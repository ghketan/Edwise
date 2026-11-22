import React from 'react';

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = 'indigo',
  badge,
}) {
  const colorMap = {
    indigo: {
      bg: 'bg-primary-fixed dark:bg-indigo-950/60',
      text: 'text-primary dark:text-indigo-400',
      border: 'border-indigo-100 dark:border-indigo-900/50',
    },
    emerald: {
      bg: 'bg-status-emerald-bg dark:bg-emerald-950/60',
      text: 'text-status-emerald-text dark:text-emerald-400',
      border: 'border-emerald-100 dark:border-emerald-900/50',
    },
    amber: {
      bg: 'bg-status-amber-bg dark:bg-amber-950/60',
      text: 'text-status-amber-text dark:text-amber-400',
      border: 'border-amber-100 dark:border-amber-900/50',
    },
    rose: {
      bg: 'bg-status-rose-bg dark:bg-rose-950/60',
      text: 'text-status-rose-text dark:text-rose-400',
      border: 'border-rose-100 dark:border-rose-900/50',
    },
    sky: {
      bg: 'bg-status-sky-bg dark:bg-sky-950/60',
      text: 'text-status-sky-text dark:text-sky-400',
      border: 'border-sky-100 dark:border-sky-900/50',
    },
  };

  const scheme = colorMap[color] || colorMap.indigo;

  return (
    <div className="glass-card rounded-2xl p-5 transition-all hover:scale-[1.01] hover:shadow-md">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold text-outline dark:text-slate-400 uppercase tracking-wider">{title}</span>
        {Icon && (
          <div className={`p-2 rounded-xl ${scheme.bg} ${scheme.text} shadow-xs`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-on-surface dark:text-white font-mono tracking-tight">{value}</span>
        {badge && (
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-surface-container-high dark:bg-slate-800 text-on-surface-variant dark:text-slate-300 font-mono">
            {badge}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-on-surface-variant dark:text-slate-400">{subtitle}</p>}
      {trend && (
        <div className="mt-2 text-xs flex items-center gap-1 font-medium font-mono">
          <span className={trend.positive ? 'text-status-emerald-text dark:text-emerald-400' : 'text-status-rose-text dark:text-rose-400'}>
            {trend.value}
          </span>
          <span className="text-outline dark:text-slate-500">{trend.label}</span>
        </div>
      )}
    </div>
  );
}
