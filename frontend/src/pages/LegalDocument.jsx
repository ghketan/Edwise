import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ShieldCheck, FileText, ArrowLeft, Printer, RefreshCw, CheckCircle2 } from 'lucide-react';
import { legalApi } from '../api/legal';
import { extractApiError } from '../utils/format';

export default function LegalDocument({ defaultType = null }) {
  const location = useLocation();
  const docType = defaultType || (location.pathname.includes('privacy') ? 'privacy' : 'terms');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const isPrivacy = docType === 'privacy' || docType === 'privacy-policy';
  const Icon = isPrivacy ? ShieldCheck : FileText;

  useEffect(() => {
    setLoading(true);
    setError('');
    legalApi
      .getDocument(docType)
      .then(setData)
      .catch((err) => setError(extractApiError(err, 'Failed to retrieve legal document.')))
      .finally(() => setLoading(false));
  }, [docType]);

  return (
    <div className="min-h-screen blackboard-bg chalk-grid text-slate-100 font-sans flex flex-col justify-between p-4 sm:p-8">
      {/* Top Bar */}
      <header className="max-w-4xl w-full mx-auto flex items-center justify-between mb-8">
        <Link
          to="/login"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900/80 dark:bg-slate-900/80 bg-white/90 border border-slate-700/80 dark:border-slate-700/80 border-slate-200 text-xs font-semibold text-slate-200 dark:text-slate-200 text-slate-800 shadow-sm hover:border-indigo-400 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Login</span>
        </Link>

        <div className="flex items-center gap-2">
          <Link
            to="/privacy"
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              isPrivacy
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Privacy Policy
          </Link>
          <Link
            to="/terms"
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              !isPrivacy
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Terms of Service
          </Link>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-4xl w-full mx-auto my-auto glass-surface-canvas rounded-3xl shadow-glass p-6 sm:p-10 text-slate-800 relative overflow-hidden">
        {loading && (
          <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-500">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
            <p className="text-sm font-medium">Loading verified document from EDWISE backend...</p>
          </div>
        )}

        {error && (
          <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm">
            <p className="font-semibold">{error}</p>
          </div>
        )}

        {data && (
          <div className="space-y-6">
            <div className="flex items-start justify-between gap-4 pb-6 border-b border-slate-200 flex-wrap">
              <div className="flex items-center gap-3">
                <div
                  className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-sm ${
                    isPrivacy
                      ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                      : 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                  }`}
                >
                  <Icon className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                      {isPrivacy ? 'Privacy Policy' : 'Terms of Service'}
                    </h1>
                    <span className="text-xs font-mono uppercase font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                      v{data.version}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 font-medium mt-0.5">
                    {data.jurisdiction} • Last Updated: {data.last_updated}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => window.print()}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-xs cursor-pointer"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print Copy</span>
              </button>
            </div>

            {/* Summary Notice */}
            <div className="p-4 rounded-2xl bg-indigo-50/70 border border-indigo-100 text-xs text-indigo-950 flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
              <div className="leading-relaxed font-medium">{data.summary}</div>
            </div>

            {/* Document Content Sections */}
            <div className="space-y-4">
              {data.sections.map((section, idx) => (
                <div
                  key={idx}
                  className="p-5 rounded-2xl bg-slate-50/70 border border-slate-200/80 shadow-xs space-y-2 hover:border-slate-300 transition"
                >
                  <h2 className="font-bold text-sm text-slate-900 tracking-tight">
                    {section.heading}
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
                    {section.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="max-w-4xl w-full mx-auto text-center text-xs text-slate-400 mt-8">
        <p>Copyright © 2026 EDWISE Analytics Suite. All rights reserved.</p>
      </footer>
    </div>
  );
}
