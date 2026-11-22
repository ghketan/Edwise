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
        attPct,
        attTotal,
        attPresent,
        attAbsent,
        assignAvg,
        subAssignments,
        subCompletedCount,
        assumedScore,
        riskLevel,
        riskColor,
        studyTime,
        needsMoreTime,
        failureAssumptionReason,
      };
    });
  }, [subjects, marks, exams, attendanceRecords, assignments, submissions, examMap]);

  // Set active subject if not set
  const activeSubjectId = selectedSubjectId || (subjects[0] ? subjects[0].id : null);
  const activeDiagnostic = subjectDiagnostics.find((d) => d.subject.id === activeSubjectId);

  if (!subjects || subjects.length === 0) {
    return (
      <section className="glass-card rounded-2xl p-5 shadow-sm min-w-0">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-4 h-4 text-primary shrink-0" />
          <h2 className="font-bold text-sm text-on-surface">Subject Performance Diagnostics</h2>
        </div>
        <div className="py-6 text-center text-xs text-outline border border-dashed border-slate-200 rounded-xl">
          No enrolled subjects found for this session.
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-4">
      {/* Header and Subject Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-primary-container text-white flex items-center justify-center shadow-sm">
            <BookOpen className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-bold text-sm text-on-surface">Subject Diagnostics</h2>
            <p className="text-[11px] text-on-surface-variant">
              Evaluated across your continuous 3-pillar learning framework
            </p>
          </div>
        </div>

        {/* Subject Pill Selector */}
        <div className="inline-flex p-1 bg-surface-container-high/80 rounded-xl backdrop-blur-md overflow-x-auto max-w-full">
          {subjects.map((sub) => {
            const isSelected = sub.id === activeSubjectId;
            return (
              <button
                key={sub.id}
                onClick={() => setSelectedSubjectId(sub.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                  isSelected
                    ? 'bg-surface-container-lowest text-primary shadow-sm font-bold'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {sub.name}
              </button>
            );
          })}
        </div>
      </div>

      {activeDiagnostic && (
        <div className="glass-panel rounded-2xl p-5 flex flex-col gap-4">
          {/* Active Diagnostic Title & Confidence Pill */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-glass-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-status-sky-bg text-secondary flex items-center justify-center shadow-inner">
                <Award className="w-5 h-5 text-secondary" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-sm text-on-surface">
                    {activeDiagnostic.subject.name} Core
                  </h3>
                  <span className="px-2 py-0.5 rounded-full bg-status-emerald-bg text-status-emerald-text text-[10px] font-bold font-mono">
                    Active Diagnostic
                  </span>
                </div>
                <p className="text-[11px] text-outline">
                  Code: {activeDiagnostic.subject.code || `SUB${activeDiagnostic.subject.id}`} • Institutional Weightage: 1.0
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface-container-low text-on-surface text-xs font-mono">
                <span className="text-[10px] uppercase font-bold text-outline">Assumed Score:</span>
                <span className="font-bold text-primary">
                  {activeDiagnostic.assumedScore.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>

          {/* Failure Assumption Alert & Study Time Card */}
          <div
            className={`p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
              activeDiagnostic.riskColor === 'rose'
                ? 'bg-status-rose-bg/80 border-rose-200 text-status-rose-text'
                : activeDiagnostic.riskColor === 'amber'
                ? 'bg-status-amber-bg/80 border-amber-200 text-status-amber-text'
                : 'bg-status-emerald-bg/80 border-emerald-200 text-status-emerald-text'
            }`}
          >
            <div className="flex items-start gap-2.5 min-w-0">
              {activeDiagnostic.riskColor === 'rose' ? (
                <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              ) : activeDiagnostic.riskColor === 'amber' ? (
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              )}
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-xs uppercase tracking-wide">
                    {activeDiagnostic.riskLevel}
                  </span>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white/70 border border-current">
                    Pillar Analysis
                  </span>
                </div>
                <p className="text-xs mt-0.5 leading-relaxed font-medium">
                  {activeDiagnostic.failureAssumptionReason}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0 self-start sm:self-center bg-white/80 px-3 py-1.5 rounded-xl border border-current shadow-xs">
              <Clock className="w-4 h-4 text-primary" />
              <div className="text-left font-mono">
                <div className="text-[9px] uppercase font-bold text-outline">Recommended Study</div>
                <div className="text-xs font-bold text-on-surface">{activeDiagnostic.studyTime}</div>
              </div>
            </div>
          </div>

          {/* 3 Pillars Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Pillar 1: Exams */}
            <div className="glass-card p-4 rounded-xl flex flex-col justify-between gap-2">
              <div>
                <div className="flex items-center justify-between text-xs font-bold text-on-surface">
                  <span className="flex items-center gap-1.5">
                    <Award className="w-4 h-4 text-primary" /> Evaluated Exams
                  </span>
                  <span className="font-mono text-primary font-bold">
                    {activeDiagnostic.examAvg !== null ? `${activeDiagnostic.examAvg.toFixed(1)}%` : 'No data'}
                  </span>
                </div>
                <p className="text-[11px] text-on-surface-variant mt-1">
                  {activeDiagnostic.gradedMarksCount} evaluated exams on record for {activeDiagnostic.subject.name}.
                </p>
              </div>
              {activeDiagnostic.subMarks.length > 0 && (
                <div className="text-[11px] space-y-1 pt-2 border-t border-slate-100 font-mono">
                  {activeDiagnostic.subMarks.slice(0, 3).map((m) => {
                    const ex = examMap[m.exam_id];
                    return (
                      <div key={m.id} className="flex justify-between text-on-surface-variant">
                        <span className="truncate max-w-[130px] font-sans">{ex?.name || `Exam #${m.exam_id}`}</span>
                        <span className="font-bold">
                          {m.is_absent ? (
                            <span className="text-status-rose-text">Absent</span>
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
            <div className="glass-card p-4 rounded-xl flex flex-col justify-between gap-2">
              <div>
                <div className="flex items-center justify-between text-xs font-bold text-on-surface">
                  <span className="flex items-center gap-1.5">
                    <CalendarCheck className="w-4 h-4 text-status-emerald-text" /> Subject Attendance
                  </span>
                  <span
                    className={`font-mono font-bold ${
                      activeDiagnostic.attPct !== null && activeDiagnostic.attPct < 75
                        ? 'text-status-rose-text'
                        : 'text-status-emerald-text'
                    }`}
                  >
                    {activeDiagnostic.attPct !== null ? `${activeDiagnostic.attPct.toFixed(1)}%` : 'No records'}
                  </span>
                </div>
                <p className="text-[11px] text-on-surface-variant mt-1">
                  {activeDiagnostic.attPresent} attended of {activeDiagnostic.attTotal} sessions held in this subject.
                </p>
              </div>
              <div className="text-[11px] pt-2 border-t border-slate-100 flex justify-between text-on-surface-variant font-mono">
                <span>Absences: <strong className="text-status-rose-text">{activeDiagnostic.attAbsent}</strong></span>
                <span>Target: <strong>75%</strong></span>
              </div>
            </div>

            {/* Pillar 3: Coursework */}
            <div className="glass-card p-4 rounded-xl flex flex-col justify-between gap-2">
              <div>
                <div className="flex items-center justify-between text-xs font-bold text-on-surface">
                  <span className="flex items-center gap-1.5">
                    <FileCheck className="w-4 h-4 text-secondary" /> Coursework Tasks
                  </span>
                  <span className="font-mono text-secondary font-bold">
                    {activeDiagnostic.subCompletedCount}/{activeDiagnostic.subAssignments.length}
                  </span>
                </div>
                <p className="text-[11px] text-on-surface-variant mt-1">
                  {activeDiagnostic.assignAvg !== null
                    ? `Average score: ${activeDiagnostic.assignAvg.toFixed(1)}% on turned in homework.`
                    : 'Turn in solutions in assignments to boost your score.'}
                </p>
              </div>
              <div className="text-[11px] pt-2 border-t border-slate-100 text-on-surface-variant font-mono">
                Status: {activeDiagnostic.subCompletedCount === activeDiagnostic.subAssignments.length ? (
                  <span className="text-status-emerald-text font-bold">All coursework completed</span>
                ) : (
                  <span className="text-status-amber-text font-bold">
                    {activeDiagnostic.subAssignments.length - activeDiagnostic.subCompletedCount} pending submission
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
