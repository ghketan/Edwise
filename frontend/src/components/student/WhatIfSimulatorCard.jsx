import React, { useState, useEffect, useRef } from 'react';
import { Sliders, Sparkles, Clock } from 'lucide-react';
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
      ? 'bg-rose-100 text-rose-800 border-rose-200'
      : prediction?.risk_level === 'Medium Risk'
      ? 'bg-amber-100 text-amber-800 border-amber-200'
      : 'bg-emerald-100 text-emerald-800 border-emerald-200';

  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <Sliders className="w-4 h-4 text-indigo-600 shrink-0" />
          <h2 className="font-semibold text-sm text-slate-900">
            Interactive What-If AI Score Predictor
          </h2>
        </div>

        <select
          value={subjectName}
          onChange={(e) => setSubjectName(e.target.value)}
          className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/70">
          <div className="flex justify-between text-xs font-medium text-slate-700 mb-1.5">
            <label htmlFor="sim-unit-test">Unit Test Score</label>
            <span className="font-mono font-bold text-indigo-600">{unitTest}%</span>
          </div>
          <input
            id="sim-unit-test"
            type="range"
            min="0"
            max="100"
            step="1"
            value={unitTest}
            onChange={(e) => setUnitTest(Number(e.target.value))}
            className="w-full accent-indigo-600 cursor-pointer"
          />
        </div>

        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/70">
          <div className="flex justify-between text-xs font-medium text-slate-700 mb-1.5">
            <label htmlFor="sim-mid-term">Mid-Term Score</label>
            <span className="font-mono font-bold text-indigo-600">{midTerm}%</span>
          </div>
          <input
            id="sim-mid-term"
            type="range"
            min="0"
            max="100"
            step="1"
            value={midTerm}
            onChange={(e) => setMidTerm(Number(e.target.value))}
            className="w-full accent-indigo-600 cursor-pointer"
          />
        </div>

        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/70">
          <div className="flex justify-between text-xs font-medium text-slate-700 mb-1.5">
            <label htmlFor="sim-assignment">Assignment Score</label>
            <span className="font-mono font-bold text-indigo-600">{assignment}%</span>
          </div>
          <input
            id="sim-assignment"
            type="range"
            min="0"
            max="100"
            step="1"
            value={assignment}
            onChange={(e) => setAssignment(Number(e.target.value))}
            className="w-full accent-indigo-600 cursor-pointer"
          />
        </div>

        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/70">
          <div className="flex justify-between text-xs font-medium text-slate-700 mb-1.5">
            <label htmlFor="sim-attendance">Attendance %</label>
            <span className="font-mono font-bold text-emerald-600">{attendance}%</span>
          </div>
          <input
            id="sim-attendance"
            type="range"
            min="0"
            max="100"
            step="1"
            value={attendance}
            onChange={(e) => setAttendance(Number(e.target.value))}
            className="w-full accent-emerald-600 cursor-pointer"
          />
        </div>
      </div>

      {errorMsg && (
        <div className="mb-3 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800">
          {errorMsg}
        </div>
      )}

      {prediction ? (
        <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50/70 to-slate-50 border border-indigo-100 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Simulated Forecast ({prediction.subject_name})
              </div>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-2xl font-bold text-indigo-700 font-mono">
                  {Number(prediction.active_prediction).toFixed(1)}%
                </span>
                <span className="text-[11px] font-medium text-slate-500">
                  {loading ? 'Updating...' : `via ${prediction.active_model}`}
                </span>
              </div>
            </div>

            <span className={`text-xs font-bold px-3 py-1 rounded-full border ${riskBadgeStyle}`}>
              {prediction.risk_level}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
            <div className="p-2.5 rounded-lg bg-white border border-slate-200/70 flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-600 shrink-0" />
              <div>
                <div className="text-[10px] text-slate-400 font-semibold uppercase">
                  Recommended Study Hours
                </div>
                <div className="font-bold text-slate-900">
                  {prediction.recommended_study_hours} hrs/day
                  {prediction.extra_time_increase > 0 && (
                    <span className="text-amber-600 ml-1">
                      (+{prediction.extra_time_increase}h extra)
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-white border border-slate-200/70 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-600 shrink-0" />
              <div className="min-w-0">
                <div className="text-[10px] text-slate-400 font-semibold uppercase">
                  Active Engine
                </div>
                <div className="font-semibold text-slate-800 truncate">
                  {prediction.active_model}
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 text-[11px]">
            <span className="px-2 py-1 rounded bg-white border border-slate-200 text-slate-600 font-mono">
              Linear: {Number(prediction.linear_prediction).toFixed(1)}%
            </span>
            <span className="px-2 py-1 rounded bg-white border border-slate-200 text-slate-600 font-mono">
              Random Forest: {Number(prediction.rf_prediction).toFixed(1)}%
            </span>
            <span className="px-2 py-1 rounded bg-white border border-slate-200 text-slate-600 font-mono">
              XGBoost: {Number(prediction.xgb_prediction).toFixed(1)}%
            </span>
          </div>
        </div>
      ) : (
        <div className="py-6 text-center text-xs text-slate-400">
          Running live simulation...
        </div>
      )}
    </section>
  );
}
