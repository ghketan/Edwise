import api from './client';

export const predictLive = async (payload = {}) => {
  const cleanPayload = Object.fromEntries(
    Object.entries(payload || {}).filter(
      ([k, v]) => v !== undefined && (k === 'subject_name' || (v !== null && v !== ''))
    )
  );
  const res = await api.post('/ml/predict-live', cleanPayload);
  return res.data;
};

export const switchModel = async (modelNameOrPayload) => {
  const body =
    typeof modelNameOrPayload === 'string'
      ? { model_name: modelNameOrPayload }
      : (modelNameOrPayload ?? { model_name: '' });
  const res = await api.post('/ml/switch-model', body);
  return res.data;
};

export const mlApi = {
  // API-003, R-009, R-010, R-015
  getStudentEstimate: async (studentId, sessionId) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const res = await api.get(`/ml/students/${studentId}/estimate`, { params });
    return res.data;
  },
  getModelRegistry: async () => {
    const res = await api.get('/ml/models');
    return res.data;
  },
  getClusters: async (sessionId) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const res = await api.get('/ml/clusters', { params });
    return res.data;
  },
  // §8.6, DoD-008: Model Feature Drift Monitoring
  getDrift: async (sessionId) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const res = await api.get('/ml/drift', { params });
    return res.data;
  },

  // Live Predictor & Active Model Switcher
  predictLive,
  switchModel,
};
