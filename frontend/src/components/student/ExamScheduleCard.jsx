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
    return 'bg-slate-100 text-slate-600 border border-slate-200';
  }
  if (status === 'Today!' || (daysLeft !== null && daysLeft <= 3)) {
    return 'bg-rose-100 text-rose-800 border border-rose-200';
  }
  if (daysLeft !== null && daysLeft <= 7) {
    return 'bg-amber-100 text-amber-800 border border-amber-200';
  }
  return 'bg-emerald-100 text-emerald-800 border border-emerald-200';
}

export default function ExamScheduleCard({
  exams = [],
  subjectMap = {},
  onDownloadDatesheet,
  downloadError = '',
  downloadingExamId = null,
}) {
  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm min-w-0">
      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <Calendar className="w-4 h-4 text-indigo-600 shrink-0" />
          <h2 className="font-semibold text-sm text-slate-900 truncate">
            Upcoming Exam Schedules &amp; Datesheets
          </h2>
        </div>
        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 shrink-0">
          {exams.length} Scheduled
        </span>
      </div>

      {downloadError && (
        <div className="mb-3 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="break-words min-w-0">{downloadError}</span>
        </div>
      )}

      {exams.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
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
                className="p-3 rounded-lg border border-slate-200/80 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 min-w-0 break-words"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-xs text-slate-900 break-words">
                    {exam.name}
                  </div>
                  <div className="text-[11px] text-slate-600 mt-0.5 break-words">
                    {subjectLabel}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500 mt-1">
                    <span className="font-mono">{formatDateOnly(exam.date)}</span>
                    <span>•</span>
                    <span className="inline-flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {exam.time_slot || '09:00 AM - 12:00 PM'}
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${badgeStyle}`}>
                    {status}
                  </span>

                  {hasDatesheet ? (
                    <button
                      type="button"
                      onClick={() => onDownloadDatesheet?.(exam)}
                      disabled={downloadingExamId === exam.id}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-200 transition disabled:opacity-50"
                    >
                      <Download className="w-3 h-3" />
                      {downloadingExamId === exam.id ? 'Downloading...' : 'Download Datesheet'}
                    </button>
                  ) : (
                    <span className="text-[11px] text-slate-400 italic px-1">
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
