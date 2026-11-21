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
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-12 h-12 rounded-2xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-200">
            <GraduationCap className="w-7 h-7" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-slate-900">
          EDWISE Platform
        </h2>
        <p className="mt-1 text-center text-xs text-slate-500">
          Learning Analytics & Academic Performance Evaluation
        </p>

        {/* Tab switcher */}
        <div className="mt-6 flex bg-slate-200/70 p-1 rounded-xl">
          <button
            type="button"
            onClick={() => {
              setIsLoginTab(true);
              setError('');
            }}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              isLoginTab ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
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
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              !isLoginTab ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Claim Student Roster
          </button>
        </div>
      </div>

      <div className="mt-4 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200/80 rounded-2xl sm:px-10">
          {error && (
            <div className="mb-4 rounded-lg bg-rose-50 border border-rose-200 p-3 flex items-start gap-2.5 text-xs text-rose-700">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {regSuccess && (
            <div className="mb-4 rounded-lg bg-emerald-50 border border-emerald-200 p-3.5 flex items-start gap-2.5 text-xs text-emerald-800">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600" />
              <div>
                <p className="font-semibold">Request Received</p>
                <p className="mt-0.5">{regSuccess}</p>
                <p className="mt-1 text-[11px] text-emerald-600">
                  If matched with an unclaimed record, your account is immediately verified and active.
                </p>
              </div>
            </div>
          )}

          {isLoginTab ? (
            /* Login Form */
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700">
                  Username or Admission No.
                </label>
                <div className="mt-1 relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <User className="h-4 w-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. admin or teacher_sarah"
                    className="block w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">Password</label>
                <div className="mt-1 relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="block w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors disabled:opacity-50"
              >
                {loading ? 'Authenticating...' : 'Sign In to Portal'}
              </button>

              {/* Demo Quick Logins */}
              <div className="pt-4 border-t border-slate-100">
                <p className="text-[11px] font-semibold text-slate-500 mb-2 uppercase tracking-wider">
                  Demo Fast Credentials
                </p>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => fillQuickCreds('admin', 'Admin@123')}
                    className="text-[11px] py-1 px-2 rounded border border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100 text-center font-medium"
                  >
                    Admin
                  </button>
                  <button
                    type="button"
                    onClick={() => fillQuickCreds('teacher_sarah', 'Teacher@123')}
                    className="text-[11px] py-1 px-2 rounded border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 text-center font-medium"
                  >
                    Teacher
                  </button>
                  <button
                    type="button"
                    onClick={() => fillQuickCreds('STU1001', 'Student@123')}
                    className="text-[11px] py-1 px-2 rounded border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-center font-medium"
                  >
                    Student
                  </button>
                </div>
              </div>
            </form>
          ) : (
            /* Student Self-Registration Form */
            <form onSubmit={handleRegister} className="space-y-3.5">
              <div className="p-2.5 rounded-lg bg-blue-50/70 border border-blue-100 text-[11px] text-blue-800 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <span>
                  Students must enter their official admission number assigned in the institution roster to claim their account.
                </span>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">
                  Admission Number <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={admissionNumber}
                  onChange={(e) => setAdmissionNumber(e.target.value)}
                  placeholder="e.g. STU1003"
                  className="mt-1 block w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">
                  Class {classes.length === 0 && '(Class ID)'} <span className="text-rose-500">*</span>
                </label>
                {classes.length > 0 ? (
                  <select
                    required
                    value={classId}
                    onChange={(e) => setClassId(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
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
                    className="mt-1 block w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">
                  Create Password (8-72 chars) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  maxLength={72}
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  className="mt-1 block w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Email (Optional)</label>
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    placeholder="student@school.edu"
                    className="mt-1 block w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700">Phone (Optional)</label>
                  <input
                    type="tel"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    placeholder="+1 555-0100"
                    className="mt-1 block w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none disabled:opacity-50 transition-colors"
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
