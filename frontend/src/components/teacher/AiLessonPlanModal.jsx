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
      ? 'bg-status-rose-bg text-status-rose-text border-rose-300'
      : plan?.performance_status === 'Moderate'
      ? 'bg-status-amber-bg text-status-amber-text border-amber-300'
      : 'bg-status-emerald-bg text-status-emerald-text border-emerald-300';

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl border border-glass-border shadow-2xl w-full max-w-xl p-6 space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-status-sky-bg text-secondary flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-on-surface flex flex-wrap items-center gap-2">
                <span>AI Remedial Lesson Plan Generator</span>
                {selectedClassObj && (
                  <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-surface-container-high text-primary border border-glass-border font-mono">
                    Selected Class: {selectedClassObj.name}
                  </span>
                )}
              </h2>
              <p className="text-[11px] text-on-surface-variant font-medium">
                Automated curriculum recovery based on student performance bottlenecks
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-outline hover:text-on-surface transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Class Selection Form */}
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-on-surface mb-1">
              Select Target Class
            </label>
            <select
              value={selectedClassId}
              onChange={(e) => {
                setSelectedClassId(e.target.value);
                setPlan(null);
                setErrorMsg('');
              }}
              className="w-full text-xs px-3 py-2 rounded-xl border border-glass-border bg-surface-container-low text-on-surface font-semibold focus:outline-none focus:ring-2 focus:ring-primary-container"
            >
              {scopedClasses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || !selectedClassId}
            className="w-full py-2.5 px-4 text-xs font-bold text-white bg-primary-container hover:opacity-95 rounded-xl shadow-md shadow-indigo-200 flex items-center justify-center gap-2 transition-all active:scale-[0.98] disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            <span>{loading ? 'Synthesizing Lesson Plan...' : 'Generate 4-Week Remedial Plan'}</span>
          </button>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-xl bg-status-rose-bg border border-rose-200 text-xs text-status-rose-text flex items-center gap-2 font-medium">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Generated Plan Output */}
        {plan && (
          <div className="space-y-4 pt-2 border-t border-slate-100">
            <div className="p-4 rounded-xl bg-surface-container-low/80 border border-glass-border space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold text-on-surface flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-primary" />
                  Target Focus Subject: {plan.lowest_subject_name}
                </span>
                <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border font-mono ${statusStyle}`}>
                  {plan.performance_status}
                </span>
              </div>
              <p className="text-xs text-on-surface-variant leading-relaxed font-medium">
                {plan.pedagogical_focus}
              </p>
            </div>

            {/* Weekly Schedule */}
            <div className="space-y-2.5">
              <h3 className="text-xs font-bold text-on-surface uppercase tracking-wider text-outline">
                Weekly Remedial Curriculum
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {plan.suggested_schedule?.map((item) => (
                  <div
                    key={item.week}
                    className="p-3 rounded-xl border border-glass-border bg-surface-container-lowest/80 space-y-1 shadow-xs"
                  >
                    <div className="flex items-center justify-between text-xs font-bold text-primary font-mono">
                      <span>Week {item.week}</span>
                      <span className="text-[10px] text-outline font-sans flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {item.hours_per_week} hrs/wk
                      </span>
                    </div>
                    <div className="font-semibold text-xs text-on-surface">{item.topic}</div>
                    <p className="text-[11px] text-on-surface-variant font-medium">{item.activities}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
