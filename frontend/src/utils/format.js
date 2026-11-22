/**
 * Utility functions for API error parsing, date formatting, and token decoding.
 */

export function extractApiError(err, fallback = 'An unexpected error occurred') {
  if (!err) return fallback;
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    // FastAPI 422 validation errors: [{ loc: ['body', 'field'], msg: '...', type: '...' }]
    return detail
      .map(item => {
        const field = Array.isArray(item.loc)
          ? item.loc.filter(l => l !== 'body').join('.')
          : item.loc;
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join('; ');
  }
  if (detail && typeof detail === 'object') {
    return detail.message || JSON.stringify(detail);
  }
  if (err.response?.data?.message) {
    return err.response.data.message;
  }
  if (err.message) {
    return err.message;
  }
  return fallback;
}

export function getLocalDateString(d = new Date()) {
  const dateObj = typeof d === 'string' ? new Date(d) : d;
  if (Number.isNaN(dateObj.getTime())) return '';
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, '0');
  const day = String(dateObj.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function getLocalDateTimeInput(d = new Date()) {
  const dateObj = typeof d === 'string' ? new Date(d) : d;
  if (Number.isNaN(dateObj.getTime())) return '';
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, '0');
  const day = String(dateObj.getDate()).padStart(2, '0');
  const hours = String(dateObj.getHours()).padStart(2, '0');
  const minutes = String(dateObj.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function formatDateOnly(val) {
  if (!val) return '—';
  // If val is YYYY-MM-DD string, don't parse through new Date() to avoid timezone shift
  if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(val)) {
    const [y, m, d] = val.split('-');
    return `${d}/${m}/${y}`;
  }
  try {
    const dateObj = new Date(val);
    if (Number.isNaN(dateObj.getTime())) return String(val);
    return dateObj.toLocaleDateString();
  } catch {
    return String(val);
  }
}

export function formatUtcTimestamp(val) {
  if (!val) return '—';
  try {
    const dateObj = new Date(val);
    if (Number.isNaN(dateObj.getTime())) return String(val);
    return dateObj.toLocaleString();
  } catch {
    return String(val);
  }
}

export function decodeJwtPayload(token) {
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length < 2) return null;
  try {
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

