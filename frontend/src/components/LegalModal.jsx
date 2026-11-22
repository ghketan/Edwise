import React, { useState, useEffect } from 'react';
import { ShieldCheck, FileText, X, Printer, RefreshCw, CheckCircle2 } from 'lucide-react';
import { legalApi } from '../api/legal';
import { extractApiError } from '../utils/format';

export default function LegalModal({ isOpen, docType = 'privacy', onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) {
      setData(null);
      setError('');
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError('');

    legalApi
      .getDocument(docType)
      .then((res) => {
        if (isMounted) setData(res);
      })
      .catch((err) => {
        if (isMounted) setError(extractApiError(err, 'Failed to load document.'));
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, docType]);

  if (!isOpen) return null;

  const isPrivacy = docType === 'privacy' || docType === 'privacy-policy';
  const Icon = isPrivacy ? ShieldCheck : FileText;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/70 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-3xl bg-white dark:bg-[#0c1527] border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden transition-all duration-300">
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-slate-200 dark:border-slate-800/80 flex items-center justify-between bg-slate-50/80 dark:bg-slate-900/50 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div
              className={`w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-sm ${
                isPrivacy
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/60'
                  : 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800/60'
              }`}
            >
              <Icon className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white tracking-tight truncate">
                  {isPrivacy ? 'Privacy Policy' : 'Terms of Service'}
                </h2>
                {data?.version && (
                  <span className="text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
                    v{data.version}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium truncate">
                {data?.jurisdiction || 'Institutional Regulatory Compliance'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800/80 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5 text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
          {loading && (
            <div className="py-16 flex flex-col items-center justify-center gap-3 text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin text-indigo-600 dark:text-indigo-400" />
              <p className="text-xs font-medium">Fetching verified terms from institutional backend...</p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-rose-800 dark:text-rose-200 text-xs">
              <p className="font-semibold">{error}</p>
              <button
                type="button"
                onClick={() => {
                  setLoading(true);
                  setError('');
                  legalApi
                    .getDocument(docType)
                    .then(setData)
                    .catch((err) => setError(extractApiError(err, 'Failed to reload.')))
                    .finally(() => setLoading(false));
                }}
                className="mt-2 text-indigo-600 dark:text-indigo-400 underline font-semibold"
              >
                Click to retry
              </button>
            </div>
          )}

          {data && (
            <>
              {/* Summary Callout Banner */}
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/80 space-y-1.5 shadow-xs">
                <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Institutional Notice • Last Updated: {data.last_updated}</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 font-medium">
                  {data.summary}
                </p>
              </div>

              {/* Sections List */}
              <div className="space-y-4 pt-1">
                {data.sections.map((sec, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl bg-white dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800/60 shadow-xs space-y-1.5 hover:border-slate-200 dark:hover:border-slate-700/60 transition-all"
                  >
                    <h3 className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white tracking-tight">
                      {sec.heading}
                    </h3>
                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
                      {sec.content}
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800/80 bg-slate-50/80 dark:bg-slate-900/50 flex items-center justify-between shrink-0">
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/80 transition-colors cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Document</span>
          </button>

          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all cursor-pointer active:scale-95"
          >
            Acknowledge &amp; Close
          </button>
        </div>
      </div>
    </div>
  );
}
