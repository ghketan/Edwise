import api from './client';

export const auditApi = {
  getAuditLogs: async (params) => {
    // GET /audit/logs (R-014, D-013)
    const res = await api.get('/audit/logs', { params });
    return res.data;
  },
};
