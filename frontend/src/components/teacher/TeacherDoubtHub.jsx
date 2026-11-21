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
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm min-w-0">
      <hgroup className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <span className="flex items-center gap-2 min-w-0">
          <HelpCircle className="w-4 h-4 text-indigo-600 shrink-0" />
          <h2 className="font-semibold text-sm text-slate-900">
            Student Doubt Resolution Hub
          </h2>
        </span>

        <span className="flex flex-wrap items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="answered">Answered</option>
          </select>

          <select
            value={subjectFilter}
            onChange={(e) => setSubjectFilter(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
        <div className="py-8 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
          No doubts found matching the selected filters.
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {filteredDoubts.map((d) => (
            <div
              key={d.id}
              className="p-4 rounded-xl border border-slate-200 bg-slate-50/40 space-y-2.5 min-w-0 break-words"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-semibold text-slate-900">
                    {d.student_name || 'Student'}
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">
                    ({d.student_roll || 'N/A'})
                  </span>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">
                    {d.subject_name || 'Subject'}
                  </span>
                </div>

                <span
                  className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                    d.is_resolved
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {d.is_resolved ? (
                    <>
                      <CheckCircle2 className="w-3 h-3" /> Answered
                    </>
                  ) : (
                    <>
                      <Clock className="w-3 h-3" /> Pending
                    </>
                  )}
                </span>
              </div>

              <p className="text-xs font-medium text-slate-900 break-words">
                Q: {d.question}
              </p>

              {d.is_resolved ? (
                <div className="p-2.5 rounded-lg bg-emerald-50 border-l-4 border-emerald-500 text-xs text-emerald-950 break-words">
                  <div className="font-semibold text-[11px] text-emerald-800 mb-0.5">
                    Response by {d.answered_by_name || 'Faculty'}
                    {d.answered_at ? ` • ${formatDateOnly(d.answered_at)}` : ''}
                  </div>
                  <p className="leading-relaxed break-words">{d.answer}</p>
                </div>
              ) : (
                <form
                  onSubmit={(e) => handleAnswerSubmit(e, d.id)}
                  className="space-y-2 pt-1"
                >
                  <textarea
                    rows="2"
                    value={drafts[d.id] || ''}
                    onChange={(e) => handleDraftChange(d.id, e.target.value)}
                    placeholder="Write your reply to resolve this doubt..."
                    className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  {cardErrors[d.id] && (
                    <div className="p-2 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{cardErrors[d.id]}</span>
                    </div>
                  )}
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={submittingId === d.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50"
                    >
                      <Send className="w-3 h-3" />
                      {submittingId === d.id ? 'Sending...' : 'Submit Answer'}
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
