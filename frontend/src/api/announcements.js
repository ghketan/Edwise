import api from './client';

function sanitizeParams(params) {
  return Object.fromEntries(
    Object.entries(params || {}).filter(
      ([, v]) => v !== null && v !== undefined && v !== ''
    )
  );
}

export const getAnnouncements = async (paramsOrSessionId = {}, classId = null) => {
  const rawParams =
    paramsOrSessionId && typeof paramsOrSessionId === 'object'
      ? paramsOrSessionId
      : { session_id: paramsOrSessionId, class_id: classId };
  const cleanParams = sanitizeParams(rawParams);
  const res = await api.get('/announcements', { params: cleanParams });
  return res.data;
};

export const createAnnouncement = async (data) => {
  const res = await api.post('/announcements', data);
  return res.data;
};

export const deleteAnnouncement = async (announcementId) => {
  const res = await api.delete(`/announcements/${announcementId}`);
  return res.data;
};

export const announcementsApi = {
  getAnnouncements,
  createAnnouncement,
  deleteAnnouncement,
};

export default announcementsApi;
