import React, { useState, useEffect } from 'react';
import { Sparkles, X, BookOpen, Clock, AlertCircle } from 'lucide-react';
import { analyticsApi } from '../../api/analytics';
import { extractApiError } from '../../utils/format';

export default function AiLessonPlanModal({
  isOpen = false,
  onClose,
  scopedClasses = [],
  sessionId,
}) {
  const [selectedClassId, setSelectedClassId] = useState('');
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    setPlan(null);
    setErrorMsg('');
  }, [sessionId]);

  useEffect(() => {
    if (isOpen) {
      setErrorMsg('');
      if (scopedClasses.length > 0) {
        setSelectedClassId((prev) =>
          scopedClasses.some((c) => String(c.id) === String(prev))
            ? prev
            : String(scopedClasses[0].id)
        );
      } else {
        setSelectedClassId('');
      }
    }
  }, [isOpen, scopedClasses]);

  const selectedClassObj = scopedClasses.find(
    (c) => String(c.id) === String(selectedClassId)
  );

  if (!isOpen) return null;

  const handleGenerate = async () => {
    if (!selectedClassId || !sessionId) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await analyticsApi.getAiLessonPlan(Number(selectedClassId), sessionId);
      setPlan(res);
    } catch (err) {
      setErrorMsg(extractApiError(err, 'Failed to generate AI remedial lesson plan.'));
    } finally {
      setLoading(false);
    }
  };

  const statusStyle =
    plan?.performance_status === 'Challenging'
      ? 'bg-rose-100 text-rose-800 border-rose-200'
      : plan?.performance_status === 'Moderate'
      ? 'bg-amber-100 text-amber-800 border-amber-200'
      : 'bg-emerald-100 text-emerald-800 border-emerald-200';

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xl w-full max-w-xl p-6 space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex flex-wrap items-center gap-2">
                <span>AI Remedial Lesson Plan Generator</span>
                {selectedClassObj && (
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                    Selected Class: {selectedClassObj.name}
                  </span>
                )}
              </h2>
              <p className="text-[11px] text-slate-500">
                Identifies weakest class subject and builds a 3-day remediation schedule
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-end gap-3">
          <div className="flex-1">
            <label className="block text-[11px] font-semibold text-slate-500 uppercase mb-1">
              Target Class
            </label>
            <select
              value={selectedClassId}
              onChange={(e) => {
                setSelectedClassId(e.target.value);
                setPlan(null);
              }}
              className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {scopedClasses.length === 0 ? (
                <option value="">No assigned classes</option>
              ) : (
                scopedClasses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={!selectedClassId || !sessionId || loading}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {loading ? 'Generating...' : 'Generate Plan'}
          </button>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {plan && (
          <div className="space-y-4 pt-2">
            <div className="p-4 rounded-xl bg-indigo-50/60 border border-indigo-100 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-indigo-600" />
                  <span className="text-xs font-bold text-slate-900">
                    Focus Subject: {plan.focus_subject}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-indigo-700">
                    {Number(plan.avg_score).toFixed(1)}% Avg
                  </span>
                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${statusStyle}`}
                  >
                    {plan.performance_status}
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed">
                {plan.key_recommendation}
              </p>
            </div>

            <div>
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2.5">
                3-Day Weekly Remediation Schedule
              </h3>
              <div className="space-y-2">
                {(plan.weekly_schedule || []).map((item, idx) => (
                  <div
                    key={`${item.day}-${idx}`}
                    className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <span className="text-xs font-bold text-indigo-700">{item.day}</span>
                      <p className="text-xs text-slate-700 mt-0.5">{item.topic}</p>
                    </div>
                    <span className="inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2.5 py-1 rounded-full bg-white border border-slate-200 text-slate-700 shrink-0 self-start sm:self-center">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {item.hours} hrs
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
