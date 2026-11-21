import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { institutionApi } from '../../api/institution';
import { academicsApi } from '../../api/academics';
import { analyticsApi } from '../../api/analytics';
import { mlApi } from '../../api/ml';
import { recommendationApi } from '../../api/recommendations';
import { reportsApi } from '../../api/reports';
import TruthBanner from '../../components/TruthBanner';
import { extractApiError, formatDateOnly, formatUtcTimestamp } from '../../utils/format';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  BrainCircuit,
  FileDown,
  ArrowLeft,
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  Award,
  Sparkles,
  BarChart2,
} from 'lucide-react';

export default function StudentDetail() {
  const { studentId } = useParams();
  const { activeSession, role } = useAuth();

  const [student, setStudent] = useState(null);
  const [marks, setMarks] = useState([]);
  const [exams, setExams] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [estimate, setEstimate] = useState(null);
  const [comparative, setComparative] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reviewMsg, setReviewMsg] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    loadStudentProfile();
  }, [studentId, activeSession]);

  const loadStudentProfile = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const sessionId = activeSession?.id;
      const [stu, markList, recList, examList, subjList, compData] = await Promise.all([
        institutionApi.getStudentById(studentId),
        academicsApi.getStudentMarks(studentId, sessionId),
        recommendationApi.getStudentRecommendations(studentId, sessionId),
        academicsApi.getExams(sessionId ? { session_id: sessionId } : {}).catch(() => []),
        institutionApi.getSubjects().catch(() => []),
        sessionId ? analyticsApi.getStudentVsClass(studentId, sessionId).catch(() => null) : null,
      ]);

      setStudent(stu);
      setMarks(markList || []);
      setRecommendations(recList || []);
      setExams(examList || []);
      setSubjects(subjList || []);
      setComparative(compData);

      // Only Teachers and Admins can query ML estimates (D-012)
      if (role === 'TEACHER' || role === 'ADMINISTRATOR') {
        try {
          const est = await mlApi.getStudentEstimate(studentId, sessionId);
          setEstimate(est);
        } catch (e) {
          console.log('ML estimate unavailable', e);
          setEstimate({
            status: 'model_unavailable',
            estimate_text: 'Predictive model is currently offline or unconfigured.',
          });
        }
      }
    } catch (err) {
      setErrorMsg(extractApiError(err, 'Failed to load student record.'));
    } finally {
      setLoading(false);
    }
  };

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

  const handleReviewAction = async (recId, reviewStatus) => {
    try {
      await recommendationApi.reviewRecommendation(
        recId,
        reviewStatus,
        `Teacher recorded review: ${reviewStatus}`
      );
      setReviewMsg('Action recorded. Does not suppress underlying indicator history.');
      // Refresh recommendations
      const recList = await recommendationApi.getStudentRecommendations(
        studentId,
        activeSession?.id
      );
      setRecommendations(recList || []);
    } catch (err) {
      setReviewMsg(extractApiError(err, 'Failed to record review action.'));
    }
  };

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      await reportsApi.downloadStudentPdf(
        studentId,
        activeSession?.id,
        student?.full_name?.replace(/\s+/g, '_') || 'student'
      );
    } catch (e) {
      alert(extractApiError(e, 'Failed to generate PDF report.'));
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadExcel = async () => {
    setDownloading(true);
    try {
      await reportsApi.downloadStudentExcel(
        studentId,
        activeSession?.id,
        student?.full_name?.replace(/\s+/g, '_') || 'student'
      );
    } catch (e) {
      alert(extractApiError(e, 'Failed to generate Excel report.'));
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="py-12 text-center text-xs text-slate-500">
        Loading student academic profile...
      </div>
    );
  }

  if (errorMsg || !student) {
    return (
      <div className="py-12 text-center text-xs text-rose-600">
        {errorMsg || 'Student record not found or outside your authorized teaching scope (404).'}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button and Profile Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <Link
            to={role === 'TEACHER' ? '/teacher' : '/admin/roster'}
            className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-800 mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-base">
              {student.full_name?.charAt(0) || 'S'}
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                {student.full_name}
              </h1>
              <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                <span className="font-mono">{student.admission_number}</span>
                <span>•</span>
                <span>Roll: {student.roll_number || 'N/A'}</span>
                <span>•</span>
                <span>Class #{student.class_id}</span>
                {student.section_id && <span>• Section #{student.section_id}</span>}
              </div>
            </div>
          </div>
        </div>

        {/* Report Export Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadPdf}
            disabled={downloading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 shadow-sm transition disabled:opacity-50"
          >
            <FileDown className="w-3.5 h-3.5 text-rose-600" /> Download PDF Report
          </button>
          <button
            onClick={handleDownloadExcel}
            disabled={downloading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 shadow-sm transition disabled:opacity-50"
          >
            <FileDown className="w-3.5 h-3.5 text-emerald-600" /> Export Excel
          </button>
        </div>
      </div>

      {reviewMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{reviewMsg}</span>
        </div>
      )}

      {/* Mandatory Playbook Truth Banner (R-015, C-001) */}
      <TruthBanner
        modelVersion={estimate?.model_version || 'v1.0'}
        dataSource={estimate?.data_source_label || 'synthetic-baseline'}
        isSynthetic={estimate?.is_synthetic ?? true}
      />

      {/* ML Performance Estimate (UI-005, R-009, R-010, R-015) */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BrainCircuit className="w-4 h-4 text-indigo-600" />
            <h2 className="font-semibold text-sm text-slate-900">
              Evaluative Performance Estimate (R-009, R-015)
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Data Through:{' '}
            {estimate?.data_through ? formatDateOnly(estimate.data_through) : 'Current Date'}
          </span>
        </div>

        {estimate?.status === 'not_enough_data' ? (
          /* Guarded UI state: Minimum history threshold safeguard */
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/70 p-6 text-center">
            <div className="mx-auto w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 mb-2">
              <HelpCircle className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-sm text-slate-800">Not Enough Data</h3>
            <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto">
              Per architectural safeguard (R-009, D-007), performance prediction requires at least{' '}
              <strong>2 completed exams</strong> in the active session before generating an estimate.
            </p>
            <p className="mt-2 text-[11px] text-slate-400 italic">
              Premature predictions from single data points are disabled to prevent misleading labels.
            </p>
          </div>
        ) : estimate?.status === 'model_unavailable' ? (
          <div className="rounded-xl border border-dashed border-amber-300 bg-amber-50/50 p-6 text-center">
            <div className="mx-auto w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-600 mb-2">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-sm text-amber-800">Model Unavailable</h3>
            <p className="mt-1 text-xs text-amber-700 max-w-md mx-auto">
              {estimate.estimate_text || 'Predictive model is currently unavailable or unconfigured.'}
            </p>
          </div>
        ) : (
          /* Prediction with uncertainty interval and truth language */
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Predicted Performance (Estimate)
              </div>
              <div className="mt-2 text-2xl font-bold text-slate-900">
                {estimate?.value !== null && estimate?.value !== undefined
                  ? `${estimate.value.toFixed(1)}%`
                  : '—'}
              </div>
              {estimate?.interval_lower !== null &&
                estimate?.interval_upper !== null &&
                estimate?.interval_lower !== undefined &&
                estimate?.interval_upper !== undefined && (
                  <div className="mt-1 text-xs text-indigo-600 font-medium">
                    Uncertainty Interval: [{estimate.interval_lower.toFixed(1)}% –{' '}
                    {estimate.interval_upper.toFixed(1)}%]
                  </div>
                )}
              <p className="mt-2 text-[10px] text-slate-400 italic">
                Demonstration baseline • Not an academic verdict
              </p>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Attention Status Indicator
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span
                  className={`text-sm font-bold px-2.5 py-1 rounded-full ${
                    estimate?.risk_level === 'high'
                      ? 'bg-rose-100 text-rose-800 border border-rose-200'
                      : estimate?.risk_level === 'medium'
                      ? 'bg-amber-100 text-amber-800 border border-amber-200'
                      : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                  }`}
                >
                  {estimate?.risk_level === 'high'
                    ? 'Attention Flagged (High Risk)'
                    : estimate?.risk_level === 'medium'
                    ? 'Moderate Risk Pattern'
                    : 'Satisfactory Pattern (Low Risk)'}
                </span>
              </div>
              {estimate?.confidence !== undefined && estimate?.confidence !== null && (
                <div className="mt-2 text-xs text-slate-600">
                  Model Confidence: {(estimate.confidence * 100).toFixed(0)}%
                </div>
              )}
              <p className="mt-2 text-[10px] text-slate-400 italic">
                Derived from synthetic behavioral trends
              </p>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Governing Model Artifact
              </div>
              <div className="mt-2 font-mono text-xs text-slate-800">
                <div>Version: {estimate?.model_version || 'v1.0'}</div>
                <div className="mt-1">Source: {estimate?.data_source_label || 'Synthetic'}</div>
                <div className="mt-1 text-[11px] text-slate-500">Task: Multi-exam regression</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Student vs Class Comparative Analytics (R-007, R-008, §6.2) */}
      {comparative && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-indigo-700">
              <BarChart2 className="w-4 h-4" />
              <h2 className="font-semibold text-sm text-slate-900">
                Student vs. Class Comparative Analytics (R-007, R-008)
              </h2>
            </div>
            <span className="text-[11px] text-slate-400">Class Cohort Benchmark</span>
          </div>

          {/* Quick Metrics Comparison */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5 text-xs">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Student Exam Avg</span>
              <span className="text-base font-bold text-indigo-700">{comparative.overall_percentage.toFixed(1)}%</span>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Class Exam Avg</span>
              <span className="text-base font-bold text-slate-700">{comparative.class_overall_average.toFixed(1)}%</span>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Student Attendance</span>
              <span className="text-base font-bold text-emerald-700">{comparative.attendance_rate.toFixed(1)}%</span>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Class Attendance Avg</span>
              <span className="text-base font-bold text-slate-700">{comparative.class_attendance_average.toFixed(1)}%</span>
            </div>
          </div>

          {/* Comparative Exam Chart */}
          {comparative.exams && comparative.exams.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={comparative.exams.map((e) => ({
                    name: e.exam_name,
                    'Student Score': e.percentage !== null && e.percentage !== undefined ? parseFloat(e.percentage.toFixed(1)) : 0,
                    'Class Average': parseFloat(e.class_average.toFixed(1)),
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(val) => [`${val}%`, '']} />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Bar dataKey="Student Score" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Class Average" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-xs text-slate-400 py-6 text-center">
              No comparative exam records available for this session cohort.
            </p>
          )}
        </div>
      )}

      {/* Rule-based Recommendations (UI-005, R-012, T-014) */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3 text-indigo-700">
          <Sparkles className="w-4 h-4" />
          <h2 className="font-semibold text-sm text-slate-900">
            Actionable Recommendations (Traceable to Indicators)
          </h2>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Each recommendation is triggered by a transparent indicator threshold (e.g. attendance drop
          or consecutive score decline).
        </p>

        {recommendations.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
            No active alerts or recommendations for this student. Academic indicators are within
            standard thresholds.
          </div>
        ) : (
          <div className="space-y-3">
            {recommendations.map((rec) => (
              <div
                key={rec.id}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                        rec.severity === 'high'
                          ? 'bg-rose-100 text-rose-800'
                          : rec.severity === 'medium'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {rec.severity} Severity
                    </span>
                    <span className="font-semibold text-xs text-slate-900">
                      {rec.title || rec.rule_code}
                    </span>
                    {rec.review_status && rec.review_status !== 'pending' && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 font-medium">
                        Reviewed: {rec.review_status}
                      </span>
                    )}
                  </div>
                  <p className="mt-1.5 text-xs text-slate-700">{rec.message}</p>
                  <p className="mt-1 text-[11px] font-mono text-slate-400">
                    Rule Code: {rec.rule_code} • Trigger Value: {rec.trigger_value}
                  </p>
                </div>

                {/* Teacher Review Actions (R-012 human factor) */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleReviewAction(rec.id, 'reviewed_no_action')}
                    className="px-2.5 py-1 text-xs font-medium rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-slate-600 transition shadow-sm"
                  >
                    Reviewed (No Action)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleReviewAction(rec.id, 'action_taken')}
                    className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition shadow-sm"
                  >
                    Take Action
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Exam Marks History */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4 text-indigo-700">
          <Award className="w-4 h-4" />
          <h2 className="font-semibold text-sm text-slate-900">Evaluated Exams & Marks History</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="py-2 px-3 font-semibold">Date</th>
                <th className="py-2 px-3 font-semibold">Exam Title</th>
                <th className="py-2 px-3 font-semibold">Subject</th>
                <th className="py-2 px-3 font-semibold">Score / Max</th>
                <th className="py-2 px-3 font-semibold">Percentage</th>
                <th className="py-2 px-3 font-semibold">Remarks</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {marks.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-4 text-center text-slate-400">
                    No evaluated exam marks on record.
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
                      <td className="py-2.5 px-3 text-slate-500">{m.remarks || '—'}</td>
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
