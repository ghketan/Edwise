import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { academicsApi } from '../../api/academics';
import { institutionApi } from '../../api/institution';
import { analyticsApi } from '../../api/analytics';
import { announcementsApi } from '../../api/announcements';
import { doubtsApi } from '../../api/doubts';
import StatCard from '../../components/StatCard';
import ExamScheduleCard from '../../components/student/ExamScheduleCard';
import NoticeBoardCard from '../../components/student/NoticeBoardCard';
import AttendanceGoalCard from '../../components/student/AttendanceGoalCard';
import AchievementBadgesCard from '../../components/student/AchievementBadgesCard';
import StudentDoubtBox from '../../components/student/StudentDoubtBox';
import WhatIfSimulatorCard from '../../components/student/WhatIfSimulatorCard';
import SubjectPerformanceDiagnostic from '../../components/student/SubjectPerformanceDiagnostic';
import { extractApiError, formatDateOnly } from '../../utils/format';
import {
  CalendarCheck,
  Award,
  BookOpen,
} from 'lucide-react';

export default function StudentDashboard() {
  const { user, studentProfile, studentId, activeSession } = useAuth();
  const [marks, setMarks] = useState([]);
  const [exams, setExams] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [attendance, setAttendance] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [submissions, setSubmissions] = useState({});
  const [announcements, setAnnouncements] = useState([]);
  const [doubts, setDoubts] = useState([]);
  const [attendanceGoal, setAttendanceGoal] = useState(null);
  const [badgeData, setBadgeData] = useState(null);
  const [downloadError, setDownloadError] = useState('');
  const [downloadingExamId, setDownloadingExamId] = useState(null);
  const [loading, setLoading] = useState(true);

  const currentStudentId = studentId || studentProfile?.id;
  const currentClassId = studentProfile?.class_id;
  const sessionId = activeSession?.id;

  const loadStudentData = useCallback(async () => {
    if (!currentStudentId || !sessionId) return;
    setLoading(true);
    setDownloadError('');
    try {
      const [
        markList,
        attList,
        assignList,
        examList,
        subjList,
        annList,
        doubtList,
        goalRes,
        badgesRes,
      ] = await Promise.all([
        academicsApi.getStudentMarks(currentStudentId, sessionId).catch(() => []),
        academicsApi.getAttendance({
          session_id: sessionId,
          student_id: currentStudentId,
        }).catch(() => []),
        currentClassId
          ? academicsApi.getAssignments({
              session_id: sessionId,
              class_id: currentClassId,
            }).catch(() => [])
          : Promise.resolve([]),
        academicsApi.getExams({ session_id: sessionId }).catch(() => []),
        institutionApi.getSubjects().catch(() => []),
        announcementsApi.getAnnouncements({ session_id: sessionId }).catch(() => []),
        doubtsApi.getDoubts({ session_id: sessionId }).catch(() => []),
        analyticsApi.getAttendanceGoal(currentStudentId, sessionId, 75.0).catch(() => null),
        analyticsApi.getStudentBadges(currentStudentId, sessionId).catch(() => null),
      ]);

      setMarks(Array.isArray(markList) ? markList : []);
      setAssignments(Array.isArray(assignList) ? assignList : []);
      setExams(Array.isArray(examList) ? examList : []);
      setSubjects(Array.isArray(subjList) ? subjList : []);
      setAnnouncements(Array.isArray(annList) ? annList : []);
      setDoubts(Array.isArray(doubtList) ? doubtList : []);
      setAttendanceGoal(goalRes || null);
      setBadgeData(badgesRes || null);

      if (Array.isArray(assignList) && assignList.length > 0) {
        const subMap = {};
        await Promise.all(
          assignList.map(async (a) => {
            try {
              const subs = await academicsApi.getSubmissions(a.id);
              if (Array.isArray(subs) && subs.length > 0) {
                const mine = subs.find((s) => s.student_id === currentStudentId) || subs[0];
                if (mine) subMap[a.id] = mine;
              }
            } catch {
              // Ignore
            }
          })
        );
        setSubmissions(subMap);
      }

      if (Array.isArray(attList)) {
        const total = attList.length;
        const present = attList.filter((a) => a.status === 'present').length;
        const late = attList.filter((a) => a.status === 'late').length;
        const absent = attList.filter((a) => a.status === 'absent').length;
        const excused = attList.filter((a) => a.status === 'excused').length;
        const rate = total > 0 ? ((present + late) / total) * 100 : null;
        setAttendance({ total, present, late, absent, excused, rate, records: attList });
      }
    } catch (err) {
      console.error('Error loading student dashboard:', err);
    } finally {
      setLoading(false);
    }
  }, [currentStudentId, currentClassId, sessionId]);

  useEffect(() => {
    if (currentStudentId && sessionId) {
      loadStudentData();
    }
  }, [currentStudentId, sessionId, loadStudentData]);

  const examMap = useMemo(() => {
    const map = {};
    exams.forEach((e) => {
      map[e.id] = e;
    });
    return map;
  }, [exams]);

  const subjectMap = useMemo(() => {
    const map = {};
    subjects.forEach((s) => {
      map[s.id] = s.name;
    });
    return map;
  }, [subjects]);

  const validMarks = marks.filter((m) => {
    const exam = examMap[m.exam_id];
    return m.score !== null && m.score !== undefined && !m.is_absent && exam?.max_marks;
  });

  const avgScore =
    validMarks.length > 0
      ? validMarks.reduce((acc, m) => {
          const max = examMap[m.exam_id].max_marks;
          return acc + (m.score / max) * 100;
        }, 0) / validMarks.length
      : null;

  const handleDownloadDatesheet = async (exam) => {
    setDownloadError('');
    setDownloadingExamId(exam.id);
    try {
      await academicsApi.downloadDatesheet(exam.id, exam.datesheet_filename);
    } catch (err) {
      setDownloadError(extractApiError(err, 'Datesheet file could not be downloaded.'));
    } finally {
      setDownloadingExamId(null);
    }
  };

  const handleDoubtCreated = (created) => {
    if (created) {
      setDoubts((prev) => [created, ...prev]);
    }
  };

  return (
    <div className="space-y-6 min-w-0">
      {/* Student Welcome Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 min-w-0">
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-slate-900 tracking-tight break-words">
            Hello, {studentProfile?.full_name || user?.username}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5 break-words">
            Admission No:{' '}
            <strong className="font-mono text-slate-700">
              {studentProfile?.admission_number || 'Enrolled'}
            </strong>{' '}
            • Class #{studentProfile?.class_id || '1'} • Roll:{' '}
            {studentProfile?.roll_number || 'N/A'}
          </p>
        </div>
        <div className="text-xs bg-slate-100 text-slate-600 px-3 py-1.5 rounded-lg font-medium self-start sm:self-auto shrink-0">
          Session: {activeSession?.name || 'Active Session'}
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 min-w-0">
        <StatCard
          title="Attendance Rate"
          value={
            attendance?.rate !== null && attendance?.rate !== undefined
              ? `${attendance.rate.toFixed(1)}%`
              : 'No Records'
          }
          subtitle={
            attendance?.total > 0
              ? `${attendance.present} present, ${attendance.absent} absent of ${attendance.total} sessions`
              : 'Attendance tracking in progress'
          }
          icon={CalendarCheck}
          color="emerald"
        />
        <StatCard
          title="Average Exam Score"
          value={avgScore !== null ? `${avgScore.toFixed(1)}%` : 'No Evaluated Exams'}
          subtitle={
            validMarks.length > 0
              ? `Calculated across ${validMarks.length} graded exams`
              : 'Scores recorded once evaluated'
          }
          icon={Award}
          color="indigo"
        />
        <StatCard
          title="Coursework Assignments"
          value={assignments.length}
          subtitle="Assignments assigned to your class"
          icon={BookOpen}
          color="sky"
        />
      </div>

      {/* Subject-Wise Performance & Failure Risk Diagnostic */}
      <SubjectPerformanceDiagnostic
        subjects={subjects}
        marks={marks}
        exams={exams}
        attendanceRecords={attendance?.records || []}
        assignments={assignments}
        submissions={submissions}
      />

      {/* Upcoming Exams & Notice Board */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-w-0">
        <ExamScheduleCard
          exams={exams}
          subjectMap={subjectMap}
          onDownloadDatesheet={handleDownloadDatesheet}
          downloadError={downloadError}
          downloadingExamId={downloadingExamId}
        />
        <NoticeBoardCard announcements={announcements} />
      </div>

      {/* Attendance 75% Goal Planner & What-If Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-w-0">
        <AttendanceGoalCard goal={attendanceGoal} />
        <WhatIfSimulatorCard subjects={subjects} />
      </div>

      {/* Achievement Badges */}
      <AchievementBadgesCard badgeData={badgeData} />

      {/* Student Doubt Clearing Box */}
      <StudentDoubtBox
        doubts={doubts}
        subjects={subjects}
        sessionId={sessionId}
        onDoubtCreated={handleDoubtCreated}
      />

      {/* Evaluated Marks History */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm min-w-0">
        <div className="flex items-center gap-2 mb-4 text-indigo-700">
          <Award className="w-4 h-4" />
          <h2 className="font-semibold text-sm text-slate-900">Your Exam Evaluations</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Date</th>
                <th className="py-2.5 px-3 font-semibold">Exam Title</th>
                <th className="py-2.5 px-3 font-semibold">Subject</th>
                <th className="py-2.5 px-3 font-semibold">Score / Max</th>
                <th className="py-2.5 px-3 font-semibold">Percentage</th>
                <th className="py-2.5 px-3 font-semibold">Teacher Feedback</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {loading && marks.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    Loading exam evaluations...
                  </td>
                </tr>
              ) : marks.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    No evaluated exam marks on record for this session.
                  </td>
                </tr>
              ) : (
                marks.map((m) => {
                  const exam = examMap[m.exam_id];
                  const maxMarks = exam ? exam.max_marks : null;
                  const examName = exam ? exam.name : `Exam #${m.exam_id}`;
                  const examDate = exam?.date ? formatDateOnly(exam.date) : formatDateOnly(m.updated_at);
                  const subjectName = exam?.subject_id
                    ? subjectMap[exam.subject_id] || `Subject #${exam.subject_id}`
                    : '—';

                  const pct =
                    m.score !== null && m.score !== undefined && maxMarks
                      ? ((m.score / maxMarks) * 100).toFixed(1)
                      : null;

                  return (
                    <tr key={m.id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-mono">{examDate}</td>
                      <td className="py-2.5 px-3 font-medium text-slate-900">{examName}</td>
                      <td className="py-2.5 px-3">{subjectName}</td>
                      <td className="py-2.5 px-3 font-mono">
                        {m.is_absent ? (
                          <span className="text-rose-600 font-semibold">Absent</span>
                        ) : m.score !== null && m.score !== undefined ? (
                          `${m.score} / ${maxMarks || '—'}`
                        ) : (
                          <span className="text-slate-400 italic">Unrecorded</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 font-semibold">
                        {pct ? (
                          <span
                            className={
                              parseFloat(pct) >= 75
                                ? 'text-emerald-600'
                                : parseFloat(pct) >= 50
                                ? 'text-amber-600'
                                : 'text-rose-600'
                            }
                          >
                            {pct}%
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-slate-500 italic">{m.remarks || '—'}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detailed Attendance Records */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm min-w-0">
        <div className="flex items-center gap-2 mb-4 text-emerald-700">
          <CalendarCheck className="w-4 h-4" />
          <h2 className="font-semibold text-sm text-slate-900">Attendance Log</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="py-2 px-3 font-semibold">Date</th>
                <th className="py-2 px-3 font-semibold">Subject</th>
                <th className="py-2 px-3 font-semibold">Recorded Status</th>
                <th className="py-2 px-3 font-semibold">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {!attendance?.records || attendance.records.length === 0 ? (
                <tr>
                  <td colSpan="4" className="py-6 text-center text-slate-400">
                    No attendance records logged for current session.
                  </td>
                </tr>
              ) : (
                attendance.records.map((att) => {
                  const subjectName = subjectMap[att.subject_id] || `Subject #${att.subject_id}`;
                  return (
                    <tr key={att.id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-mono">{formatDateOnly(att.date)}</td>
                      <td className="py-2.5 px-3 font-medium text-slate-700">{subjectName}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold capitalize ${
                            att.status === 'present'
                              ? 'bg-emerald-100 text-emerald-800'
                              : att.status === 'absent'
                              ? 'bg-rose-100 text-rose-800'
                              : att.status === 'late'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {att.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-500">{att.notes || '—'}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
