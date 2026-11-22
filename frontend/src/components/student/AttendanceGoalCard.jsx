import React from 'react';
import { Target, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function AttendanceGoalCard({ goal = null }) {
  if (!goal) {
    return (
      <section className="glass-card rounded-2xl p-5 shadow-sm min-w-0">
        <div className="flex items-center gap-2 mb-3">
          <Target className="w-4 h-4 text-status-emerald-text shrink-0" />
          <h2 className="font-bold text-sm text-on-surface">75% Attendance Goal Planner</h2>
        </div>
        <div className="py-6 text-center text-xs text-outline border border-dashed border-slate-200 rounded-xl">
          No attendance records available yet.
        </div>
      </section>
    );
  }

  const rate = Number.isFinite(Number(goal.current_rate)) ? Number(goal.current_rate) : 0;
  const targetRate = Number.isFinite(Number(goal.target_rate)) ? Number(goal.target_rate) : 75;
  const attended = Number.isFinite(Number(goal.current_attended)) ? Number(goal.current_attended) : 0;
  const total = Number.isFinite(Number(goal.total_conducted)) ? Number(goal.total_conducted) : 0;
  const needed = Number.isFinite(Number(goal.needed_consecutive_classes))
    ? Number(goal.needed_consecutive_classes)
    : 0;
  const safeSkips = Number.isFinite(Number(goal.safe_skips_available))
    ? Number(goal.safe_skips_available)
    : 0;
  const barWidth = Math.max(0, Math.min(100, rate));
  const markerPos = Math.max(0, Math.min(100, targetRate));

  return (
    <section className="glass-panel rounded-2xl p-5 shadow-sm min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-status-emerald-bg text-status-emerald-text flex items-center justify-center shadow-sm">
            <Target className="w-4 h-4 shrink-0" />
          </div>
          <h2 className="font-bold text-sm text-on-surface">75% Attendance Goal Planner</h2>
        </div>
        <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-surface-container-low text-on-surface border border-glass-border font-mono">
          Target: {targetRate}%
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4 text-xs">
        <div className="p-3 rounded-xl bg-surface-container-low/70 border border-glass-border">
          <div className="text-[10px] font-bold uppercase tracking-wider text-outline">
            Current Rate
          </div>
          <div
            className={`text-lg font-bold font-mono mt-0.5 ${
              goal.is_warning ? 'text-status-rose-text' : 'text-status-emerald-text'
            }`}
          >
            {rate.toFixed(1)}%
          </div>
        </div>
        <div className="p-3 rounded-xl bg-surface-container-low/70 border border-glass-border">
          <div className="text-[10px] font-bold uppercase tracking-wider text-outline">
            Sessions Attended
          </div>
          <div className="text-lg font-bold font-mono text-on-surface mt-0.5">
            {attended} / {total} classes
          </div>
        </div>
      </div>

      {/* Progress Bar with Target Marker */}
      <div className="mb-4">
        <div className="relative h-3 w-full bg-surface-container-high rounded-full overflow-hidden border border-slate-200/60">
          <div
            className={`h-full rounded-full transition-all ${
              goal.is_warning ? 'bg-rose-500' : 'bg-emerald-500'
            }`}
            style={{ width: `${barWidth}%` }}
          />
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-slate-900"
            style={{ left: `${markerPos}%` }}
            title={`${targetRate}% Target`}
          />
        </div>
        <div className="flex justify-between text-[10px] text-outline mt-1 font-mono">
          <span>0%</span>
          <span>Target {targetRate}%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Status Callout */}
      <div
        className={`p-3.5 rounded-xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 ${
          goal.is_warning
            ? 'bg-status-rose-bg/90 border-rose-200 text-status-rose-text'
            : 'bg-status-emerald-bg/90 border-emerald-200 text-status-emerald-text'
        }`}
      >
        <div className="flex items-start gap-2 min-w-0">
          {goal.is_warning ? (
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          )}
          <p className="leading-relaxed break-words min-w-0 font-medium">
            {goal.status_message}
          </p>
        </div>

        <span
          className={`text-[11px] font-bold px-3 py-1 rounded-full shrink-0 self-start sm:self-center font-mono ${
            goal.is_warning
              ? 'bg-rose-200 text-rose-900 border border-rose-300'
              : 'bg-emerald-200 text-emerald-900 border border-emerald-300'
          }`}
        >
          {goal.is_warning
            ? `Need ${needed} consecutive classes`
            : `${safeSkips} safe skips`}
        </span>
      </div>
    </section>
  );
}
