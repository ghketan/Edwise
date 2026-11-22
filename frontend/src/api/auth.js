import api from './client';

export const authApi = {
  login: async (username, password) => {
    const res = await api.post('/auth/login', { username, password });
    return res.data;
  },
  registerStudent: async (data) => {
    // API-002: uniform 202 response
    const res = await api.post('/auth/register-student', data);
    return res.data;
  },
  getMe: async () => {
    const res = await api.get('/auth/me');
    return res.data;
  },
};
