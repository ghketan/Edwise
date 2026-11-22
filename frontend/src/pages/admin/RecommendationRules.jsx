import React, { useState, useEffect } from 'react';
import { recommendationApi } from '../../api/recommendations';
import TruthBanner from '../../components/TruthBanner';
import { extractApiError } from '../../utils/format';
import {
  Sparkles,
  Plus,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  ShieldAlert,
  Sliders,
  HelpCircle,
} from 'lucide-react';

export default function RecommendationRules() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState({ text: '', type: '' });

  // Create Modal
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    rule_code: '',
    title: '',
    indicator: 'attendance_rate',
    operator: '<',
    threshold_value: 75.0,
    severity: 'medium',
    template_message: 'Student attendance is {value}%, below the required standard of 75%.',
    is_active: true,
  });

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    setLoading(true);
    setMsg({ text: '', type: '' });
    try {
      const data = await recommendationApi.getRules();
      setRules(Array.isArray(data) ? data : []);
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to load recommendation rules.'), type: 'error' });
      setRules([]);
    } finally {
      setLoading(false);
    }
  };

  const handleIndicatorChange = (ind) => {
    let defaultMsg = '';
    let defaultOp = '<';
    let defaultThresh = 75.0;

    if (ind === 'attendance_rate') {
      defaultMsg = 'Student attendance is {value}%, below the required standard of 75%.';
      defaultOp = '<';
      defaultThresh = 75.0;
    } else if (ind === 'score_drop') {
      defaultMsg = 'Exam performance dropped by {value} percentage points between consecutive assessments.';
      defaultOp = '>=';
      defaultThresh = 15.0;
    } else if (ind === 'missing_assignments') {
      defaultMsg = 'Student has {value} unsubmitted or late assignments in this term.';
      defaultOp = '>=';
      defaultThresh = 2.0;
    }

    setFormData({
      ...formData,
      indicator: ind,
      operator: defaultOp,
      threshold_value: defaultThresh,
      template_message: defaultMsg,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setMsg({ text: '', type: '' });

    try {
      const payload = {
        rule_code: formData.rule_code.trim().toUpperCase(),
        title: formData.title.trim(),
        indicator: formData.indicator,
        operator: formData.operator,
        threshold_value: parseFloat(formData.threshold_value),
        severity: formData.severity,
        template_message: formData.template_message.trim(),
        is_active: formData.is_active,
      };

      const created = await recommendationApi.createRule(payload);
      setMsg({ text: `Rule '${created.rule_code}' configured successfully!`, type: 'success' });
      setShowModal(false);
      setFormData({
        rule_code: '',
        title: '',
        indicator: 'attendance_rate',
        operator: '<',
        threshold_value: 75.0,
        severity: 'medium',
        template_message: 'Student attendance is {value}%, below the required standard of 75%.',
        is_active: true,
      });
      loadRules();
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to author recommendation rule.'), type: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Early Intervention Recommendation Rules
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Rule-based indicator thresholds triggering traceable teacher intervention cards (D-008, R-012, C-02).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadRules}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition"
          >
            <Plus className="w-3.5 h-3.5" /> Author New Rule
          </button>
        </div>
      </div>

      {msg.text && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
            msg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {msg.type === 'success' ? (
            <CheckCircle className="w-4 h-4 shrink-0 text-emerald-600" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          )}
          <span>{msg.text}</span>
        </div>
      )}

      {/* Transparency Banner */}
      <TruthBanner
        modelVersion="RuleEngine-v1.0"
        dataSource="Deterministic Indicator Rule Matrix (R-012)"
        isSynthetic={false}
      />

      {/* Rules Grid */}
      {loading ? (
        <div className="py-12 text-center text-xs text-slate-400">Loading active recommendation rules...</div>
      ) : rules.length === 0 ? (
        <div className="py-12 text-center text-xs text-slate-400 bg-white rounded-xl border border-slate-200 p-8">
          No recommendation rules configured. Click "Author New Rule" above to create an indicator trigger.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {rules.map((rule) => {
            const sevColor =
              rule.severity === 'high'
                ? 'bg-rose-100 text-rose-800 border-rose-200'
                : rule.severity === 'medium'
                ? 'bg-amber-100 text-amber-800 border-amber-200'
                : 'bg-sky-100 text-sky-800 border-sky-200';

            return (
              <div
                key={rule.id}
                className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[11px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                      {rule.rule_code}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${sevColor}`}
                    >
                      {rule.severity} Priority
                    </span>
                  </div>

                  <h3 className="font-bold text-sm text-slate-900 mt-1">{rule.title}</h3>

                  <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200/60 font-mono text-xs">
                    <span className="text-slate-400">Trigger: </span>
                    <span className="font-semibold text-slate-800">
                      {rule.indicator} {rule.operator} {rule.threshold_value}
                    </span>
                  </div>

                  <div className="mt-3 text-xs text-slate-600 leading-relaxed italic bg-indigo-50/40 p-2.5 rounded-lg border border-indigo-100/50">
                    "{rule.template_message}"
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                  <span className="flex items-center gap-1">
                    <span
                      className={`w-2 h-2 rounded-full ${rule.is_active ? 'bg-emerald-500' : 'bg-slate-300'}`}
                    />
                    {rule.is_active ? 'Active Trigger' : 'Inactive'}
                  </span>
                  <span className="text-slate-400 font-mono">ID #{rule.id}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Author New Rule Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900">Author Recommendation Indicator Rule</h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3.5 mt-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Rule Code <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. REC-ATT-75"
                    value={formData.rule_code}
                    onChange={(e) => setFormData({ ...formData, rule_code: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Severity Priority <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.severity}
                    onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Rule Title <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Chronic Attendance Warning"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Tracked Indicator <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.indicator}
                    onChange={(e) => handleIndicatorChange(e.target.value)}
                    className="w-full px-2.5 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none font-mono"
                  >
                    <option value="attendance_rate">attendance_rate</option>
                    <option value="score_drop">score_drop</option>
                    <option value="missing_assignments">missing_assignments</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Operator <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.operator}
                    onChange={(e) => setFormData({ ...formData, operator: e.target.value })}
                    className="w-full px-2.5 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none font-mono"
                  >
                    <option value="<">&lt; (Less than)</option>
                    <option value="<=">&lt;= (Less or equal)</option>
                    <option value=">">&gt; (Greater than)</option>
                    <option value=">=">&gt;= (Greater or equal)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Threshold Value <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={formData.threshold_value}
                    onChange={(e) => setFormData({ ...formData, threshold_value: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Recommendation Message Template <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  value={formData.template_message}
                  onChange={(e) => setFormData({ ...formData, template_message: e.target.value })}
                  placeholder="Use {value} to interpolate the student's actual trigger metric"
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-[11px] text-slate-400">
                  Tip: Include <code className="bg-slate-100 px-1 py-0.5 rounded font-mono text-slate-700">{'{value}'}</code> in the message to interpolate the student's actual recorded metric.
                </span>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="rule_is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-0"
                />
                <label htmlFor="rule_is_active" className="text-slate-700 font-medium cursor-pointer">
                  Activate rule immediately upon saving
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {submitting ? 'Saving Rule...' : 'Save Indicator Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

