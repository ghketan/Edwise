import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { institutionApi } from '../../api/institution';
import { mlApi } from '../../api/ml';
import StatCard from '../../components/StatCard';
import TruthBanner from '../../components/TruthBanner';
import {
  Calendar,
  School,
  Users,
  GraduationCap,
  ShieldCheck,
  BrainCircuit,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';

export default function AdminDashboard() {
  const [stats, setStats] = useState({
    sessions: 0,
    classes: 0,
    students: 0,
    teachers: 0,
  });
  const [activeSession, setActiveSession] = useState(null);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [sessList, classList, stuList, teachList, modelList] = await Promise.all([
        institutionApi.getSessions().catch(() => []),
        institutionApi.getClasses().catch(() => []),
        institutionApi.getStudents().catch(() => []),
        institutionApi.getTeachers().catch(() => []),
        mlApi.getModelRegistry().catch(() => []),
      ]);

      const sessions = Array.isArray(sessList) ? sessList : [];
      const classes = Array.isArray(classList) ? classList : [];
      const students = Array.isArray(stuList) ? stuList : [];
      const teachers = Array.isArray(teachList) ? teachList : [];

      setStats({
        sessions: sessions.length,
        classes: classes.length,
        students: students.length,
        teachers: teachers.length,
      });

      const active = sessions.find((s) => s.is_active) || sessions[0];
      setActiveSession(active || null);
      setModels(Array.isArray(modelList) ? modelList : []);
    } catch (err) {
      console.error('Error loading admin dashboard', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Institution Overview</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Academic configuration, student roster management, and model registry governance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Overview
          </button>
        </div>
      </div>

      {/* Playbook truth notice */}
      <TruthBanner
        modelVersion="offline-v1.0"
        dataSource="Synthetic Demo + Baseline Protocols"
        isSynthetic={true}
      />

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Session"
          value={activeSession?.name || 'None Active'}
          subtitle={
            activeSession
              ? `${activeSession.start_date} to ${activeSession.end_date}`
              : 'Configure sessions in Setup'
          }
          icon={Calendar}
          color="indigo"
          badge={activeSession?.is_active ? 'Active' : 'Archived'}
        />
        <StatCard
          title="Classes Configured"
          value={stats.classes}
          subtitle="Grade sections & subject mappings"
          icon={School}
          color="sky"
        />
        <StatCard
          title="Enrolled Students"
          value={stats.students}
          subtitle="Official roster records"
          icon={GraduationCap}
          color="emerald"
        />
        <StatCard
          title="Faculty Members"
          value={stats.teachers}
          subtitle="Instructors with active scope"
          icon={Users}
          color="amber"
        />
      </div>

      {/* Quick Launch Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center mb-3">
              <School className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-sm text-slate-900">Institution & Classes</h3>
            <p className="text-xs text-slate-500 mt-1">
              Set up classes, academic sessions, subjects, and bind teachers to class-subject assignments.
            </p>
          </div>
          <Link
            to="/admin/setup"
            className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
          >
            Manage Structure <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3">
              <Users className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-sm text-slate-900">Student Rosters</h3>
            <p className="text-xs text-slate-500 mt-1">
              Add student records or upload CSV rosters with admission numbers for self-service claim.
            </p>
          </div>
          <Link
            to="/admin/roster"
            className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
          >
            View Rosters & Import <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-sm text-slate-900">Audit Trail (R-014)</h3>
            <p className="text-xs text-slate-500 mt-1">
              Inspect immutable audit records for attendance entries, mark modifications, and enrollments.
            </p>
          </div>
          <Link
            to="/admin/audit"
            className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
          >
            Inspect Audit Logs <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Active Models Quick Glance */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BrainCircuit className="w-4 h-4 text-indigo-600" />
            <h3 className="font-semibold text-sm text-slate-900">Active ML Artifacts in Registry</h3>
          </div>
          <Link
            to="/admin/models"
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
          >
            Detailed Registry & Metrics &rarr;
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="py-2 px-3 font-semibold">Task</th>
                <th className="py-2 px-3 font-semibold">Model Name</th>
                <th className="py-2 px-3 font-semibold">Version</th>
                <th className="py-2 px-3 font-semibold">Source</th>
                <th className="py-2 px-3 font-semibold">Synthetic Flag</th>
                <th className="py-2 px-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {models.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-4 text-center text-slate-400">
                    No models registered yet.
                  </td>
                </tr>
              ) : (
                models.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50/60">
                    <td className="py-2.5 px-3 font-medium capitalize text-slate-900">{m.task}</td>
                    <td className="py-2.5 px-3 font-mono">{m.model_name}</td>
                    <td className="py-2.5 px-3">{m.version}</td>
                    <td className="py-2.5 px-3">{m.data_source}</td>
                    <td className="py-2.5 px-3">
                      {m.is_synthetic ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">
                          Synthetic Demo
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                          Empirical
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                        {m.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
