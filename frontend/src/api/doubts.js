import api from './client';

function sanitizeParams(params) {
  return Object.fromEntries(
    Object.entries(params || {}).filter(
      ([, v]) => v !== null && v !== undefined && v !== ''
    )
  );
}

export const getDoubts = async (paramsOrSessionId = {}, subjectId = null) => {
  const rawParams =
    paramsOrSessionId && typeof paramsOrSessionId === 'object'
      ? paramsOrSessionId
      : { session_id: paramsOrSessionId, subject_id: subjectId };
  const cleanParams = sanitizeParams(rawParams);
  const res = await api.get('/doubts', { params: cleanParams });
  return res.data;
};

export const createDoubt = async (data) => {
  const res = await api.post('/doubts', data);
  return res.data;
};

export const answerDoubt = async (doubtId, data) => {
  const payload = typeof data === 'string' ? { answer: data } : data;
  const res = await api.post(`/doubts/${doubtId}/answer`, payload);
  return res.data;
};

export const doubtsApi = {
  getDoubts,
  createDoubt,
  answerDoubt,
};

export default doubtsApi;
