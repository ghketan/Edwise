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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-md p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full border border-glass-border p-6 overflow-hidden">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2 text-primary font-bold">
            <div className="w-8 h-8 rounded-xl bg-status-sky-bg text-status-sky-text flex items-center justify-center">
              <ShieldAlert className="w-4 h-4 text-primary" />
            </div>
            <h3 className="font-bold text-sm text-on-surface">{title}</h3>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="text-outline hover:text-on-surface rounded-lg p-1 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4">
          <p className="text-xs text-on-surface-variant mb-3 leading-relaxed">{message}</p>
          <label className="block text-xs font-semibold text-on-surface mb-1">
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
            className="w-full text-xs rounded-xl border border-slate-300 p-3 focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container transition-all"
            autoFocus
          />
          {error && <p className="text-[11px] text-status-rose-text font-medium mt-1">{error}</p>}

          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-xs font-semibold text-on-surface-variant hover:bg-surface-container-high rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-white bg-primary-container hover:opacity-95 rounded-xl shadow-md shadow-indigo-200 transition-all active:scale-[0.98]"
            >
              Confirm & Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
