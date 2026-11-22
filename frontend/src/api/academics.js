import api from './client';

async function parseBlobError(err) {
  if (err.response?.data instanceof Blob) {
    try {
      const text = await err.response.data.text();
      const json = JSON.parse(text);
      if (json && json.detail) {
        err.response.data = json;
      }
    } catch {
      // Keep original err
    }
  }
  throw err;
}

function extractFilenameFromDisposition(disposition, fallback) {
  if (typeof disposition === 'string' && disposition) {
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;\n]+)/i);
    if (utf8Match?.[1]) {
      try {
        return decodeURIComponent(utf8Match[1].trim().replace(/^["']|["']$/g, ''));
      } catch {
        return utf8Match[1].trim();
      }
    }
    const asciiMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i);
    if (asciiMatch?.[1]) {
      const cleaned = asciiMatch[1].trim().replace(/^["']|["']$/g, '');
      if (cleaned) return cleaned;
    }
  }
  return fallback;
}

export const uploadDatesheet = async (examId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post(`/exams/${examId}/datesheet`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const downloadDatesheet = async (examId, filenameHint = null) => {
  try {
    const res = await api.get(`/exams/${examId}/datesheet`, {
      responseType: 'blob',
    });
    const disposition =
      res.headers?.['content-disposition'] || res.headers?.get?.('content-disposition');
    const filename = extractFilenameFromDisposition(
      disposition,
      filenameHint || `exam_${examId}_datesheet`
    );
    const contentType =
      res.headers?.['content-type'] ||
      res.headers?.get?.('content-type') ||
      res.data?.type ||
      'application/octet-stream';
    const blob =
      res.data instanceof Blob ? res.data : new Blob([res.data], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return { blob, filename };
  } catch (err) {
    await parseBlobError(err);
  }
};

export const uploadMarksCsv = async (
  fileOrPayload,
  sessionId,
  reasonOrOptions = 'Bulk marks CSV import',
  examId = null
) => {
  let file = fileOrPayload;
  let resolvedSessionId = sessionId;
  let resolvedReason = 'Bulk marks CSV import';
  let resolvedExamId = examId;

  if (
    fileOrPayload &&
    typeof fileOrPayload === 'object' &&
    !(typeof File !== 'undefined' && fileOrPayload instanceof File) &&
    !(typeof Blob !== 'undefined' && fileOrPayload instanceof Blob) &&
    'file' in fileOrPayload
  ) {
    file = fileOrPayload.file;
    resolvedSessionId = fileOrPayload.sessionId ?? fileOrPayload.session_id;
    resolvedReason =
      typeof fileOrPayload.reason === 'string' && fileOrPayload.reason.trim()
        ? fileOrPayload.reason
        : 'Bulk marks CSV import';
    resolvedExamId = fileOrPayload.examId ?? fileOrPayload.exam_id ?? null;
  } else if (reasonOrOptions && typeof reasonOrOptions === 'object') {
    resolvedReason =
      typeof reasonOrOptions.reason === 'string' && reasonOrOptions.reason.trim()
        ? reasonOrOptions.reason
        : 'Bulk marks CSV import';
    resolvedExamId = reasonOrOptions.examId ?? reasonOrOptions.exam_id ?? examId ?? null;
  } else if (typeof reasonOrOptions === 'string' && reasonOrOptions.trim()) {
    resolvedReason = reasonOrOptions;
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('session_id', String(resolvedSessionId));
  formData.append('reason', resolvedReason || 'Bulk marks CSV import');
  if (resolvedExamId !== null && resolvedExamId !== undefined && resolvedExamId !== '') {
    formData.append('exam_id', String(resolvedExamId));
  }

  const res = await api.post('/marks/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const academicsApi = {
  // Attendance
  getAttendance: async (params) => {
    // Note: query param for date is "date"
    const res = await api.get('/attendance', { params });
    return res.data;
  },
  saveAttendance: async (data) => {
    // PUT /api/v1/attendance (API-001)
    const res = await api.put('/attendance', data);
    return res.data;
  },

  // Exams
  getExams: async (params) => {
    const res = await api.get('/exams', { params });
    return res.data;
  },
  createExam: async (data) => {
    const res = await api.post('/exams', data);
    return res.data;
  },

  // Marks
  getMarksForExam: async (examId) => {
    const res = await api.get(`/marks/exam/${examId}`);
    return res.data;
  },
  getStudentMarks: async (studentId, sessionId) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const res = await api.get(`/marks/student/${studentId}`, { params });
    return res.data;
  },
  saveMarks: async (data) => {
    // PUT /api/v1/marks (R-005, R-014: audited with reason)
    const res = await api.put('/marks', data);
    return res.data;
  },

  // Assignments
  getAssignments: async (params) => {
    const res = await api.get('/assignments', { params });
    return res.data;
  },
  createAssignment: async (data) => {
    const res = await api.post('/assignments', data);
    return res.data;
  },
  submitAssignment: async (assignmentId, data) => {
    const payload = typeof data === 'string' ? { assignment_id: assignmentId, content: data } : { assignment_id: assignmentId, ...data };
    const res = await api.post(`/assignments/${assignmentId}/submit`, payload);
    return res.data;
  },
  uploadAssignmentSubmission: async (assignmentId, file, content = '') => {
    const formData = new FormData();
    formData.append('file', file);
    if (content) formData.append('content', content);
    const res = await api.post(`/assignments/${assignmentId}/submit-file`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  getSubmissions: async (assignmentId) => {
    const res = await api.get(`/assignments/${assignmentId}/submissions`);
    return res.data;
  },
  gradeSubmission: async (submissionId, data) => {
    const res = await api.put(`/assignments/submissions/${submissionId}/grade`, data);
    return res.data;
  },

  // Datesheets & Bulk CSV
  uploadDatesheet,
  downloadDatesheet,
  uploadMarksCsv,
};
