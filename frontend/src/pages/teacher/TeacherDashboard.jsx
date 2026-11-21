import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { institutionApi } from '../../api/institution';
import { academicsApi } from '../../api/academics';
import { analyticsApi } from '../../api/analytics';
import { announcementsApi } from '../../api/announcements';
import { doubtsApi } from '../../api/doubts';
import StatCard from '../../components/StatCard';
import TruthBanner from '../../components/TruthBanner';
import AiLessonPlanModal from '../../components/teacher/AiLessonPlanModal';
import TeacherNoticeBoard from '../../components/teacher/TeacherNoticeBoard';
import TeacherDoubtHub from '../../components/teacher/TeacherDoubtHub';
import {
  CalendarCheck,
  Award,
  Users,
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  BarChart3,
  Sparkles,
} from 'lucide-react';

export default function TeacherDashboard() {
  const { user, role, teacherProfile, teacherId, activeSession } = useAuth();
  const [assignments, setAssignments] = useState([]);
  const [classes, setClasses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [exams, setExams] = useState([]);
  const [decliningAlerts, setDecliningAlerts] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [doubts, setDoubts] = useState([]);
  const [lessonPlanOpen, setLessonPlanOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const currentTeacherId = teacherId || teacherProfile?.id;
  const sessionId = activeSession?.id;

  const loadData = useCallback(async (isCancelled = () => false) => {
    if (!sessionId || isCancelled()) return;
    setLoading(true);
    try {
      const [asgList, clsList, subjList, examList, annList, doubtList] = await Promise.all([
        currentTeacherId
          ? institutionApi.getTeacherAssignments(currentTeacherId, sessionId).catch(() => [])
          : Promise.resolve([]),
        institutionApi.getClasses(sessionId).catch(() => []),
        institutionApi.getSubjects().catch(() => []),
        academicsApi.getExams({ session_id: sessionId }).catch(() => []),
        announcementsApi.getAnnouncements({ session_id: sessionId }).catch(() => []),
        doubtsApi.getDoubts({ session_id: sessionId }).catch(() => []),
      ]);

      if (isCancelled()) return;

      const asgs = Array.isArray(asgList) ? asgList : [];
      setAssignments(asgs);
      setClasses(Array.isArray(clsList) ? clsList : []);
      setSubjects(Array.isArray(subjList) ? subjList : []);
      setExams(Array.isArray(examList) ? examList : []);
      setAnnouncements(Array.isArray(annList) ? annList : []);
      setDoubts(Array.isArray(doubtList) ? doubtList : []);

      // Load declining performance alerts across assigned classes
      if (asgs.length > 0 && !isCancelled()) {
        const uniqueClassIds = [...new Set(asgs.map((a) => a.class_id))];
        try {
          if (isCancelled()) return;
          const alertPromises = uniqueClassIds.map((cid) =>
            analyticsApi.getDecliningPerformance(cid, sessionId, 2).catch(() => null)
          );
          const results = await Promise.all(alertPromises);
          if (isCancelled()) return;
          const allDeclining = [];
          results.forEach((res) => {
            if (res && Array.isArray(res.declining_students)) {
              allDeclining.push(...res.declining_students);
            }
          });
          setDecliningAlerts(allDeclining);
        } catch (e) {
          console.warn('Declining performance query error:', e);
        }
      } else if (!isCancelled()) {
        setDecliningAlerts([]);
      }
    } catch (err) {
      if (!isCancelled()) {
        console.error('Failed to load teacher dashboard data:', err);
      }
    } finally {
      if (!isCancelled()) {
        setLoading(false);
      }
    }
  }, [currentTeacherId, sessionId]);

  useEffect(() => {
    if (!sessionId) return undefined;
    let cancelled = false;
    const isCancelled = () => cancelled || !localStorage.getItem('access_token');
    loadData(isCancelled);
    return () => {
      cancelled = true;
    };
  }, [sessionId, loadData]);

  const scopedClasses = useMemo(() => {
    if (role === 'ADMINISTRATOR') {
      return classes;
    }
    const assignedIds = new Set(assignments.map((a) => a.class_id));
    return classes.filter((c) => assignedIds.has(c.id));
  }, [classes, assignments, role]);

  const handleAnnouncementCreated = (created) => {
    if (created) {
      setAnnouncements((prev) => [created, ...prev]);
    }
  };

  const handleAnnouncementDeleted = (annId) => {
    setAnnouncements((prev) => prev.filter((a) => a.id !== annId));
  };

  const handleDoubtAnswered = (updated) => {
    if (updated) {
      setDoubts((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    }
  };

  return (
    <div className="space-y-6 min-w-0">
      {/* AI Remedial Lesson Plan Modal (placed first in DOM so its controls precede notice board filters) */}
      <AiLessonPlanModal
        isOpen={lessonPlanOpen}
        onClose={() => setLessonPlanOpen(false)}
        scopedClasses={scopedClasses}
        sessionId={sessionId}
      />

      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 min-w-0">
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-slate-900 tracking-tight break-words">
            Welcome, {teacherProfile?.full_name || user?.username}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Faculty Workspace • Active Session: {activeSession?.name || 'All Sessions'}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setLessonPlanOpen(true)}
          disabled={!sessionId || scopedClasses.length === 0}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50 self-start sm:self-auto shrink-0"
        >
          <Sparkles className="w-4 h-4" />
          AI Remedial Lesson Plan
        </button>
      </div>

      <TruthBanner
        modelVersion="offline-v1.0"
        dataSource="Synthetic Baseline Demonstrator"
        isSynthetic={true}
      />

      {/* Quick Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Teaching Scopes"
          value={assignments.length}
          subtitle={
            scopedClasses.length > 0
              ? `Assigned: ${scopedClasses.map((c) => c.name).join(', ')}`
              : 'Classes & subjects assigned'
          }
          icon={Users}
          color="indigo"
        />
        <StatCard
          title="Scheduled Exams"
          value={exams.length}
          subtitle="In current session"
          icon={Award}
          color="sky"
        />
        <StatCard
          title="Attention Alerts"
          value={decliningAlerts.length}
          subtitle="Students with 2+ consecutive drops"
          icon={TrendingDown}
          color={decliningAlerts.length > 0 ? 'amber' : 'emerald'}
        />
        <StatCard
          title="Session Status"
          value={activeSession?.name || 'Active'}
          subtitle={activeSession?.is_active ? 'Currently active' : 'Archived'}
          icon={CalendarCheck}
          color="emerald"
        />
      </div>

      {/* Main Operations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/teacher/attendance"
          className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-indigo-300 transition group flex flex-col justify-between"
        >
          <div>
            <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
              <CalendarCheck className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-slate-900 group-hover:text-indigo-600 transition">
              Record Attendance
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Mark daily attendance for your assigned class rosters with real-time saved state.
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-indigo-600">
            Open Attendance Sheet &rarr;
          </div>
        </Link>

        <Link
          to="/teacher/marks"
          className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-indigo-300 transition group flex flex-col justify-between"
        >
          <div>
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3">
              <Award className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-slate-900 group-hover:text-indigo-600 transition">
              Enter Exam Marks
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Create evaluations, upload datesheets, import CSV marks, and grade exams cleanly.
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-emerald-600">
            Grade Exams &rarr;
          </div>
        </Link>

        <Link
          to="/teacher/analytics"
          className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-indigo-300 transition group flex flex-col justify-between"
        >
          <div>
            <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
              <BarChart3 className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-slate-900 group-hover:text-indigo-600 transition">
              Analytics &amp; Reports
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Visual attendance trends, subject comparisons, and one-click PDF &amp; Excel exports.
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-blue-600">
            View Analytics &rarr;
          </div>
        </Link>
      </div>

      {/* Performance Watchlist */}
      {decliningAlerts.length > 0 && (
        <div className="bg-white rounded-xl border border-amber-200/80 p-5 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-3 text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <h3 className="font-semibold text-sm">
              Early Attention Watchlist (Declining Performance)
            </h3>
          </div>
          <p className="text-xs text-slate-600 mb-4">
            The following students show 2 or more consecutive score drops in evaluated exams. Review
            individual records for pedagogical support.
          </p>

          <div className="divide-y divide-slate-100">
            {decliningAlerts.map((alert, idx) => (
              <div
                key={`${alert.student_id}-${idx}`}
                className="py-2.5 flex flex-wrap items-center justify-between gap-2 text-xs hover:bg-slate-50 px-2 rounded-lg"
              >
                <div className="min-w-0">
                  <span className="font-semibold text-slate-900">{alert.student_name}</span>
                  <span className="text-slate-400 font-mono ml-2">({alert.admission_number})</span>
                  <span className="ml-3 text-slate-500 font-medium">Subject: {alert.subject_name}</span>
                  <span className="ml-3 text-rose-600 font-medium">
                    {alert.consecutive_declines} consecutive drops (Drop: {alert.score_drop.toFixed(1)} pts)
                  </span>
                </div>
                <Link
                  to={`/teacher/students/${alert.student_id}`}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                >
                  Inspect Profile <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Classroom Notice Board & Student Doubt Hub */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-w-0">
        <TeacherNoticeBoard
          announcements={announcements}
          scopedClasses={scopedClasses}
          sessionId={sessionId}
          currentTeacherId={currentTeacherId}
          role={role}
          onCreated={handleAnnouncementCreated}
          onDeleted={handleAnnouncementDeleted}
        />

        <TeacherDoubtHub
          doubts={doubts}
          subjects={subjects}
          onAnswered={handleDoubtAnswered}
        />
      </div>
    </div>
  );
}
