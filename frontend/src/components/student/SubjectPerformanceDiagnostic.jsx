import React, { useState, useMemo } from 'react';
import {
  BookOpen,
  AlertTriangle,
  CheckCircle2,
  Clock,
  TrendingUp,
  Award,
  CalendarCheck,
  FileCheck,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';

export default function SubjectPerformanceDiagnostic({
  subjects = [],
  marks = [],
  exams = [],
  attendanceRecords = [],
  assignments = [],
  submissions = {},
}) {
  const [selectedSubjectId, setSelectedSubjectId] = useState(null);

  // Map exam by ID
  const examMap = useMemo(() => {
    const map = {};
    exams.forEach((e) => {
      map[e.id] = e;
    });
    return map;
  }, [exams]);

  // Compute diagnostics per subject
  const subjectDiagnostics = useMemo(() => {
    if (!Array.isArray(subjects) || subjects.length === 0) return [];

    return subjects.map((sub) => {
      // 1. Exam Performance
      const subExams = exams.filter((e) => e.subject_id === sub.id);
      const subMarks = marks.filter((m) => {
        const ex = examMap[m.exam_id];
        return ex && ex.subject_id === sub.id;
      });

      const gradedMarks = subMarks.filter(
        (m) => m.score !== null && m.score !== undefined && !m.is_absent
      );

      let examAvg = null;
      if (gradedMarks.length > 0) {
        const totalPct = gradedMarks.reduce((acc, m) => {
          const max = examMap[m.exam_id]?.max_marks || 100;
          return acc + (m.score / max) * 100;
        }, 0);
        examAvg = totalPct / gradedMarks.length;
      }

      // 2. Attendance Performance
      const subAtt = attendanceRecords.filter((a) => a.subject_id === sub.id);
      const attTotal = subAtt.length;
      const attPresent = subAtt.filter((a) => a.status === 'present' || a.status === 'late').length;
      const attAbsent = subAtt.filter((a) => a.status === 'absent').length;
      const attPct = attTotal > 0 ? (attPresent / attTotal) * 100 : null;

      // 3. Assignment Performance
      const subAssignments = assignments.filter((a) => a.subject_id === sub.id);
      const subCompletedCount = subAssignments.filter((a) => {
        const s = submissions[a.id];
        return s && (s.status === 'graded' || s.status === 'submitted');
      }).length;

      let assignAvg = null;
      const gradedSubs = subAssignments
        .map((a) => submissions[a.id])
        .filter((s) => s && s.status === 'graded' && s.points_awarded !== null);

      if (gradedSubs.length > 0) {
        const totalAssignPct = gradedSubs.reduce((acc, s) => {
          const asg = subAssignments.find((a) => a.id === s.assignment_id);
          const maxPts = asg?.max_points || 100;
          return acc + (s.points_awarded / maxPts) * 100;
        }, 0);
        assignAvg = totalAssignPct / gradedSubs.length;
      }

      // 4. Composite Assumed Score & Failure Risk Assumption
      // Default to 70% if no data yet to avoid false alarm before evaluations start
      let assumedScore = 70.0;
      let scoreComponents = 0;
      let weightedSum = 0;

      if (examAvg !== null) {
        weightedSum += examAvg * 0.55;
        scoreComponents += 0.55;
      }
      if (attPct !== null) {
        weightedSum += attPct * 0.25;
        scoreComponents += 0.25;
      }
      if (assignAvg !== null) {
        weightedSum += assignAvg * 0.20;
        scoreComponents += 0.20;
      }

      if (scoreComponents > 0) {
        assumedScore = weightedSum / scoreComponents;
      }

      // Failure Risk Classification
      let riskLevel = 'Low Risk';
      let riskColor = 'emerald';
      let studyTime = '45 min/day';
      let needsMoreTime = false;
      let failureAssumptionReason = 'Consistent performance across exam scores and attendance.';

      if (assumedScore < 40 || (attPct !== null && attPct < 65)) {
        riskLevel = 'High Risk of Failure';
        riskColor = 'rose';
        studyTime = '2.5 to 3.0 hrs/day';
        needsMoreTime = true;
        if (attPct !== null && attPct < 65) {
          failureAssumptionReason = `Critical attendance deficit (${attPct.toFixed(1)}%). Below 65% mandatory threshold.`;
        } else {
          failureAssumptionReason = `Current projected score (${assumedScore.toFixed(1)}%) is below the minimum 40% passing benchmark.`;
        }
      } else if (assumedScore < 60 || (attPct !== null && attPct < 75)) {
        riskLevel = 'Moderate Risk / Warning';
        riskColor = 'amber';
        studyTime = '1.5 hrs/day';
        needsMoreTime = true;
        if (attPct !== null && attPct < 75) {
          failureAssumptionReason = `Attendance is at ${attPct.toFixed(1)}%, below the 75% CBSE safe zone requirement.`;
        } else {
          failureAssumptionReason = `Projected score of ${assumedScore.toFixed(1)}% requires revision to avoid danger zone.`;
        }
      }

      return {
        subject: sub,
        examAvg,
        gradedMarksCount: gradedMarks.length,
        subMarks,
        attTotal,
        attPresent,
        attAbsent,
        attPct,
        subAssignments,
        subCompletedCount,
        assignAvg,
        assumedScore,
        riskLevel,
        riskColor,
        studyTime,
        needsMoreTime,
        failureAssumptionReason,
      };
    });
  }, [subjects, marks, exams, attendanceRecords, assignments, submissions, examMap]);

  const activeDiagnostic = useMemo(() => {
    if (!selectedSubjectId) return subjectDiagnostics[0] || null;
    return subjectDiagnostics.find((d) => String(d.subject.id) === String(selectedSubjectId)) || null;
  }, [selectedSubjectId, subjectDiagnostics]);

  if (subjectDiagnostics.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-5 min-w-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-2.5 text-indigo-700">
          <BookOpen className="w-5 h-5 shrink-0" />
          <div>
            <h2 className="font-bold text-sm text-slate-900 tracking-tight">
              Subject-Wise Academic Diagnostic &amp; Failure Risk Forecast
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Subject-level breakdown of exam grades, attendance rate, assignment completion, assumed scores, and study time priorities.
            </p>
          </div>
        </div>
      </div>

      {/* Grid of Subject Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {subjectDiagnostics.map((diag) => {
          const isSelected = activeDiagnostic?.subject.id === diag.subject.id;

          return (
            <div
              key={diag.subject.id}
              onClick={() => setSelectedSubjectId(String(diag.subject.id))}
              className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? 'border-indigo-600 bg-indigo-50/40 shadow-sm ring-1 ring-indigo-500'
                  : 'border-slate-200 bg-white hover:border-indigo-300 hover:bg-slate-50/50'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="font-mono text-[11px] font-bold text-indigo-600 px-2 py-0.5 rounded bg-indigo-50 border border-indigo-100">
                    {diag.subject.code}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      diag.riskColor === 'rose'
                        ? 'bg-rose-100 text-rose-800 border border-rose-200'
                        : diag.riskColor === 'amber'
                        ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}
                  >
                    {diag.riskColor === 'rose' ? 'High Risk' : diag.riskColor === 'amber' ? 'Moderate Risk' : 'On Track'}
                  </span>
                </div>

                <h3 className="font-bold text-sm text-slate-900 line-clamp-1 mb-1">
                  {diag.subject.name}
                </h3>

                {/* Assumed Score Progress */}
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-slate-500 text-[11px]">Assumed Score</span>
                    <span className="font-bold font-mono text-slate-900">
                      {diag.assumedScore.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        diag.assumedScore < 40
                          ? 'bg-rose-500'
                          : diag.assumedScore < 60
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(5, diag.assumedScore))}%` }}
                    />
                  </div>
                </div>

                {/* Metrics Breakdown */}
                <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
                  <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                    <span className="text-slate-500 block">Attendance</span>
                    <strong
                      className={`font-mono text-xs ${
                        diag.attPct === null
                          ? 'text-slate-400'
                          : diag.attPct < 75
                          ? 'text-rose-600'
                          : 'text-slate-800'
                      }`}
                    >
                      {diag.attPct !== null ? `${diag.attPct.toFixed(0)}%` : 'No data'}
                    </strong>
                  </div>
                  <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                    <span className="text-slate-500 block">Exam Avg</span>
                    <strong className="font-mono text-xs text-slate-800">
                      {diag.examAvg !== null ? `${diag.examAvg.toFixed(0)}%` : 'Pending'}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Study Time Recommendation */}
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-[11px] text-slate-500 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-indigo-600" /> Study Time:
                </span>
                <span
                  className={`font-semibold text-[11px] ${
                    diag.needsMoreTime ? 'text-rose-700 font-bold' : 'text-slate-700'
                  }`}
                >
                  {diag.studyTime}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Subject Detailed Inspector */}
      {activeDiagnostic && (
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200/70 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-indigo-700 bg-indigo-100/70 px-2 py-0.5 rounded">
                  {activeDiagnostic.subject.code}
                </span>
                <h3 className="font-bold text-base text-slate-900">
                  {activeDiagnostic.subject.name} Detailed Analysis
                </h3>
              </div>
              <p className="text-xs text-slate-600 mt-1">
                {activeDiagnostic.failureAssumptionReason}
              </p>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto">
              {activeDiagnostic.needsMoreTime && (
                <span className="px-3 py-1 rounded-lg bg-rose-100 text-rose-800 text-xs font-bold border border-rose-200 flex items-center gap-1.5 animate-pulse">
                  <AlertTriangle className="w-4 h-4 text-rose-600" /> Needs Immediate Study Time
                </span>
              )}
              <div className="text-xs px-3 py-1 bg-white border border-slate-200 rounded-lg text-slate-700">
                Recommended Study: <strong className="text-indigo-600">{activeDiagnostic.studyTime}</strong>
              </div>
            </div>
          </div>

          {/* 3 Pillars Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Pillar 1: Exams */}
            <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <span className="flex items-center gap-1.5">
                  <Award className="w-4 h-4 text-indigo-600" /> Evaluated Exams
                </span>
                <span className="font-mono text-indigo-700 font-bold">
                  {activeDiagnostic.examAvg !== null ? `${activeDiagnostic.examAvg.toFixed(1)}%` : 'No data'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                {activeDiagnostic.gradedMarksCount} evaluated exams on record for {activeDiagnostic.subject.name}.
              </p>
              {activeDiagnostic.subMarks.length > 0 && (
                <div className="text-[11px] space-y-1 pt-1 border-t border-slate-100">
                  {activeDiagnostic.subMarks.slice(0, 3).map((m) => {
                    const ex = examMap[m.exam_id];
                    return (
                      <div key={m.id} className="flex justify-between text-slate-600">
                        <span className="truncate max-w-[130px]">{ex?.name || `Exam #${m.exam_id}`}</span>
                        <span className="font-mono font-medium">
                          {m.is_absent ? (
                            <span className="text-rose-600">Absent</span>
                          ) : m.score !== null ? (
                            `${m.score}/${ex?.max_marks || 100}`
                          ) : (
                            'Pending'
                          )}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Pillar 2: Attendance */}
            <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <span className="flex items-center gap-1.5">
                  <CalendarCheck className="w-4 h-4 text-emerald-600" /> Subject Attendance
                </span>
                <span
                  className={`font-mono font-bold ${
                    activeDiagnostic.attPct !== null && activeDiagnostic.attPct < 75
                      ? 'text-rose-600'
                      : 'text-emerald-700'
                  }`}
                >
                  {activeDiagnostic.attPct !== null ? `${activeDiagnostic.attPct.toFixed(1)}%` : 'No records'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                {activeDiagnostic.attPresent} attended of {activeDiagnostic.attTotal} sessions held in this subject.
              </p>
              <div className="text-[11px] pt-1 border-t border-slate-100 flex justify-between text-slate-600">
                <span>Absences: <strong className="text-rose-600">{activeDiagnostic.attAbsent}</strong></span>
                <span>Requirement: <strong>75%</strong></span>
              </div>
            </div>

            {/* Pillar 3: Coursework */}
            <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <span className="flex items-center gap-1.5">
                  <FileCheck className="w-4 h-4 text-sky-600" /> Coursework Assignments
                </span>
                <span className="font-mono text-sky-700 font-bold">
                  {activeDiagnostic.subCompletedCount}/{activeDiagnostic.subAssignments.length}
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                {activeDiagnostic.assignAvg !== null
                  ? `Average score: ${activeDiagnostic.assignAvg.toFixed(1)}% on turned in homework.`
                  : 'Turn in solutions in the assignments tab to boost your score.'}
              </p>
              <div className="text-[11px] pt-1 border-t border-slate-100 text-slate-600">
                Status: {activeDiagnostic.subCompletedCount === activeDiagnostic.subAssignments.length ? (
                  <span className="text-emerald-600 font-medium">All coursework completed</span>
                ) : (
                  <span className="text-amber-600 font-medium">{activeDiagnostic.subAssignments.length - activeDiagnostic.subCompletedCount} pending submission</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
