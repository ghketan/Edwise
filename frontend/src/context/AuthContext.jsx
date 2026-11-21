import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { authApi } from '../api/auth';
import { institutionApi } from '../api/institution';
import { decodeJwtPayload } from '../utils/format';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    // SessionStorage protects PII across tabs/persistent storage (R-017)
    const saved = sessionStorage.getItem('edwise_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('access_token') || sessionStorage.getItem('access_token'));
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const hydratedTokenRef = useRef(null);
  const inFlightHydrationRef = useRef(null);

  const logout = useCallback(() => {
    hydratedTokenRef.current = null;
    inFlightHydrationRef.current = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    sessionStorage.removeItem('edwise_user');
    setUser(null);
    setToken(null);
    setActiveSession(null);
    setSessions([]);
  }, []);

  const hydrateSession = useCallback(async (authToken) => {
    try {
      const me = await authApi.getMe();
      const decoded = decodeJwtPayload(authToken);

      let studentProfile = me.student_profile || null;
      let teacherProfile = me.teacher_profile || null;

      // If profile is not directly in me, hydrate using token claims
      if (!studentProfile && me.role === 'STUDENT' && decoded?.student_id) {
        try {
          studentProfile = await institutionApi.getStudentById(decoded.student_id);
        } catch {
          // Fallback minimal profile
          studentProfile = { id: decoded.student_id };
        }
      }

      const fullUser = {
        ...me,
        student_id: decoded?.student_id || studentProfile?.id,
        teacher_id: decoded?.teacher_id || teacherProfile?.id,
        student_profile: studentProfile,
        teacher_profile: teacherProfile,
      };

      setUser(fullUser);
      sessionStorage.setItem('edwise_user', JSON.stringify(fullUser));

      // Fetch academic sessions
      try {
        const sessList = await institutionApi.getSessions();
        setSessions(sessList);
        const active = sessList.find((s) => s.is_active) || sessList[0];
        setActiveSession(active || null);
      } catch (sessErr) {
        console.warn('Failed to load academic sessions:', sessErr);
      }
    } catch (err) {
      console.error('Session init error:', err);
      // Only logout if 401 unauthorized
      if (err.response?.status === 401) {
        logout();
      }
    }
  }, [logout]);

  // Load user profile & active academic session on mount
  useEffect(() => {
    let active = true;
    const init = async () => {
      if (token && hydratedTokenRef.current !== token) {
        if (!inFlightHydrationRef.current) {
          inFlightHydrationRef.current = hydrateSession(token).finally(() => {
            inFlightHydrationRef.current = null;
          });
        }
        await inFlightHydrationRef.current;
        if (localStorage.getItem('access_token') === token) {
          hydratedTokenRef.current = token;
        }
      }
      if (active) setLoading(false);
    };
    init();
    return () => {
      active = false;
    };
  }, [token, hydrateSession]);

  const login = async (username, password) => {
    const res = await authApi.login(username, password);
    localStorage.setItem('access_token', res.access_token);
    if (res.refresh_token) {
      localStorage.setItem('refresh_token', res.refresh_token);
    }
    const baseUser = {
      id: res.user_id,
      username: res.username,
      role: res.role,
      student_id: res.student_id,
      teacher_id: res.teacher_id,
    };
    setUser(baseUser);
    sessionStorage.setItem('edwise_user', JSON.stringify(baseUser));
    setToken(res.access_token);
    hydratedTokenRef.current = res.access_token;

    // Background hydrate full profile without blocking immediate navigation
    hydrateSession(res.access_token).catch((err) => {
      console.warn('Background hydration notice:', err);
    });

    return res;
  };

  const registerStudent = async (data) => {
    return await authApi.registerStudent(data);
  };

  const value = {
    user,
    token,
    role: user?.role,
    isAdmin: user?.role === 'ADMINISTRATOR',
    isTeacher: user?.role === 'TEACHER',
    isStudent: user?.role === 'STUDENT',
    studentProfile: user?.student_profile,
    teacherProfile: user?.teacher_profile,
    studentId: user?.student_id || user?.student_profile?.id,
    teacherId: user?.teacher_id || user?.teacher_profile?.id,
    sessions,
    activeSession,
    setActiveSession,
    login,
    logout,
    registerStudent,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
