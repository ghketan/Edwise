import api from './client';

export const recommendationApi = {
  getRules: async () => {
    const res = await api.get('/recommendations/rules');
    return res.data;
  },
  createRule: async (data) => {
    const res = await api.post('/recommendations/rules', data);
    return res.data;
  },
  getStudentRecommendations: async (studentId, sessionId) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const res = await api.get(`/recommendations/student/${studentId}`, { params });
    return res.data;
  },
  reviewRecommendation: async (recId, reviewStatus, reviewNotes) => {
    // PUT /recommendations/{rec_id}/review with { review_status, review_notes }
    const res = await api.put(`/recommendations/${recId}/review`, {
      review_status: reviewStatus,
      review_notes: reviewNotes,
    });
    return res.data;
  },
};
