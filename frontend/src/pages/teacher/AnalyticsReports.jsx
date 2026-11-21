import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { institutionApi } from '../../api/institution';
import { academicsApi } from '../../api/academics';
import { analyticsApi } from '../../api/analytics';
import { mlApi } from '../../api/ml';
import { reportsApi } from '../../api/reports';
import TruthBanner from '../../components/TruthBanner';
import { extractApiError } from '../../utils/format';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import { BarChart3, FileDown, TrendingUp, Users, BrainCircuit, Layers } from 'lucide-react';

export default function AnalyticsReports() {
  const { activeSession, role, teacherProfile, teacherId } = useAuth();
  const [classes, setClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState('');
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState('');
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');

  // Analytics data
  const [attendanceAnalytics, setAttendanceAnalytics] = useState(null);
  const [examAnalytics, setExamAnalytics] = useState(null);
  const [clusterData, setClusterData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const sessionId = activeSession?.id;

  // Load clusters for session (R-011)
  useEffect(() => {
    if (!sessionId) return undefined;
    let cancelled = false;
    const timer = setTimeout(() => {
      if (cancelled) return;
      mlApi
        .getClusters(sessionId)
        .then((data) => {
          if (!cancelled) setClusterData(data);
        })
        .catch((err) => {
          if (!cancelled) console.warn('Cluster analysis unavailable:', err);
        });
    }, 60);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [sessionId]);

  // Load classes
  useEffect(() => {
    institutionApi
      .getClasses(sessionId)
      .then((clsList) => {
        if (Array.isArray(clsList) && clsList.length > 0) {
          setClasses(clsList);
          setSelectedClass(String(clsList[0].id));
        }
      })
      .catch((err) => {
        console.error('Failed to load classes:', err);
      });
  }, [sessionId]);

  // When class changes, load students and exams
  useEffect(() => {
    if (!selectedClass) return;
    const cid = parseInt(selectedClass, 10);

    Promise.all([
      institutionApi.getStudents(cid).catch(() => []),
      academicsApi.getExams(sessionId ? { session_id: sessionId, class_id: cid } : { class_id: cid }).catch(() => []),
    ]).then(([stuList, examList]) => {
      setStudents(stuList || []);
      if (stuList && stuList.length > 0) {
        setSelectedStudent(String(stuList[0].id));
      } else {
        setSelectedStudent('');
      }

      setExams(examList || []);
      if (examList && examList.length > 0) {
        setSelectedExamId(String(examList[0].id));
      } else {
        setSelectedExamId('');
      }
    });
  }, [selectedClass, sessionId]);

  // Load attendance analytics for selected class
  useEffect(() => {
    if (!selectedClass || !sessionId) return;
    setLoading(true);
    setErrorMsg('');

    analyticsApi
      .getAttendanceAnalytics({
        session_id: sessionId,
        class_id: parseInt(selectedClass, 10),
      })
      .then((data) => {
        setAttendanceAnalytics(data);
      })
      .catch((err) => {
        setErrorMsg(extractApiError(err, 'Failed to load attendance analytics.'));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [selectedClass, sessionId]);

  // Load exam analytics when selected exam changes
  useEffect(() => {
    if (!selectedExamId) {
      setExamAnalytics(null);
      return;
    }

    analyticsApi
      .getExamAnalytics(parseInt(selectedExamId, 10))
      .then((data) => {
        setExamAnalytics(data);
      })
      .catch((err) => {
        console.warn('Failed to load exam analytics:', err);
        setExamAnalytics(null);
      });
  }, [selectedExamId]);

  const handleDownloadClassExcel = async () => {
    if (!selectedClass) return;
    setDownloading(true);
    try {
      const clsObj = classes.find((c) => c.id === parseInt(selectedClass, 10));
      await reportsApi.downloadClassExcel(
        parseInt(selectedClass, 10),
        activeSession?.id,
        null,
        clsObj ? clsObj.name.replace(/\s+/g, '_') : 'class'
      );
    } catch (e) {
      alert(extractApiError(e, 'Failed to generate Class Excel report.'));
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadStudentPdf = async () => {
    if (!selectedStudent) return;
    setDownloading(true);
    try {
      const stuObj = students.find((s) => s.id === parseInt(selectedStudent, 10));
      await reportsApi.downloadStudentPdf(
        parseInt(selectedStudent, 10),
        activeSession?.id,
        stuObj ? stuObj.full_name.replace(/\s+/g, '_') : 'student'
      );
    } catch (e) {
      alert(extractApiError(e, 'Failed to generate Student PDF report.'));
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadStudentExcel = async () => {
    if (!selectedStudent) return;
    setDownloading(true);
    try {
      const stuObj = students.find((s) => s.id === parseInt(selectedStudent, 10));
      await reportsApi.downloadStudentExcel(
        parseInt(selectedStudent, 10),
        activeSession?.id,
        stuObj ? stuObj.full_name.replace(/\s+/g, '_') : 'student'
      );
    } catch (e) {
      alert(extractApiError(e, 'Failed to generate Student Excel report.'));
    } finally {
      setDownloading(false);
    }
  };

  const subjectAttendanceData = attendanceAnalytics?.by_subject?.map((s) => ({
    name: s.subject_name,
    rate: parseFloat((s.attendance_rate * 100).toFixed(1)),
  })) || [];

  const trendData = attendanceAnalytics?.trends?.map((t) => ({
    period: t.period,
    rate: parseFloat((t.attendance_rate * 100).toFixed(1)),
  })) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Academic Analytics & Reports Center
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Aggregated curriculum performance, score distributions, and official exports (R-008, R-013, UI-007).
          </p>
        </div>

        {/* Filter Selection */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500 font-medium">Target Class:</label>
          <select
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <TruthBanner
        modelVersion="offline-v1.0"
        dataSource="Class Aggregate Analytics Fixtures"
        isSynthetic={true}
      />

      {errorMsg && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-xs text-rose-800 rounded-lg">
          {errorMsg}
        </div>
      )}

      {/* Reports Export Hub (UI-007) */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">
          Instant Report Downloads (ReportLab & OpenPyXL)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-900">Class Performance Excel</div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Full roster marks, attendance percentages, and subject grade breakdown.
              </p>
            </div>
            <button
              onClick={handleDownloadClassExcel}
              disabled={downloading || !selectedClass}
              className="mt-3 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition disabled:opacity-50"
            >
              <FileDown className="w-3.5 h-3.5" /> Export Class Spreadsheet
            </button>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-900">Student Progress PDF</div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Formatted academic evaluation sheet with official institutional header and synthetic notice.
              </p>
            </div>
            <div className="mt-2 flex gap-2">
              <select
                value={selectedStudent}
                onChange={(e) => setSelectedStudent(e.target.value)}
                className="flex-1 text-[11px] px-2 py-1 rounded border border-slate-300 bg-white focus:outline-none"
              >
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name} ({s.admission_number})
                  </option>
                ))}
              </select>
              <button
                onClick={handleDownloadStudentPdf}
                disabled={downloading || !selectedStudent}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition disabled:opacity-50"
              >
                <FileDown className="w-3.5 h-3.5" /> PDF
              </button>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-900">Individual Student Excel</div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Detailed spreadsheet with sanitized formula injection defense (H-07).
              </p>
            </div>
            <button
              onClick={handleDownloadStudentExcel}
              disabled={downloading || !selectedStudent}
              className="mt-3 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50"
            >
              <FileDown className="w-3.5 h-3.5" /> Download Student Excel
            </button>
          </div>
        </div>
      </div>

      {/* Visual Charts Grid (Recharts) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Attendance by Subject */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-indigo-700">
              <Users className="w-4 h-4" />
              <h3 className="font-semibold text-sm text-slate-900">
                Attendance Rate by Subject (%)
              </h3>
            </div>
            {attendanceAnalytics && (
              <span className="text-xs font-semibold text-slate-600">
                Overall: {(attendanceAnalytics.overall_attendance_rate * 100).toFixed(1)}%
              </span>
            )}
          </div>
          <div className="h-64 w-full">
            {subjectAttendanceData.length === 0 ? (
              <p className="text-xs text-slate-400 py-24 text-center">No attendance subject records.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={subjectAttendanceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(val) => [`${val}%`, 'Attendance Rate']} />
                  <Bar dataKey="rate" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Attendance Trend Line */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-emerald-700">
              <TrendingUp className="w-4 h-4" />
              <h3 className="font-semibold text-sm text-slate-900">
                Attendance Trends Over Time
              </h3>
            </div>
          </div>
          <div className="h-64 w-full">
            {trendData.length === 0 ? (
              <p className="text-xs text-slate-400 py-24 text-center">No temporal trend data recorded.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(val) => [`${val}%`, 'Attendance Rate']} />
                  <Line type="monotone" dataKey="rate" stroke="#10b981" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Exam Distribution Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        {exams.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {exams.map((ex) => {
              const isSelected = String(ex.id) === String(selectedExamId);
              return (
                <button
                  key={ex.id}
                  type="button"
                  onClick={() => setSelectedExamId(String(ex.id))}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition ${
                    isSelected
                      ? 'bg-indigo-50 text-indigo-700 border-indigo-200 font-semibold'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {ex.name}
                </button>
              );
            })}
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2 text-indigo-700">
            <BarChart3 className="w-4 h-4" />
            <h3 className="font-semibold text-sm text-slate-900">
              Exam Score Distribution & Evaluation Analytics
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-500">Select Exam:</label>
            <select
              value={selectedExamId}
              onChange={(e) => setSelectedExamId(e.target.value)}
              className="text-xs font-medium px-2.5 py-1 rounded border border-slate-300 bg-white focus:outline-none"
            >
              {exams.length === 0 && <option value="">No exams for class</option>}
              {exams.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name} (Max: {e.max_marks})
                </option>
              ))}
            </select>
          </div>
        </div>

        {examAnalytics ? (
          <div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4 text-xs">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Average</span>
                <span className="text-base font-bold text-slate-900">{examAnalytics.average_score.toFixed(1)}</span>
                <span className="text-slate-400 text-[10px]"> / {examAnalytics.max_marks}</span>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Median</span>
                <span className="text-base font-bold text-slate-900">{examAnalytics.median_score.toFixed(1)}</span>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Pass Rate</span>
                <span className="text-base font-bold text-emerald-600">{(examAnalytics.pass_rate * 100).toFixed(1)}%</span>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Highest</span>
                <span className="text-base font-bold text-indigo-600">{examAnalytics.highest_score}</span>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Lowest</span>
                <span className="text-base font-bold text-rose-600">{examAnalytics.lowest_score}</span>
              </div>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={examAnalytics.distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="range_label" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(val, name, item) => [`${val} students (${item.payload.percentage.toFixed(1)}%)`, 'Count']} />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-400 py-12 text-center">
            Select an exam with evaluated student marks to display distribution analytics.
          </p>
        )}
      </div>

      {/* K-Means Academic Engagement Cluster Exploration (R-011, §8.4) */}
      {clusterData && clusterData.clusters && clusterData.clusters.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2 text-indigo-700">
              <Layers className="w-4 h-4" />
              <div>
                <h3 className="font-semibold text-sm text-slate-900">
                  K-Means Engagement Pattern Exploration (R-011)
                </h3>
                <p className="text-[11px] text-slate-400">
                  Exploratory pattern analysis across session behavioral indicators • Model v{clusterData.model_version}
                </p>
              </div>
            </div>
            <span className="text-xs font-mono font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg">
              {clusterData.n_clusters} Engagement Clusters
            </span>
          </div>

          {/* Truth Safeguard Note (R-011) */}
          <div className="p-3 bg-indigo-50/60 border border-indigo-200/60 rounded-xl text-xs text-indigo-900 leading-relaxed">
            <p className="font-semibold mb-0.5">Exploratory Pattern Notice:</p>
            <p className="text-indigo-800 text-[11px]">{clusterData.note}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {clusterData.clusters.map((c) => {
              const att = c.feature_means?.attendance_rate || 0;
              const exam = c.feature_means?.prior_exam_avg || 0;
              const asg = c.feature_means?.assignment_rate || 0;

              return (
                <div
                  key={c.cluster_id}
                  className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-xs text-slate-900">{c.cluster_label}</span>
                      <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                        {c.student_count} Students
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-600 italic mb-4 leading-relaxed">
                      "{c.description}"
                    </p>

                    <div className="space-y-2.5 text-xs">
                      <div>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-500">Attendance Mean:</span>
                          <span className="font-semibold font-mono text-slate-800">{att}%</span>
                        </div>
                        <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-emerald-500 h-full rounded-full"
                            style={{ width: `${Math.min(100, Math.max(0, att))}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-500">Prior Exam Avg:</span>
                          <span className="font-semibold font-mono text-slate-800">{exam}%</span>
                        </div>
                        <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-indigo-500 h-full rounded-full"
                            style={{ width: `${Math.min(100, Math.max(0, exam))}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-500">Assignment Completion:</span>
                          <span className="font-semibold font-mono text-slate-800">{asg}%</span>
                        </div>
                        <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-sky-500 h-full rounded-full"
                            style={{ width: `${Math.min(100, Math.max(0, asg))}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-200/60 text-[10px] text-slate-400 font-mono">
                    Cluster Center ID #{c.cluster_id}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
