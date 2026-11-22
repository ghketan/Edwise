import api from './client';

export const legalApi = {
  getPrivacyPolicy: async () => {
    const res = await api.get('/legal/privacy');
    return res.data;
  },
  getTermsOfService: async () => {
    const res = await api.get('/legal/terms');
    return res.data;
  },
  getDocument: async (docType) => {
    const res = await api.get(`/legal/${docType}`);
    return res.data;
  },
};
