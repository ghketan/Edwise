import React from 'react';
import { Info, ShieldAlert } from 'lucide-react';

export default function TruthBanner({
  modelVersion = 'v1.0',
  dataSource = 'synthetic-baseline',
  isSynthetic = true,
  className = '',
}) {
  return (
    <div
      className={`rounded-2xl border border-amber-200/80 bg-status-amber-bg/90 backdrop-blur-md p-4 text-amber-900 shadow-sm ${className}`}
    >
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700 shrink-0 mt-0.5">
          <Info className="h-4 w-4" />
        </div>
        <div className="text-xs leading-relaxed">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-bold uppercase tracking-wider text-[11px] text-amber-900">
              Transparency & Evaluation Notice (R-015, C-001)
            </span>
            {isSynthetic && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-200 text-amber-900 border border-amber-300">
                Synthetic Demo Model
              </span>
            )}
            <span className="text-amber-800 font-mono text-[11px]">Model: {modelVersion}</span>
            <span className="text-amber-800 font-mono text-[11px]">Source: {dataSource}</span>
          </div>
          <p className="text-amber-900/90 font-medium">
            Predictions are <strong>demonstration estimates</strong> generated from historical data patterns. They do <strong>not</strong> represent a definitive verdict, cause, diagnosis, or automated academic decision.
          </p>
        </div>
      </div>
    </div>
  );
}
