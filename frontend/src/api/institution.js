import api from './client';

export const institutionApi = {
  // Sessions
  getSessions: async () => {
    const res = await api.get('/institution/sessions');
    return res.data;
  },
  getActiveSession: async () => {
    const res = await api.get('/institution/sessions/active');
    return res.data;
  },
  createSession: async (data) => {
    const res = await api.post('/institution/sessions', data);
    return res.data;
  },

  // Classes
  getClasses: async (sessionId) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const res = await api.get('/institution/classes', { params });
    return res.data;
  },
  createClass: async (data) => {
    const res = await api.post('/institution/classes', data);
    return res.data;
  },

  // Sections (endpoint: /institution/classes/{class_id}/sections)
  getSections: async (classId) => {
    if (!classId) return [];
    const res = await api.get(`/institution/classes/${classId}/sections`);
    return res.data;
  },
  createSection: async (data) => {
    const res = await api.post('/institution/sections', data);
    return res.data;
  },

  // Class-Specific Subjects (Independent per Class)
  getClassSubjects: async (classId) => {
    if (!classId) return [];
    const res = await api.get(`/institution/classes/${classId}/subjects`);
    return res.data;
  },
  assignClassSubject: async (classId, data) => {
    const res = await api.post(`/institution/classes/${classId}/subjects`, data);
    return res.data;
  },
  removeClassSubject: async (classId, subjectId) => {
    const res = await api.delete(`/institution/classes/${classId}/subjects/${subjectId}`);
    return res.data;
  },

  // Subjects
  getSubjects: async () => {
    const res = await api.get('/institution/subjects');
    return res.data;
  },
  createSubject: async (data) => {
    const res = await api.post('/institution/subjects', data);
    return res.data;
  },

  // Teachers
  getTeachers: async () => {
    const res = await api.get('/institution/teachers');
    return res.data;
  },
  createTeacher: async (data) => {
    const res = await api.post('/institution/teachers', data);
    return res.data;
  },

  // Teacher Assignments (ClassSubjectTeacher)
  getAllTeacherAssignments: async (sessionId) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const res = await api.get('/institution/assignments/teachers', { params });
    return res.data;
  },
  getTeacherAssignments: async (teacherId, sessionId) => {
    if (!teacherId) return [];
    const params = sessionId ? { session_id: sessionId } : {};
    const res = await api.get(`/institution/teachers/${teacherId}/assignments`, { params });
    return res.data;
  },
  assignTeacher: async (data) => {
    const res = await api.post('/institution/assignments/teachers', data);
    return res.data;
  },

  // Students & Rosters
  getStudents: async (classId, sectionId) => {
    const params = {};
    if (classId) params.class_id = classId;
    if (sectionId) params.section_id = sectionId;
    const res = await api.get('/institution/students', { params });
    return res.data;
  },
  getStudentById: async (studentId) => {
    const res = await api.get(`/students/${studentId}`);
    return res.data;
  },
  importRoster: async (studentsList) => {
    // Backend expects { students: [...] } (StudentRosterImport)
    const payload = Array.isArray(studentsList) ? { students: studentsList } : studentsList;
    const res = await api.post('/institution/roster/import', payload);
    return res.data;
  },
  enrollStudent: async (data) => {
    const res = await api.post('/institution/enrollments', data);
    return res.data;
  },
};
