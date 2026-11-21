import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';

export default function TruthBanner({
  modelVersion = 'v1.0',
  dataSource = 'synthetic-baseline',
  isSynthetic = true,
  className = '',
}) {
  return (
    <div
      className={`rounded-lg border border-amber-200 bg-amber-50/80 p-3.5 text-amber-900 shadow-sm ${className}`}
    >
      <div className="flex items-start gap-3">
        <Info className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
        <div className="text-xs leading-relaxed">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-semibold uppercase tracking-wider text-[11px] text-amber-800">
              Transparency & Evaluation Notice (R-015, C-001)
            </span>
            {isSynthetic && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-amber-200 text-amber-800">
                Synthetic Demo Model
              </span>
            )}
            <span className="text-amber-700">Model: {modelVersion}</span>
            <span className="text-amber-700">Source: {dataSource}</span>
          </div>
          <p className="text-amber-800">
            Predictions are <strong>demonstration estimates</strong> generated from historical data patterns. They do <strong>not</strong> represent a definitive verdict, cause, diagnosis, or automated academic decision.
          </p>
        </div>
      </div>
    </div>
  );
}

