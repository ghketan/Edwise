import React, { useState, useEffect, useMemo } from 'react';
import { usersApi } from '../../api/users';
import { extractApiError, formatDateOnly, formatUtcTimestamp } from '../../utils/format';
import {
  Users,
  UserPlus,
  ShieldCheck,
  CheckCircle,
  AlertCircle,
  Search,
  Filter,
  RefreshCw,
  Lock,
  UserCheck,
  XCircle,
} from 'lucide-react';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [verifiedFilter, setVerifiedFilter] = useState('');
  const [msg, setMsg] = useState({ text: '', type: '' });

  // Create User Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    role: 'STUDENT',
    is_active: true,
    is_verified: true,
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    setMsg({ text: '', type: '' });
    try {
      const data = await usersApi.getUsers();
      setUsers(Array.isArray(data) ? data : []);
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to load user accounts.'), type: 'error' });
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (userId, username) => {
    try {
      await usersApi.verifyUser(userId);
      setMsg({ text: `Account '${username}' verified successfully.`, type: 'success' });
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_verified: true } : u))
      );
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to verify user.'), type: 'error' });
    }
  };

  const handleToggleActive = async (user) => {
    try {
      const newStatus = !user.is_active;
      await usersApi.updateUser(user.id, { is_active: newStatus });
      setMsg({
        text: `Account '${user.username}' marked as ${newStatus ? 'active' : 'deactivated'}.`,
        type: 'success',
      });
      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, is_active: newStatus } : u))
      );
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to update user status.'), type: 'error' });
    }
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setMsg({ text: '', type: '' });

    try {
      const payload = {
        username: formData.username.trim(),
        email: formData.email.trim() || undefined,
        password: formData.password,
        role: formData.role,
        is_active: formData.is_active,
        is_verified: formData.is_verified,
      };

      const newUser = await usersApi.createUser(payload);
      setMsg({ text: `User '${newUser.username}' created successfully!`, type: 'success' });
      setShowCreateModal(false);
      setFormData({
        username: '',
        email: '',
        password: '',
        role: 'STUDENT',
        is_active: true,
        is_verified: true,
      });
      loadUsers();
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to create user.'), type: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const matchSearch =
        u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (u.email && u.email.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchRole = !roleFilter || u.role === roleFilter;
      const matchVerified =
        !verifiedFilter ||
        (verifiedFilter === 'verified' && u.is_verified) ||
        (verifiedFilter === 'unverified' && !u.is_verified);
      return matchSearch && matchRole && matchVerified;
    });
  }, [users, searchQuery, roleFilter, verifiedFilter]);

  const stats = useMemo(() => {
    const total = users.length;
    const students = users.filter((u) => u.role === 'STUDENT').length;
    const teachers = users.filter((u) => u.role === 'TEACHER').length;
    const admins = users.filter((u) => u.role === 'ADMINISTRATOR').length;
    const pending = users.filter((u) => !u.is_verified).length;
    return { total, students, teachers, admins, pending };
  }, [users]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Institutional User Accounts</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage user roles, toggle account activity, and verify pending student and teacher self-registrations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadUsers}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition"
          >
            <UserPlus className="w-3.5 h-3.5" /> Create User
          </button>
        </div>
      </div>

      {msg.text && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
            msg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {msg.type === 'success' ? (
            <CheckCircle className="w-4 h-4 shrink-0 text-emerald-600" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          )}
          <span>{msg.text}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
        <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-slate-500 block text-[10px] uppercase font-semibold">Total Accounts</span>
          <span className="text-lg font-bold text-slate-900">{stats.total}</span>
        </div>
        <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-slate-500 block text-[10px] uppercase font-semibold">Students</span>
          <span className="text-lg font-bold text-sky-700">{stats.students}</span>
        </div>
        <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-slate-500 block text-[10px] uppercase font-semibold">Teachers</span>
          <span className="text-lg font-bold text-amber-700">{stats.teachers}</span>
        </div>
        <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-slate-500 block text-[10px] uppercase font-semibold">Administrators</span>
          <span className="text-lg font-bold text-indigo-700">{stats.admins}</span>
        </div>
        <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-sm">
          <span className="text-slate-500 block text-[10px] uppercase font-semibold">Pending Verification</span>
          <span
            className={`text-lg font-bold ${
              stats.pending > 0 ? 'text-rose-600 font-extrabold' : 'text-slate-900'
            }`}
          >
            {stats.pending}
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search by username or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none"
          >
            <option value="">All Roles</option>
            <option value="ADMINISTRATOR">Administrator</option>
            <option value="TEACHER">Teacher</option>
            <option value="STUDENT">Student</option>
          </select>

          <select
            value={verifiedFilter}
            onChange={(e) => setVerifiedFilter(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none"
          >
            <option value="">All Verification</option>
            <option value="verified">Verified Only</option>
            <option value="unverified">Pending Verification</option>
          </select>

          {(searchQuery || roleFilter || verifiedFilter) && (
            <button
              onClick={() => {
                setSearchQuery('');
                setRoleFilter('');
                setVerifiedFilter('');
              }}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* User Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="py-2.5 px-3 font-semibold">User Details</th>
                <th className="py-2.5 px-3 font-semibold">Role</th>
                <th className="py-2.5 px-3 font-semibold">Status</th>
                <th className="py-2.5 px-3 font-semibold">Verification</th>
                <th className="py-2.5 px-3 font-semibold">Created Date</th>
                <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    Loading user accounts...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    No matching users found.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => {
                  return (
                    <tr key={u.id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-slate-900">{u.username}</div>
                        <div className="text-[11px] text-slate-400">{u.email || 'No email associated'}</div>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            u.role === 'ADMINISTRATOR'
                              ? 'bg-indigo-100 text-indigo-800'
                              : u.role === 'TEACHER'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-sky-100 text-sky-800'
                          }`}
                        >
                          {u.role}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${
                            u.is_active
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-slate-100 text-slate-500'
                          }`}
                        >
                          {u.is_active ? 'Active' : 'Deactivated'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        {u.is_verified ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                            <CheckCircle className="w-3.5 h-3.5" /> Verified
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-600 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                            <AlertCircle className="w-3.5 h-3.5" /> Pending
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-slate-500 font-mono text-[11px]">
                        {formatDateOnly(u.created_at)}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {!u.is_verified && (
                            <button
                              onClick={() => handleVerify(u.id, u.username)}
                              className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition"
                            >
                              <UserCheck className="w-3 h-3" /> Verify
                            </button>
                          )}
                          <button
                            onClick={() => handleToggleActive(u)}
                            className={`px-2 py-1 text-[11px] font-semibold rounded border transition ${
                              u.is_active
                                ? 'border-rose-200 text-rose-700 hover:bg-rose-50'
                                : 'border-emerald-200 text-emerald-700 hover:bg-emerald-50'
                            }`}
                          >
                            {u.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900">Provision New Institutional Account</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-3.5 mt-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Username <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. jsmith or teacher_mary"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Email Address</label>
                <input
                  type="email"
                  placeholder="e.g. jsmith@institution.edu"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Initial Password <span className="text-rose-500">*</span>
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="Minimum 8 characters"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Institutional Role</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none"
                >
                  <option value="STUDENT">Student</option>
                  <option value="TEACHER">Teacher</option>
                  <option value="ADMINISTRATOR">Administrator</option>
                </select>
              </div>

              <div className="flex items-center gap-6 pt-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="rounded text-indigo-600 focus:ring-0"
                  />
                  <span className="text-slate-700 font-medium">Active Immediately</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_verified}
                    onChange={(e) => setFormData({ ...formData, is_verified: e.target.checked })}
                    className="rounded text-indigo-600 focus:ring-0"
                  />
                  <span className="text-slate-700 font-medium">Pre-Verified</span>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

