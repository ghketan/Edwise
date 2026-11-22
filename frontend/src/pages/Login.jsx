import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { institutionApi } from '../api/institution';
import { extractApiError } from '../utils/format';
import {
  GraduationCap,
  Lock,
  User,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';

export default function Login() {
  const [isLoginTab, setIsLoginTab] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Registration state
  const [admissionNumber, setAdmissionNumber] = useState('');
  const [classId, setClassId] = useState('1');
  const [regPassword, setRegPassword] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [regSuccess, setRegSuccess] = useState(null);
  const [classes, setClasses] = useState([]);

  const { login, registerStudent, user } = useAuth();
  const navigate = useNavigate();

  // If already logged in, redirect
  useEffect(() => {
    if (user && user.role) {
      if (user.role === 'ADMINISTRATOR') navigate('/admin', { replace: true });
      else if (user.role === 'TEACHER') navigate('/teacher', { replace: true });
      else if (user.role === 'STUDENT') navigate('/student', { replace: true });
    }
  }, [user, navigate]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await login(username, password);
      if (res?.role === 'ADMINISTRATOR') {
        navigate('/admin', { replace: true });
      } else if (res?.role === 'TEACHER') {
        navigate('/teacher', { replace: true });
      } else if (res?.role === 'STUDENT') {
        navigate('/student', { replace: true });
      } else {
        navigate('/', { replace: true });
      }
    } catch (err) {
      setError(extractApiError(err, 'Invalid username or password.'));
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setRegSuccess(null);

    const parsedClassId = parseInt(classId, 10);
    if (!parsedClassId || parsedClassId < 1) {
      setError('Please provide a valid Class ID.');
      return;
    }

    if (regPassword.length < 8 || regPassword.length > 72) {
      setError('Password must be between 8 and 72 characters.');
      return;
    }

    setLoading(true);
    try {
      const res = await registerStudent({
        admission_number: admissionNumber.trim(),
        class_id: parsedClassId,
        password: regPassword,
        contact_email: contactEmail.trim() || null,
        contact_phone: contactPhone.trim() || null,
      });
      // Uniform 202 response (API-002, T-006)
      setRegSuccess(
        res.message || 'Registration request received and being processed against official rosters.'
      );
      setAdmissionNumber('');
      setRegPassword('');
      setContactEmail('');
      setContactPhone('');
    } catch (err) {
      setError(extractApiError(err, 'Registration failed. Please check inputs.'));
    } finally {
      setLoading(false);
    }
  };

  const fillQuickCreds = (u, p) => {
    setUsername(u);
    setPassword(p);
    setError('');
  };

  return (
    <div className="min-h-screen bg-canvas-slate flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Ambient background glows */}
      <div className="ambient-glow-cyan"></div>
      <div className="ambient-glow-indigo"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex justify-center">
          <div className="w-14 h-14 rounded-2xl bg-primary-container flex items-center justify-center text-white shadow-xl shadow-indigo-300">
            <GraduationCap className="w-8 h-8" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-on-surface">
          EDWISE Platform
        </h2>
        <p className="mt-1 text-center text-xs text-on-surface-variant font-medium">
          Learning Analytics & Academic Performance Evaluation
        </p>

        {/* Tab switcher */}
        <div className="mt-6 flex bg-surface-container-high/80 p-1 rounded-2xl backdrop-blur-md">
          <button
            type="button"
            onClick={() => {
              setIsLoginTab(true);
              setError('');
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all ${
              isLoginTab ? 'bg-surface-container-lowest text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setIsLoginTab(false);
              setError('');
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all ${
              !isLoginTab ? 'bg-surface-container-lowest text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Student Registration
          </button>
        </div>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md relative z-10 px-4 sm:px-0">
        <div className="glass-panel py-8 px-6 sm:px-10 rounded-3xl border border-glass-border shadow-2xl">
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-status-rose-bg border border-rose-200 text-xs text-status-rose-text flex items-center gap-2 font-medium">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
          )}

          {regSuccess && (
            <div className="mb-4 p-3.5 rounded-xl bg-status-emerald-bg border border-emerald-200 text-xs text-emerald-950 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 mt-0.5" />
              <div>
                <p className="font-bold text-status-emerald-text">Registration Submitted</p>
                <p className="mt-0.5 leading-relaxed font-medium">{regSuccess}</p>
                <button
                  type="button"
                  onClick={() => setIsLoginTab(true)}
                  className="mt-2 text-[11px] font-bold text-primary underline block"
                >
                  Return to Sign In
                </button>
              </div>
            </div>
          )}

          {isLoginTab ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-on-surface">
                  Username
                </label>
                <div className="mt-1 relative rounded-xl shadow-xs">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="h-4 w-4 text-outline" />
                  </div>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. admin or teacher_sarah"
                    className="block w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-glass-border bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface">
                  Password
                </label>
                <div className="mt-1 relative rounded-xl shadow-xs">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-4 w-4 text-outline" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="block w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-glass-border bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-xl shadow-md text-xs font-bold text-white bg-primary-container hover:opacity-95 focus:outline-none disabled:opacity-50 transition-all active:scale-[0.98]"
              >
                {loading ? 'Authenticating...' : 'Sign In to Portal'}
              </button>

              {/* Quick test credentials */}
              <div className="mt-6 pt-4 border-t border-slate-100">
                <p className="text-[10px] font-bold uppercase tracking-wider text-outline mb-2 text-center">
                  Quick Demo Accounts
                </p>
                <div className="flex flex-wrap gap-1.5 justify-center">
                  <button
                    type="button"
                    onClick={() => fillQuickCreds('admin', 'Admin@123')}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-surface-container-low hover:bg-surface-container-high border border-glass-border text-on-surface font-mono font-medium transition-colors"
                  >
                    Admin
                  </button>
                  <button
                    type="button"
                    onClick={() => fillQuickCreds('teacher_sarah', 'Teacher@123')}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-surface-container-low hover:bg-surface-container-high border border-glass-border text-on-surface font-mono font-medium transition-colors"
                  >
                    Teacher Sarah
                  </button>
                  <button
                    type="button"
                    onClick={() => fillQuickCreds('STU1001', 'Student@123')}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-surface-container-low hover:bg-surface-container-high border border-glass-border text-on-surface font-mono font-medium transition-colors"
                  >
                    Student Alex
                  </button>
                </div>
              </div>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-3.5">
              <div className="p-3 rounded-xl bg-status-sky-bg border border-sky-200 text-[11px] text-sky-950 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-secondary shrink-0 mt-0.5" />
                <span className="font-medium">
                  Students must enter their official admission number assigned in the institution roster to claim their account.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface">
                  Admission Number <span className="text-status-rose-text">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={admissionNumber}
                  onChange={(e) => setAdmissionNumber(e.target.value)}
                  placeholder="e.g. STU1003"
                  className="mt-1 block w-full px-3 py-2 text-xs rounded-xl border border-glass-border bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface">
                  Class {classes.length === 0 && '(Class ID)'} <span className="text-status-rose-text">*</span>
                </label>
                {classes.length > 0 ? (
                  <select
                    required
                    value={classId}
                    onChange={(e) => setClassId(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 text-xs rounded-xl border border-glass-border bg-surface-container-lowest text-on-surface font-semibold focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container"
                  >
                    {classes.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    min="1"
                    required
                    value={classId}
                    onChange={(e) => setClassId(e.target.value)}
                    placeholder="Enter Class ID (e.g. 1)"
                    className="mt-1 block w-full px-3 py-2 text-xs rounded-xl border border-glass-border bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container"
                  />
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface">
                  Create Password (8-72 chars) <span className="text-status-rose-text">*</span>
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  maxLength={72}
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  className="mt-1 block w-full px-3 py-2 text-xs rounded-xl border border-glass-border bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container focus:border-primary-container"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-on-surface">Email (Optional)</label>
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    placeholder="student@school.edu"
                    className="mt-1 block w-full px-3 py-1.5 text-xs rounded-xl border border-glass-border bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-on-surface">Phone (Optional)</label>
                  <input
                    type="tel"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    placeholder="+1 555-0100"
                    className="mt-1 block w-full px-3 py-1.5 text-xs rounded-xl border border-glass-border bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-xl shadow-md text-xs font-bold text-white bg-primary-container hover:opacity-95 focus:outline-none disabled:opacity-50 transition-all active:scale-[0.98]"
              >
                {loading ? 'Submitting Claim...' : 'Claim Student Record'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
