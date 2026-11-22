import api from './client';

export const usersApi = {
  // GET /users (Admin lists all users)
  getUsers: async () => {
    const res = await api.get('/users');
    return res.data;
  },

  // POST /users (Admin creates a new user)
  createUser: async (userData) => {
    const res = await api.post('/users', userData);
    return res.data;
  },

  // PUT /users/{id} (Admin updates account status or password)
  updateUser: async (userId, data) => {
    const res = await api.put(`/users/${userId}`, data);
    return res.data;
  },

  // POST /users/{id}/verify (Admin verifies student/teacher registration)
  verifyUser: async (userId) => {
    const res = await api.post(`/users/${userId}/verify`);
    return res.data;
  },
};

