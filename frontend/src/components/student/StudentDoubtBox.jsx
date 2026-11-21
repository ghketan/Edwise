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
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm min-w-0">
      <hgroup className="flex items-center gap-2 mb-4">
        <HelpCircle className="w-4 h-4 text-indigo-600 shrink-0" />
        <h2 className="font-semibold text-sm text-slate-900">Doubt Clearing Box</h2>
      </hgroup>

      {/* First in DOM: Always-visible Ask a Doubt Form */}
      <form
        onSubmit={handleSubmit}
        className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 mb-5 space-y-3"
      >
        <hgroup className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <span className="text-xs font-semibold text-slate-700">Ask a Doubt</span>
          <span className="flex items-center gap-2">
            <label className="text-[11px] font-medium text-slate-500">Subject:</label>
            <select
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {subjects.length === 0 ? (
                <option value="">No subjects</option>
              ) : (
                subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))
              )}
            </select>
          </span>
        </hgroup>

        <textarea
          rows="2"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about a subject or exam..."
          className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />

        {formMsg.text && (
          <div
            className={`p-2 rounded-lg text-xs flex items-center gap-1.5 ${
              formMsg.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}
          >
            {formMsg.type === 'success' ? (
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            )}
            <span className="break-words min-w-0">{formMsg.text}</span>
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting || subjects.length === 0}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            {submitting ? 'Submitting...' : 'Submit Doubt'}
          </button>
        </div>
      </form>

      {/* Second in DOM: My Doubts Header + Subject Filter */}
      <hgroup className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h3 className="text-xs font-semibold text-slate-700">
          My Doubts ({filteredDoubts.length})
        </h3>
        <select
          value={filterSubjectId}
          onChange={(e) => setFilterSubjectId(e.target.value)}
          className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Subjects</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </hgroup>

      {filteredDoubts.length === 0 ? (
        <div className="py-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
          No doubts found for this filter.
        </div>
      ) : (
        <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
          {filteredDoubts.map((d) => (
            <div
              key={d.id}
              className="p-3.5 rounded-lg border border-slate-200/80 bg-slate-50/40 min-w-0 break-words"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">
                  {d.subject_name || 'Subject'}
                </span>
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
                {d.question}
              </p>

              {d.is_resolved && d.answer && (
                <div className="mt-2.5 p-2.5 rounded-lg bg-emerald-50 border-l-4 border-emerald-500 text-xs text-emerald-950 break-words">
                  <div className="font-semibold text-[11px] text-emerald-800 mb-0.5">
                    Faculty Response ({d.answered_by_name || 'Faculty'})
                    {d.answered_at ? ` • ${formatDateOnly(d.answered_at)}` : ''}
                  </div>
                  <p className="leading-relaxed break-words">{d.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
