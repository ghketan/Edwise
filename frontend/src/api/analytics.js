import api from './client';

export const getAttendanceGoal = async (studentId, sessionId, targetPct = 75.0) => {
  const params = { session_id: sessionId };
  if (targetPct !== undefined && targetPct !== null && targetPct !== '') {
    params.target_pct = targetPct;
  }
  const res = await api.get(`/attendance/goal/${studentId}`, { params });
  return res.data;
};

export const getAiLessonPlan = async (classId, sessionId) => {
  const res = await api.get(`/analytics/ai-lesson-plan/${classId}`, {
    params: { session_id: sessionId },
  });
  return res.data;
};

export const getStudentBadges = async (studentId, sessionId) => {
  const res = await api.get(`/analytics/student-badges/${studentId}`, {
    params: { session_id: sessionId },
  });
  return res.data;
};

export const analyticsApi = {
  // Scoped attendance analytics
  getAttendanceAnalytics: async (params) => {
    const res = await api.get('/analytics/attendance', { params });
    return res.data;
  },

  // Exam analytics (distribution, mean, median, pass rate)
  getExamAnalytics: async (examId) => {
    const res = await api.get(`/analytics/exams/${examId}`);
    return res.data;
  },

  // Student vs Class comparative analytics
  getStudentVsClass: async (studentId, sessionId) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const res = await api.get(`/analytics/student-vs-class/${studentId}`, { params });
    return res.data;
  },

  // Declining performance alert
  getDecliningPerformance: async (classId, sessionId, minDrops = 2) => {
    const params = { session_id: sessionId, min_consecutive_drops: minDrops };
    const res = await api.get(`/analytics/declining-performance/${classId}`, { params });
    return res.data;
  },

  // Attendance Goal, AI Lesson Plan & Student Badges
  getAttendanceGoal,
  getAiLessonPlan,
  getStudentBadges,
};
