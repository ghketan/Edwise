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

export const reportsApi = {
  downloadStudentPdf: async (studentId, sessionId, studentName = 'student') => {
    try {
      const res = await api.get(`/reports/student/${studentId}/pdf`, {
        params: { session_id: sessionId },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${studentName}_report.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      await parseBlobError(err);
    }
  },

  downloadStudentExcel: async (studentId, sessionId, studentName = 'student') => {
    try {
      const res = await api.get(`/reports/student/${studentId}/excel`, {
        params: { session_id: sessionId },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(
        new Blob([res.data], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
      );
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${studentName}_report.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      await parseBlobError(err);
    }
  },

  downloadClassExcel: async (classId, sessionId, sectionId = null, className = 'class') => {
    try {
      const params = { session_id: sessionId };
      if (sectionId) params.section_id = sectionId;
      const res = await api.get(`/reports/class/${classId}/excel`, {
        params,
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(
        new Blob([res.data], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
      );
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${className}_report.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      await parseBlobError(err);
    }
  },
};
