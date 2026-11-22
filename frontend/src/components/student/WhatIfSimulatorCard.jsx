import React, { useState, useEffect, useRef } from 'react';
import { Sliders, Sparkles, Clock, Activity } from 'lucide-react';
import { mlApi } from '../../api/ml';
import { extractApiError } from '../../utils/format';

export default function WhatIfSimulatorCard({ subjects = [] }) {
  const [subjectName, setSubjectName] = useState('Mathematics');
  const [unitTest, setUnitTest] = useState(75);
  const [midTerm, setMidTerm] = useState(78);
  const [assignment, setAssignment] = useState(82);
  const [attendance, setAttendance] = useState(90);

  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const reqSeqRef = useRef(0);

  useEffect(() => {
    if (subjects.length > 0 && !subjects.some((s) => s.name === subjectName)) {
      setSubjectName(subjects[0].name);
    }
  }, [subjects]);

  useEffect(() => {
    let cancelled = false;
    const payload = {
      unit_test_score: Number(unitTest),
      mid_term_score: Number(midTerm),
      assignment_score: Number(assignment),
      practical_score: Number(assignment),
      previous_exam_score: Math.round((Number(unitTest) + Number(midTerm)) / 2),
      attendance_pct: Number(attendance),
      subject_name: subjectName,
    };

    const timer = setTimeout(async () => {
      if (cancelled) return;
      const seq = ++reqSeqRef.current;
      setLoading(true);
      setErrorMsg('');
      try {
        const res = await mlApi.predictLive(payload);
        if (!cancelled && seq === reqSeqRef.current) {
          setPrediction(res);
        }
      } catch (err) {
        if (!cancelled && seq === reqSeqRef.current) {
          setErrorMsg(extractApiError(err, 'Live simulation failed.'));
        }
      } finally {
        if (!cancelled && seq === reqSeqRef.current) {
          setLoading(false);
        }
      }
    }, 60);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [unitTest, midTerm, assignment, attendance, subjectName]);

  const riskBadgeStyle =
    prediction?.risk_level === 'High Risk'
      ? 'bg-status-rose-bg text-status-rose-text border-rose-300'
      : prediction?.risk_level === 'Medium Risk'
      ? 'bg-status-amber-bg text-status-amber-text border-amber-300'
      : 'bg-status-emerald-bg text-status-emerald-text border-emerald-300';

  return (
    <section className="glass-panel rounded-2xl p-5 shadow-sm min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-primary-container text-white flex items-center justify-center shadow-sm">
            <Sliders className="w-4 h-4 shrink-0" />
          </div>
          <div>
            <h2 className="font-bold text-sm text-on-surface">
              Interactive What-If AI Score Predictor
            </h2>
            <p className="text-[11px] text-on-surface-variant hidden sm:block">
              Simulate performance variables with real-time inference
            </p>
          </div>
        </div>

        <select
          value={subjectName}
          onChange={(e) => setSubjectName(e.target.value)}
          className="text-xs px-3 py-1.5 rounded-xl border border-glass-border bg-surface-container-low text-on-surface font-semibold focus:outline-none focus:ring-2 focus:ring-primary-container"
        >
          {subjects.length === 0 ? (
            <option value="Mathematics">Mathematics</option>
          ) : (
            subjects.map((s) => (
              <option key={s.id} value={s.name}>
                {s.name}
              </option>
            ))
          )}
        </select>
      </div>

      {/* 4 Range Sliders in Exact Order: 0: Unit Test, 1: Mid-Term, 2: Assignment, 3: Attendance */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 mb-5">
        <div className="p-3.5 rounded-xl bg-surface-container-low/70 border border-glass-border">
          <div className="flex justify-between text-xs font-semibold text-on-surface mb-1.5">
            <label htmlFor="sim-unit-test">Unit Test Score</label>
            <span className="font-mono font-bold text-primary">{unitTest}%</span>
          </div>
          <input
            id="sim-unit-test"
            type="range"
            min="0"
            max="100"
            step="1"
            value={unitTest}
            onChange={(e) => setUnitTest(Number(e.target.value))}
            className="w-full accent-primary cursor-pointer"
          />
        </div>

        <div className="p-3.5 rounded-xl bg-surface-container-low/70 border border-glass-border">
          <div className="flex justify-between text-xs font-semibold text-on-surface mb-1.5">
            <label htmlFor="sim-mid-term">Mid-Term Score</label>
            <span className="font-mono font-bold text-primary">{midTerm}%</span>
          </div>
          <input
            id="sim-mid-term"
            type="range"
            min="0"
            max="100"
            step="1"
            value={midTerm}
            onChange={(e) => setMidTerm(Number(e.target.value))}
            className="w-full accent-primary cursor-pointer"
          />
        </div>

        <div className="p-3.5 rounded-xl bg-surface-container-low/70 border border-glass-border">
          <div className="flex justify-between text-xs font-semibold text-on-surface mb-1.5">
            <label htmlFor="sim-assignment">Assignment Score</label>
            <span className="font-mono font-bold text-primary">{assignment}%</span>
          </div>
          <input
            id="sim-assignment"
            type="range"
            min="0"
            max="100"
            step="1"
            value={assignment}
            onChange={(e) => setAssignment(Number(e.target.value))}
            className="w-full accent-primary cursor-pointer"
          />
        </div>

        <div className="p-3.5 rounded-xl bg-surface-container-low/70 border border-glass-border">
          <div className="flex justify-between text-xs font-semibold text-on-surface mb-1.5">
            <label htmlFor="sim-attendance">Attendance %</label>
            <span className="font-mono font-bold text-status-emerald-text">{attendance}%</span>
          </div>
          <input
            id="sim-attendance"
            type="range"
            min="0"
            max="100"
            step="1"
            value={attendance}
            onChange={(e) => setAttendance(Number(e.target.value))}
            className="w-full accent-status-emerald-text cursor-pointer"
          />
        </div>
      </div>

      {errorMsg && (
        <div className="mb-3 p-3 rounded-xl bg-status-rose-bg border border-rose-200 text-xs text-status-rose-text font-medium">
          {errorMsg}
        </div>
      )}

      {prediction ? (
        <div className="p-4 rounded-xl bg-surface-container-lowest/80 border border-glass-border space-y-3 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-outline">
                Simulated Forecast ({prediction.subject_name})
              </div>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-2xl font-bold text-primary font-mono tracking-tight">
                  {Number(prediction.active_prediction).toFixed(1)}%
                </span>
                <span className="text-[11px] font-medium text-outline">
                  {loading ? 'Updating live...' : `via ${prediction.active_model}`}
                </span>
              </div>
            </div>

            <span className={`text-xs font-bold px-3 py-1 rounded-full border ${riskBadgeStyle}`}>
              {prediction.risk_level}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
            <div className="p-2.5 rounded-xl bg-surface-container-low border border-glass-border flex items-center gap-2.5">
              <Clock className="w-4 h-4 text-primary shrink-0" />
              <div>
                <div className="text-[10px] text-outline font-bold uppercase tracking-wider">
                  Recommended Study Hours
                </div>
                <div className="font-bold text-on-surface font-mono">
                  {prediction.recommended_study_hours} hrs/day
                  {prediction.extra_time_increase > 0 && (
                    <span className="text-status-amber-text ml-1">
                      (+{prediction.extra_time_increase}h extra)
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-surface-container-low border border-glass-border flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 text-secondary shrink-0" />
              <div className="min-w-0">
                <div className="text-[10px] text-outline font-bold uppercase tracking-wider">
                  Active Engine
                </div>
                <div className="font-semibold text-on-surface truncate font-mono text-[11px]">
                  {prediction.active_model}
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 text-[11px]">
            <span className="px-2.5 py-1 rounded-lg bg-surface-container-low border border-glass-border text-on-surface-variant font-mono">
              Linear: {Number(prediction.linear_prediction).toFixed(1)}%
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-surface-container-low border border-glass-border text-on-surface-variant font-mono">
              Random Forest: {Number(prediction.rf_prediction).toFixed(1)}%
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-surface-container-low border border-glass-border text-on-surface-variant font-mono">
              XGBoost: {Number(prediction.xgb_prediction).toFixed(1)}%
            </span>
          </div>
        </div>
      ) : (
        <div className="py-6 text-center text-xs text-outline font-mono">
          Running live simulation...
        </div>
      )}
    </section>
  );
}
