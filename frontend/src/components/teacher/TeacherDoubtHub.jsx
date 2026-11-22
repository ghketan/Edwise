import React, { useState, useMemo } from 'react';
import { HelpCircle, CheckCircle2, Clock, Send, AlertCircle } from 'lucide-react';
import { doubtsApi } from '../../api/doubts';
import { extractApiError, formatDateOnly } from '../../utils/format';

export default function TeacherDoubtHub({
  doubts = [],
  subjects = [],
  onAnswered,
}) {
  const [statusFilter, setStatusFilter] = useState('all');
  const [subjectFilter, setSubjectFilter] = useState('');
  const [drafts, setDrafts] = useState({});
  const [submittingId, setSubmittingId] = useState(null);
  const [cardErrors, setCardErrors] = useState({});

  const filteredDoubts = useMemo(() => {
    return doubts.filter((d) => {
      if (statusFilter === 'pending' && d.is_resolved) return false;
      if (statusFilter === 'answered' && !d.is_resolved) return false;
      if (subjectFilter && String(d.subject_id) !== String(subjectFilter)) return false;
      return true;
    });
  }, [doubts, statusFilter, subjectFilter]);

  const handleDraftChange = (doubtId, val) => {
    setDrafts((prev) => ({ ...prev, [doubtId]: val }));
    if (cardErrors[doubtId]) {
      setCardErrors((prev) => ({ ...prev, [doubtId]: '' }));
    }
  };

  const handleAnswerSubmit = async (e, doubtId) => {
    e.preventDefault();
    const answerText = (drafts[doubtId] || '').trim();
    if (!answerText) {
      setCardErrors((prev) => ({
        ...prev,
        [doubtId]: 'Answer cannot be empty.',
      }));
      return;
    }

    setSubmittingId(doubtId);
    setCardErrors((prev) => ({ ...prev, [doubtId]: '' }));
    try {
      const updated = await doubtsApi.answerDoubt(doubtId, answerText);
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[doubtId];
        return next;
      });
      onAnswered?.(updated);
    } catch (err) {
      setCardErrors((prev) => ({
        ...prev,
        [doubtId]: extractApiError(err, 'Failed to submit answer.'),
      }));
    } finally {
      setSubmittingId(null);
    }
  };

  return (
    <section className="glass-panel rounded-2xl p-5 shadow-sm min-w-0">
      <hgroup className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <span className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-primary-container text-white flex items-center justify-center shadow-sm">
            <HelpCircle className="w-4 h-4 shrink-0" />
          </div>
          <h2 className="font-bold text-sm text-on-surface">
            Student Doubt Resolution Hub
          </h2>
        </span>

        <span className="flex flex-wrap items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs px-3 py-1.5 rounded-xl border border-glass-border bg-surface-container-low text-on-surface font-semibold focus:outline-none focus:ring-2 focus:ring-primary-container"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="answered">Answered</option>
          </select>

          <select
            value={subjectFilter}
            onChange={(e) => setSubjectFilter(e.target.value)}
            className="text-xs px-3 py-1.5 rounded-xl border border-glass-border bg-surface-container-low text-on-surface font-semibold focus:outline-none focus:ring-2 focus:ring-primary-container"
          >
            <option value="">All Subjects</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </span>
      </hgroup>

      {filteredDoubts.length === 0 ? (
        <div className="py-8 text-center text-xs text-outline border border-dashed border-slate-200 rounded-xl font-mono">
          No student doubts matching the selected filters.
        </div>
      ) : (
        <div className="space-y-4 max-h-[32rem] overflow-y-auto pr-1">
          {filteredDoubts.map((doubt) => (
            <div
              key={doubt.id}
              className="p-4 rounded-xl border border-glass-border bg-surface-container-lowest/80 shadow-xs space-y-3 hover:border-slate-300 transition-all min-w-0 break-words"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-bold text-xs text-on-surface">
                    {doubt.student_name || `Student #${doubt.student_id}`}
                  </span>
                  <span className="text-[10px] text-outline font-mono">
                    ({doubt.student_admission_number || `ID ${doubt.student_id}`})
                  </span>
                  <span className="text-[11px] font-bold text-primary px-2 py-0.5 rounded-md bg-surface-container-high font-mono">
                    {doubt.subject_name || `Subject #${doubt.subject_id}`}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full font-mono ${
                      doubt.is_resolved
                        ? 'bg-status-emerald-bg text-status-emerald-text border border-emerald-200'
                        : 'bg-status-amber-bg text-status-amber-text border border-amber-200'
                    }`}
                  >
                    {doubt.is_resolved ? 'Resolved' : 'Pending'}
                  </span>
                  <span className="text-[10px] text-outline font-mono">
                    {formatDateOnly(doubt.created_at)}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-surface-container-low text-xs text-on-surface leading-relaxed break-words font-medium">
                <span className="font-bold text-outline">Question: </span>
                {doubt.question}
              </div>

              {doubt.is_resolved && doubt.answer ? (
                <div className="p-3.5 rounded-xl bg-status-emerald-bg/60 border border-emerald-200 text-xs text-emerald-950 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-[11px] text-status-emerald-text">
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                    <span>Answered by {doubt.answered_by_name || 'Faculty'}</span>
                    {doubt.answered_at && (
                      <span className="text-outline font-mono font-normal">
                        • {formatDateOnly(doubt.answered_at)}
                      </span>
                    )}
                  </div>
                  <p className="leading-relaxed break-words font-medium">{doubt.answer}</p>
                </div>
              ) : (
                <form
                  onSubmit={(e) => handleAnswerSubmit(e, doubt.id)}
                  className="space-y-2 pt-1"
                >
                  <label htmlFor={`answer-input-${doubt.id}`} className="sr-only">
                    Answer Question
                  </label>
                  <textarea
                    id={`answer-input-${doubt.id}`}
                    rows={2}
                    value={drafts[doubt.id] ?? ''}
                    onChange={(e) => handleDraftChange(doubt.id, e.target.value)}
                    placeholder="Provide a clear, detailed pedagogical explanation..."
                    className="w-full text-xs rounded-xl border border-glass-border bg-surface-container-lowest p-3 focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container"
                  />

                  {cardErrors[doubt.id] && (
                    <div className="p-2 rounded-lg bg-status-rose-bg text-status-rose-text text-xs flex items-center gap-1.5 font-medium">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{cardErrors[doubt.id]}</span>
                    </div>
                  )}

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={submittingId === doubt.id}
                      className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-primary-container hover:opacity-95 rounded-xl shadow-md shadow-indigo-200 transition-all active:scale-[0.98] disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{submittingId === doubt.id ? 'Submitting...' : 'Submit Answer'}</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
