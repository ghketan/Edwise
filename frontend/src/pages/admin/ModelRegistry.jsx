import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import { mlApi } from '../../api/ml';
import TruthBanner from '../../components/TruthBanner';
import { extractApiError, formatUtcTimestamp } from '../../utils/format';
import { RefreshCw, CheckCircle, Layers, Activity, AlertTriangle, Cpu } from 'lucide-react';

function formatMetricVal(val) {
  if (typeof val === 'number') {
    return Number.isFinite(val) ? val.toFixed(3) : '—';
  }
  if (Array.isArray(val)) {
    return `${val.length} items`;
  }
  if (val && typeof val === 'object') {
    const entries = Object.entries(val)
      .filter(([, v]) => typeof v === 'number' && Number.isFinite(v))
      .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v.toFixed(2)}`);
    return entries.length > 0 ? entries.join(' • ') : 'Configured';
  }
  if (val === null || val === undefined) return '—';
  return String(val);
}

function getModelOrderRank(modelName = '') {
  const lower = modelName.toLowerCase();
  if (lower.includes('linear')) return 0;
  if (lower.includes('random forest')) return 1;
  if (lower.includes('xgboost')) return 2;
  return 3;
}

function resolveSwitchKey(modelName = '') {
  const lower = modelName.toLowerCase();
  if (lower.includes('xgboost')) return 'xgboost';
  if (lower.includes('random forest')) return 'random_forest';
  if (lower.includes('linear')) return 'linear_regression';
  return modelName;
}

export default function ModelRegistry() {
  const { activeSession } = useAuth();
  const [models, setModels] = useState([]);
  const [drift, setDrift] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [switchingId, setSwitchingId] = useState(null);
  const [msg, setMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const sessionId = activeSession?.id;

  const loadModels = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const modelData = await mlApi.getModelRegistry();
      setModels(Array.isArray(modelData) ? modelData : []);
    } catch (err) {
      setErrorMsg(extractApiError(err, 'Failed to load model registry.'));
      setModels([]);
    } finally {
      setLoading(false);
    }
  };

  const loadDrift = async (sid) => {
    if (!sid) return;
    try {
      const driftData = await mlApi.getDrift(sid);
      setDrift(driftData);
    } catch {
      setDrift(null);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (sessionId) {
      loadDrift(sessionId);
    }
  }, [sessionId]);

  const handleRefresh = async () => {
    setRefreshing(true);
    setMsg('');
    try {
      await Promise.all([loadModels(), sessionId ? loadDrift(sessionId) : Promise.resolve()]);
      setMsg('Model registry refreshed successfully.');
    } finally {
      setRefreshing(false);
    }
  };

  const handleSwitchModel = async (model) => {
    setMsg('');
    setErrorMsg('');
    setSwitchingId(model.id);
    try {
      const key = resolveSwitchKey(model.model_name);
      const res = await mlApi.switchModel(key);
      setModels((prev) =>
        prev.map((m) =>
          (m.task || '').toLowerCase().includes('regression')
            ? { ...m, is_active: m.id === model.id }
            : m
        )
      );
      setMsg(
        `Active regression engine switched to ${res.active_model || model.model_name} (${res.version || model.version}).`
      );
    } catch (err) {
      setErrorMsg(extractApiError(err, 'Failed to switch active model.'));
    } finally {
      setSwitchingId(null);
    }
  };

  const regressionModels = useMemo(() => {
    return models
      .filter((m) => (m.task || '').toLowerCase().includes('regression'))
      .sort((a, b) => getModelOrderRank(a.model_name) - getModelOrderRank(b.model_name));
  }, [models]);

  return (
    <div className="space-y-6 min-w-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Machine Learning Model Registry</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Offline-trained model artifacts, versioned metadata, and baseline evaluation benchmarks (D-005, R-016).
          </p>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={loading || refreshing}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh Registry
        </button>
      </div>

      {msg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{msg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-xs text-rose-800 rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <TruthBanner
        modelVersion="Offline-v1.0"
        dataSource="Synthetic Demo + Baseline Protocol"
        isSynthetic={true}
      />

      {/* Active Regression Model Switcher & Side-by-Side Comparison */}
      {regressionModels.length > 0 && (
        <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-600 shrink-0" />
              <div>
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Active Regression Model Switcher &amp; Side-by-Side Comparison
                </h2>
                <p className="text-[11px] text-slate-500">
                  Compare MAE, RMSE, and R² metrics across models and select the active inference engine.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {regressionModels.map((model) => {
              const m = model.metrics || {};
              const mae = formatMetricVal(m.mae);
              const rmse = formatMetricVal(m.rmse);
              const r2 = formatMetricVal(m.r2);
              const cvScore = m.cv_score !== undefined && m.cv_score !== null ? formatMetricVal(m.cv_score) : null;

              return (
                <div
                  key={`switch-${model.id}`}
                  className={`p-4 rounded-xl border flex flex-col justify-between gap-4 ${
                    model.is_active
                      ? 'bg-indigo-50/40 border-indigo-300 ring-1 ring-indigo-200'
                      : 'bg-slate-50/60 border-slate-200'
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="font-bold text-slate-900 text-xs font-mono break-words">
                          {model.model_name}
                        </h3>
                        <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                          {model.version}
                        </p>
                      </div>
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0 ${
                          model.is_active
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : 'bg-slate-200 text-slate-600'
                        }`}
                      >
                        {model.is_active ? 'Active Model' : 'Standby'}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center font-mono">
                      <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                        <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">
                          MAE
                        </div>
                        <div className="text-xs font-bold text-slate-900 mt-0.5">{mae}</div>
                      </div>
                      <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                        <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">
                          RMSE
                        </div>
                        <div className="text-xs font-bold text-slate-900 mt-0.5">{rmse}</div>
                      </div>
                      <div className="bg-white p-2 rounded-lg border border-slate-200/80">
                        <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">
                          R2
                        </div>
                        <div className="text-xs font-bold text-indigo-700 mt-0.5">{r2}</div>
                      </div>
                    </div>

                    {cvScore && (
                      <div className="flex items-center justify-between text-[11px] bg-white px-2.5 py-1.5 rounded-lg border border-slate-200/70">
                        <span className="text-slate-500 font-medium">5-Fold CV R²:</span>
                        <span className="font-mono font-bold text-emerald-700">{cvScore}</span>
                      </div>
                    )}
                  </div>

                  <button
                    type="button"
                    disabled={switchingId !== null}
                    onClick={() => handleSwitchModel(model)}
                    className={`w-full py-2 px-3 rounded-lg text-xs font-semibold transition disabled:opacity-50 ${
                      model.is_active
                        ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm'
                        : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'
                    }`}
                  >
                    {switchingId === model.id
                      ? 'Switching...'
                      : model.is_active
                      ? 'Active (Re-Activate)'
                      : 'Switch Model'}
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Model Feature Drift Monitoring (Playbook §8.6, DoD-008) */}
      {drift && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-600" />
              <div>
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Session Feature Drift Monitoring (§8.6)
                </h2>
                <p className="text-[11px] text-slate-500">
                  Model baseline: <code className="font-mono text-indigo-600 font-semibold">{drift.model_version}</code> • Current Session ID: #{drift.session_id}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${
                  drift.drift_detected
                    ? 'bg-rose-100 text-rose-800 border border-rose-200'
                    : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                }`}
              >
                {drift.drift_detected ? (
                  <>
                    <AlertTriangle className="w-3.5 h-3.5" /> Drift Warning (&gt;{drift.threshold}%)
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-3.5 h-3.5" /> Feature Means Normal
                  </>
                )}
              </span>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
            {Object.entries(drift.feature_drift || {}).map(([featName, featData]) => (
              <div
                key={featName}
                className={`p-3.5 rounded-xl border text-xs ${
                  featData.drift_flag
                    ? 'bg-rose-50/50 border-rose-200'
                    : 'bg-slate-50 border-slate-200/70'
                }`}
              >
                <div className="flex items-center justify-between font-mono font-bold text-slate-800 text-[11px] mb-2">
                  <span>{featName}</span>
                  {featData.drift_flag ? (
                    <span className="text-rose-600 text-[10px] uppercase font-bold">Drift Exceeded</span>
                  ) : (
                    <span className="text-emerald-600 text-[10px] uppercase font-bold">Stable</span>
                  )}
                </div>

                <div className="space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Baseline Mean:</span>
                    <span className="font-mono font-medium">{featData.baseline_mean}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Live Session Mean:</span>
                    <span className="font-mono font-medium">{featData.session_mean}%</span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-slate-200/60 font-semibold">
                    <span className="text-slate-500">Difference:</span>
                    <span className={featData.drift_flag ? 'text-rose-600 font-mono' : 'text-slate-800 font-mono'}>
                      {featData.delta > 0 ? `+${featData.delta}` : featData.delta}% ({featData.percent_difference}%)
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <p className="mt-3 text-[11px] text-slate-400 leading-relaxed">
            {drift.note}
          </p>
        </div>
      )}

      {/* All Registered Model Artifacts Cards */}
      {loading ? (
        <div className="py-12 text-center text-xs text-slate-500">
          Loading active and historical model artifacts...
        </div>
      ) : models.length === 0 ? (
        <div className="py-12 text-center text-xs text-slate-400">
          No model artifacts registered yet in the database.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {models.map((model) => {
            const metricsObj = model.metrics || model.metrics_summary || {};
            return (
              <div
                key={model.id}
                className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {model.task}
                    </span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                        model.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {model.is_active ? 'Active in API' : 'Standby'}
                    </span>
                  </div>

                  <h3 className="font-bold text-slate-900 text-sm font-mono">{model.model_name}</h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">{model.version}</p>

                  <div className="mt-4 space-y-2 text-xs text-slate-600">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-slate-400">Data Source:</span>
                      <span className="font-medium text-slate-800 text-right">{model.data_source}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Dataset Origin:</span>
                      <span
                        className={`font-semibold text-[11px] px-1.5 py-0.5 rounded ${
                          model.is_synthetic ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {model.is_synthetic ? 'Synthetic Demo' : 'Empirical Dataset'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Split Method:</span>
                      <span className="font-mono text-slate-700">{model.split_method}</span>
                    </div>
                  </div>

                  {/* Feature List */}
                  <div className="mt-4 pt-3 border-t border-slate-100">
                    <div className="text-[11px] font-semibold text-slate-500 mb-1.5 flex items-center gap-1">
                      <Layers className="w-3.5 h-3.5 text-slate-400" />
                      Academic Input Features (D-015)
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {Array.isArray(model.feature_list) &&
                        model.feature_list.map((f, i) => (
                          <span
                            key={i}
                            className="text-[10px] font-mono px-1.5 py-0.5 bg-slate-100 rounded text-slate-600"
                          >
                            {f}
                          </span>
                        ))}
                    </div>
                  </div>

                  {/* Metrics Summary */}
                  {Object.keys(metricsObj).length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-100 bg-slate-50/60 p-2.5 rounded-lg">
                      <div className="text-[11px] font-semibold text-slate-700 mb-2">
                        Evaluation Benchmarks
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                        {Object.entries(metricsObj).map(([key, val]) => (
                          <div key={key} className="bg-white p-1.5 rounded border border-slate-200 min-w-0">
                            <div className="text-[10px] text-slate-400 uppercase truncate">{key}</div>
                            <div className="font-bold text-indigo-700 text-[11px] break-words">
                              {formatMetricVal(val)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 text-[10px] text-slate-400 flex items-center justify-between">
                  <span>Artifact ID: #{model.id}</span>
                  <span>Registered: {formatUtcTimestamp(model.trained_at)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
