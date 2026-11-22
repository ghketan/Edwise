import React, { useState, useEffect } from 'react';
import { ShieldAlert, X } from 'lucide-react';

export default function AuditModal({
  isOpen,
  title = 'Reason for Record Change',
  message = 'Academic regulations (R-014) require an audit justification for modifying evaluated marks.',
  onConfirm,
  onCancel,
}) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) {
      setReason('');
      setError('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError('Please provide a descriptive reason for this change.');
      return;
    }
    onConfirm(reason.trim());
    setReason('');
    setError('');
  };

  const handleClose = () => {
    setReason('');
    setError('');
    onCancel();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-md p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-md w-full border border-glass-border dark:border-slate-800 p-6 overflow-hidden">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2 text-primary dark:text-indigo-400 font-bold">
            <div className="w-8 h-8 rounded-xl bg-status-sky-bg dark:bg-sky-950/60 text-status-sky-text dark:text-sky-400 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4 text-primary dark:text-indigo-400" />
            </div>
            <h3 className="font-bold text-sm text-on-surface dark:text-slate-100">{title}</h3>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="text-outline hover:text-on-surface dark:text-slate-400 dark:hover:text-slate-200 rounded-lg p-1 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4">
          <p className="text-xs text-on-surface-variant dark:text-slate-300 mb-3 leading-relaxed">{message}</p>
          <label className="block text-xs font-semibold text-on-surface dark:text-slate-200 mb-1">
            Audit Reason <span className="text-status-rose-text">*</span>
          </label>
          <textarea
            rows={3}
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              if (error) setError('');
            }}
            placeholder="e.g., Re-evaluation of question 3 upon student review request"
            className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 p-3 focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container transition-all"
            autoFocus
          />
          {error && <p className="text-[11px] text-status-rose-text font-medium mt-1">{error}</p>}

          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-xs font-semibold text-on-surface-variant dark:text-slate-300 hover:bg-surface-container-high dark:hover:bg-slate-800 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-white bg-primary-container hover:opacity-95 rounded-xl shadow-md shadow-indigo-200 dark:shadow-none transition-all active:scale-[0.98]"
            >
              Confirm & Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
