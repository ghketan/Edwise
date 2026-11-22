import React, { useState, useEffect, useMemo, useRef } from 'react';
import { HelpCircle, Send, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { doubtsApi } from '../../api/doubts';
import { extractApiError, formatDateOnly } from '../../utils/format';

export default function StudentDoubtBox({
  doubts = [],
  subjects = [],
  sessionId,
  onDoubtCreated,
}) {
  const [subjectId, setSubjectId] = useState('');
  const [question, setQuestion] = useState('');
  const [filterSubjectId, setFilterSubjectId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formMsg, setFormMsg] = useState({ text: '', type: '' });
  const submittingRef = useRef(false);

  useEffect(() => {
    if (subjects.length > 0 && !subjectId) {
      setSubjectId(String(subjects[0].id));
    }
  }, [subjects, subjectId]);

  const filteredDoubts = useMemo(() => {
    if (!filterSubjectId) return doubts;
    return doubts.filter((d) => String(d.subject_id) === String(filterSubjectId));
  }, [doubts, filterSubjectId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submittingRef.current) return;
    setFormMsg({ text: '', type: '' });

    const trimmed = question.trim();
    if (!trimmed) {
      setFormMsg({ text: 'Please enter a question before submitting.', type: 'error' });
      return;
    }
    if (!sessionId || !subjectId) {
      setFormMsg({ text: 'Please select a subject and active session.', type: 'error' });
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    try {
      const created = await doubtsApi.createDoubt({
        session_id: sessionId,
        subject_id: Number(subjectId),
        question: trimmed,
      });
      setQuestion('');
      setFormMsg({ text: 'Your doubt has been submitted to faculty.', type: 'success' });
      onDoubtCreated?.(created);
    } catch (err) {
      setFormMsg({
        text: extractApiError(err, 'Failed to submit doubt.'),
        type: 'error',
      });
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  return (
    <section className="glass-panel rounded-2xl p-5 shadow-sm min-w-0">
      <hgroup className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-xl bg-primary-container text-white flex items-center justify-center shadow-sm">
          <HelpCircle className="w-4 h-4 shrink-0" />
        </div>
        <h2 className="font-bold text-sm text-on-surface">Doubt Clearing Box</h2>
      </hgroup>

      {/* First in DOM: Always-visible Ask a Doubt Form */}
      <form
        onSubmit={handleSubmit}
        className="p-4 rounded-xl bg-surface-container-low/70 border border-glass-border mb-5 space-y-3"
      >
        <hgroup className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <span className="text-xs font-bold text-on-surface">Ask a Doubt</span>
          <div className="flex items-center gap-1.5">
            <label htmlFor="doubt-subject-select" className="text-[11px] text-outline font-semibold">
              Subject:
            </label>
            <select
              id="doubt-subject-select"
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
              className="text-xs px-2.5 py-1 rounded-xl border border-glass-border bg-surface-container-lowest text-on-surface font-semibold focus:outline-none focus:ring-2 focus:ring-primary-container"
            >
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </hgroup>

        <div>
          <label htmlFor="doubt-question-input" className="sr-only">
            Your Question
          </label>
          <textarea
            id="doubt-question-input"
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type your academic question or problem here..."
            className="w-full text-xs rounded-xl border border-glass-border bg-surface-container-lowest p-3 focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container"
          />
        </div>

        {formMsg.text && (
          <div
            className={`p-2.5 rounded-xl text-xs font-medium flex items-center gap-2 ${
              formMsg.type === 'success'
                ? 'bg-status-emerald-bg text-status-emerald-text border border-emerald-200'
                : 'bg-status-rose-bg text-status-rose-text border border-rose-200'
            }`}
          >
            {formMsg.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{formMsg.text}</span>
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-primary-container hover:opacity-95 rounded-xl shadow-md shadow-indigo-200 transition-all active:scale-[0.98] disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{submitting ? 'Submitting...' : 'Submit Doubt'}</span>
          </button>
        </div>
      </form>

      {/* Filter and Doubt History List */}
      <div className="pt-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
          <span className="text-xs font-bold text-on-surface">My Doubts ({filteredDoubts.length})</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-outline font-semibold">Filter:</span>
            <select
              value={filterSubjectId}
              onChange={(e) => setFilterSubjectId(e.target.value)}
              className="text-xs px-2.5 py-1 rounded-xl border border-glass-border bg-surface-container-low text-on-surface font-semibold focus:outline-none focus:ring-2 focus:ring-primary-container"
            >
              <option value="">All Subjects</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {filteredDoubts.length === 0 ? (
          <div className="py-6 text-center text-xs text-outline border border-dashed border-slate-200 rounded-xl font-mono">
            No doubts recorded for this subject filter.
          </div>
        ) : (
          <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
            {filteredDoubts.map((doubt) => (
              <div
                key={doubt.id}
                className="p-3.5 rounded-xl border border-glass-border bg-surface-container-lowest/80 shadow-xs space-y-2 hover:border-slate-300 transition-all min-w-0 break-words"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[11px] font-bold text-primary font-mono">
                    {doubt.subject_name || `Subject #${doubt.subject_id}`}
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full font-mono ${
                        doubt.is_resolved
                          ? 'bg-status-emerald-bg text-status-emerald-text border border-emerald-200'
                          : 'bg-status-amber-bg text-status-amber-text border border-amber-200'
                      }`}
                    >
                      {doubt.is_resolved ? 'Resolved' : 'Pending Review'}
                    </span>
                    <span className="text-[10px] text-outline font-mono">
                      {formatDateOnly(doubt.created_at)}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-on-surface leading-relaxed break-words font-medium">
                  <span className="font-bold text-outline">Q: </span>
                  {doubt.question}
                </p>

                {doubt.is_resolved && doubt.answer && (
                  <div className="p-3 rounded-xl bg-status-emerald-bg/60 border border-emerald-200 text-xs text-emerald-950 space-y-1">
                    <div className="flex items-center gap-1 font-bold text-[11px] text-status-emerald-text">
                      <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                      <span>Answer by {doubt.answered_by_name || 'Faculty'}</span>
                      {doubt.answered_at && (
                        <span className="text-outline font-mono font-normal">
                          • {formatDateOnly(doubt.answered_at)}
                        </span>
                      )}
                    </div>
                    <p className="leading-relaxed break-words font-medium">{doubt.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
