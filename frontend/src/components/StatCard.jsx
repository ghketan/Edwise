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
      bg: 'bg-primary-fixed',
      text: 'text-primary',
      border: 'border-indigo-100',
    },
    emerald: {
      bg: 'bg-status-emerald-bg',
      text: 'text-status-emerald-text',
      border: 'border-emerald-100',
    },
    amber: {
      bg: 'bg-status-amber-bg',
      text: 'text-status-amber-text',
      border: 'border-amber-100',
    },
    rose: {
      bg: 'bg-status-rose-bg',
      text: 'text-status-rose-text',
      border: 'border-rose-100',
    },
    sky: {
      bg: 'bg-status-sky-bg',
      text: 'text-status-sky-text',
      border: 'border-sky-100',
    },
  };

  const scheme = colorMap[color] || colorMap.indigo;

  return (
    <div className="glass-card rounded-2xl p-5 transition-all hover:scale-[1.01] hover:shadow-md">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold text-outline uppercase tracking-wider">{title}</span>
        {Icon && (
          <div className={`p-2 rounded-xl ${scheme.bg} ${scheme.text} shadow-xs`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-on-surface font-mono tracking-tight">{value}</span>
        {badge && (
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-mono">
            {badge}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-on-surface-variant">{subtitle}</p>}
      {trend && (
        <div className="mt-2 text-xs flex items-center gap-1 font-medium font-mono">
          <span className={trend.positive ? 'text-status-emerald-text' : 'text-status-rose-text'}>
            {trend.value}
          </span>
          <span className="text-outline">{trend.label}</span>
        </div>
      )}
    </div>
  );
}
