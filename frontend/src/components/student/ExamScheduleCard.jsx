import React from 'react';
import { Calendar, Clock, Download, AlertCircle } from 'lucide-react';
import { formatDateOnly } from '../../utils/format';

function computeCountdown(exam) {
  if (exam.countdown_status && exam.days_left !== null && exam.days_left !== undefined) {
    return { daysLeft: exam.days_left, status: exam.countdown_status };
  }
  if (!exam.date) {
    return { daysLeft: null, status: 'Scheduled' };
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const examDate = new Date(`${exam.date}T00:00:00`);
  if (Number.isNaN(examDate.getTime())) {
    return { daysLeft: null, status: 'Scheduled' };
  }
  const diffDays = Math.round((examDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  const status = diffDays === 0 ? 'Today!' : diffDays > 0 ? `${diffDays} Days Left` : 'Completed';
  return { daysLeft: diffDays, status };
}

function getCountdownBadgeStyle(daysLeft, status) {
  if (status === 'Completed' || (daysLeft !== null && daysLeft < 0)) {
    return 'bg-surface-container-high text-outline border border-glass-border';
  }
  if (status === 'Today!' || (daysLeft !== null && daysLeft <= 3)) {
    return 'bg-status-rose-bg text-status-rose-text border border-rose-200';
  }
  if (daysLeft !== null && daysLeft <= 7) {
    return 'bg-status-amber-bg text-status-amber-text border border-amber-200';
  }
  return 'bg-status-emerald-bg text-status-emerald-text border border-emerald-200';
}

export default function ExamScheduleCard({
  exams = [],
  subjectMap = {},
  onDownloadDatesheet,
  downloadError = '',
  downloadingExamId = null,
}) {
  return (
    <section className="glass-panel rounded-2xl p-5 shadow-sm min-w-0">
      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-primary-container text-white flex items-center justify-center shadow-sm">
            <Calendar className="w-4 h-4 shrink-0" />
          </div>
          <h2 className="font-bold text-sm text-on-surface truncate">
            Upcoming Exam Schedules &amp; Datesheets
          </h2>
        </div>
        <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-surface-container-low text-primary border border-glass-border font-mono shrink-0">
          {exams.length} Scheduled
        </span>
      </div>

      {downloadError && (
        <div className="mb-3 p-3 rounded-xl bg-status-rose-bg border border-rose-200 text-xs text-status-rose-text flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="break-words min-w-0 font-medium">{downloadError}</span>
        </div>
      )}

      {exams.length === 0 ? (
        <div className="py-8 text-center text-xs text-outline border border-dashed border-slate-200 rounded-xl font-mono">
          No upcoming exams scheduled for this session.
        </div>
      ) : (
        <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
          {exams.map((exam) => {
            const { daysLeft, status } = computeCountdown(exam);
            const badgeStyle = getCountdownBadgeStyle(daysLeft, status);
            const subjectLabel = exam.subject_name || subjectMap[exam.subject_id] || 'Subject';
            const hasDatesheet = Boolean(exam.datesheet_filename);

            return (
              <div
                key={exam.id}
                className="p-3.5 rounded-xl border border-glass-border bg-surface-container-lowest/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 min-w-0 break-words shadow-xs hover:border-slate-300 transition-all"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-bold text-xs text-on-surface break-words">
                    {exam.name}
                  </div>
                  <div className="text-[11px] text-on-surface-variant mt-0.5 break-words font-medium">
                    {subjectLabel}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-outline mt-1 font-mono">
                    <span>{formatDateOnly(exam.date)}</span>
                    <span>•</span>
                    <span className="inline-flex items-center gap-1 font-sans text-on-surface-variant font-medium">
                      <Clock className="w-3 h-3 text-outline" />
                      {exam.time_slot || '09:00 AM - 12:00 PM'}
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <span className={`text-[11px] font-bold px-3 py-1 rounded-full font-mono ${badgeStyle}`}>
                    {status}
                  </span>

                  {hasDatesheet ? (
                    <button
                      type="button"
                      onClick={() => onDownloadDatesheet?.(exam)}
                      disabled={downloadingExamId === exam.id}
                      className="inline-flex items-center gap-1 px-3 py-1 text-[11px] font-bold rounded-xl bg-surface-container-low border border-glass-border text-on-surface hover:bg-surface-container-high transition-all active:scale-[0.98] disabled:opacity-50"
                    >
                      <Download className="w-3.5 h-3.5 text-primary" />
                      {downloadingExamId === exam.id ? 'Downloading...' : 'Download Datesheet'}
                    </button>
                  ) : (
                    <span className="text-[11px] text-outline italic px-1 font-mono">
                      No datesheet
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
