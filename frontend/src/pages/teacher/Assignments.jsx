import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { institutionApi } from '../../api/institution';
import { academicsApi } from '../../api/academics';
import { extractApiError, getLocalDateTimeInput, formatUtcTimestamp } from '../../utils/format';
import { BookOpen, Plus, CheckCircle, Clock, AlertCircle, Link2, ExternalLink } from 'lucide-react';

export default function TeacherAssignments() {
  const { teacherProfile, teacherId, activeSession } = useAuth();
  const [scopes, setScopes] = useState([]);
  const [selectedScope, setSelectedScope] = useState('');
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [students, setStudents] = useState([]);

  // Create assignment form
  const [showCreate, setShowCreate] = useState(false);
  const [newAssign, setNewAssign] = useState({
    title: '',
    description: '',
    max_points: 100,
    due_date: getLocalDateTimeInput(new Date(Date.now() + 7 * 86400000)),
  });

  // Grade state
  const [gradingSubId, setGradingSubId] = useState(null);
  const [gradePoints, setGradePoints] = useState('');
  const [gradeFeedback, setGradeFeedback] = useState('');

  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState({ text: '', type: '' });

  const currentTeacherId = teacherId || teacherProfile?.id;

  useEffect(() => {
    if (currentTeacherId) {
      institutionApi
        .getTeacherAssignments(currentTeacherId, activeSession?.id)
        .then((asgs) => {
          if (Array.isArray(asgs)) {
            setScopes(asgs);
            if (asgs.length > 0) setSelectedScope(String(asgs[0].id));
          }
        })
        .catch((err) => {
          console.error('Failed to load teacher assignments:', err);
        });
    }
  }, [currentTeacherId, activeSession]);

  useEffect(() => {
    if (!selectedScope) return;
    const currentScope = scopes.find((s) => s.id === parseInt(selectedScope, 10));
    if (!currentScope) return;

    setLoading(true);
    // Load enrolled students for this class/section to map student names
    institutionApi
      .getStudents(currentScope.class_id, currentScope.section_id)
      .then((stuList) => {
        setStudents(stuList || []);
      })
      .catch(() => setStudents([]));

    academicsApi
      .getAssignments({
        session_id: currentScope.session_id,
        class_id: currentScope.class_id,
        subject_id: currentScope.subject_id,
      })
      .then((list) => {
        const asgList = Array.isArray(list) ? list : [];
        setAssignments(asgList);
        if (asgList.length > 0) {
          handleSelectAssignment(asgList[0]);
        } else {
          setSelectedAssignment(null);
          setSubmissions([]);
        }
      })
      .catch((err) => {
        setMsg({ text: extractApiError(err, 'Failed to load assignments.'), type: 'error' });
      })
      .finally(() => setLoading(false));
  }, [selectedScope, scopes]);

  const handleSelectAssignment = async (assign) => {
    setSelectedAssignment(assign);
    try {
      const subs = await academicsApi.getSubmissions(assign.id);
      setSubmissions(Array.isArray(subs) ? subs : []);
    } catch (e) {
      console.warn('Submissions unavailable or empty:', e);
      setSubmissions([]);
    }
  };

  const handleCreateAssignment = async (e) => {
    e.preventDefault();
    const currentScope = scopes.find((s) => s.id === parseInt(selectedScope, 10));
    if (!currentScope) return;

    try {
      const created = await academicsApi.createAssignment({
        session_id: currentScope.session_id,
        class_id: currentScope.class_id,
        section_id: currentScope.section_id,
        subject_id: currentScope.subject_id,
        title: newAssign.title.trim(),
        description: newAssign.description.trim() || null,
        max_points: parseFloat(newAssign.max_points),
        due_date: new Date(newAssign.due_date).toISOString(),
      });
      setAssignments([created, ...assignments]);
      handleSelectAssignment(created);
      setShowCreate(false);
      setMsg({ text: `Assignment "${created.title}" published!`, type: 'success' });
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to create assignment.'), type: 'error' });
    }
  };

  const handleGradeSubmit = async (subId) => {
    const points = parseFloat(gradePoints);
    if (isNaN(points) || points < 0 || points > selectedAssignment.max_points) {
      setMsg({
        text: `Score must be between 0 and max points ${selectedAssignment.max_points}`,
        type: 'error',
      });
      return;
    }

    try {
      await academicsApi.gradeSubmission(subId, {
        points_awarded: points,
        feedback: gradeFeedback.trim() || null,
      });
      setMsg({ text: 'Submission graded successfully!', type: 'success' });
      setGradingSubId(null);
      setGradePoints('');
      setGradeFeedback('');
      // Refresh submissions
      const subs = await academicsApi.getSubmissions(selectedAssignment.id);
      setSubmissions(Array.isArray(subs) ? subs : []);
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to save grade.'), type: 'error' });
    }
  };

  const studentMap = {};
  students.forEach((s) => {
    studentMap[s.id] = s;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Assignment Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Create class coursework, evaluate submissions, and provide qualitative student feedback (R-006).
          </p>
        </div>

        <button
          onClick={() => setShowCreate(!showCreate)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition"
        >
          <Plus className="w-3.5 h-3.5" />
          {showCreate ? 'Cancel' : 'New Assignment'}
        </button>
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
            <CheckCircle className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          <span>{msg.text}</span>
        </div>
      )}

      {/* Scope Selector */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center gap-3">
        <label className="text-[11px] font-semibold text-slate-500 uppercase">
          Teaching Scope (D-004)
        </label>
        <select
          value={selectedScope}
          onChange={(e) => setSelectedScope(e.target.value)}
          className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {scopes.length === 0 && <option value="">No authorized scopes assigned</option>}
          {scopes.map((s) => (
            <option key={s.id} value={s.id}>
              Class #{s.class_id} {s.section_id ? `(Sec #${s.section_id})` : ''} • Subject #{s.subject_id}
            </option>
          ))}
        </select>
      </div>

      {/* Create Assignment Modal / Form */}
      {showCreate && (
        <form
          onSubmit={handleCreateAssignment}
          className="bg-indigo-50/60 border border-indigo-200 rounded-xl p-5 shadow-sm space-y-3"
        >
          <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Create New Coursework Assignment
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-700">Title</label>
              <input
                type="text"
                required
                placeholder="e.g. Chapter 4 Problem Set"
                value={newAssign.title}
                onChange={(e) => setNewAssign({ ...newAssign, title: e.target.value })}
                className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-700">Max Points</label>
              <input
                type="number"
                required
                min="1"
                value={newAssign.max_points}
                onChange={(e) => setNewAssign({ ...newAssign, max_points: e.target.value })}
                className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-700">Due Date</label>
              <input
                type="datetime-local"
                required
                value={newAssign.due_date}
                onChange={(e) => setNewAssign({ ...newAssign, due_date: e.target.value })}
                className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-700">
              Instructions / Description
            </label>
            <textarea
              rows={2}
              placeholder="Instructions for students..."
              value={newAssign.description}
              onChange={(e) => setNewAssign({ ...newAssign, description: e.target.value })}
              className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-sm"
            >
              Publish Assignment
            </button>
          </div>
        </form>
      )}

      {/* Assignments and Submissions split view */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Assignment List */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h2 className="font-semibold text-xs text-slate-900 uppercase tracking-wider mb-3">
            Assignments ({assignments.length})
          </h2>
          <div className="space-y-2">
            {assignments.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No assignments found.</p>
            ) : (
              assignments.map((a) => (
                <div
                  key={a.id}
                  onClick={() => handleSelectAssignment(a)}
                  className={`p-3 rounded-lg border text-xs cursor-pointer transition ${
                    selectedAssignment?.id === a.id
                      ? 'border-indigo-500 bg-indigo-50/50'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="font-semibold text-slate-900">{a.title}</div>
                  <div className="flex items-center justify-between mt-1 text-[11px] text-slate-500">
                    <span>Max: {a.max_points} pts</span>
                    <span>Due: {formatUtcTimestamp(a.due_date)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Submissions & Grading table */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          {selectedAssignment ? (
            <div>
              <div className="border-b border-slate-100 pb-3 mb-4">
                <h2 className="font-bold text-sm text-slate-900">{selectedAssignment.title}</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Max: {selectedAssignment.max_points} points • Submissions: {submissions.length}
                </p>
                {selectedAssignment.description && (
                  <p className="text-xs text-slate-600 mt-2 bg-slate-50 p-2.5 rounded-lg">
                    {selectedAssignment.description}
                  </p>
                )}
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-xs">
                  <thead className="bg-slate-50 text-slate-500 text-left">
                    <tr>
                      <th className="py-2 px-3 font-semibold">Student</th>
                      <th className="py-2 px-3 font-semibold">Submitted At</th>
                      <th className="py-2 px-3 font-semibold">Status</th>
                      <th className="py-2 px-3 font-semibold">Grade</th>
                      <th className="py-2 px-3 font-semibold">Feedback</th>
                      <th className="py-2 px-3 font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {submissions.length === 0 ? (
                      <tr>
                        <td colSpan="6" className="py-6 text-center text-slate-400">
                          No student submissions received for this assignment yet.
                        </td>
                      </tr>
                    ) : (
                      submissions.map((sub) => {
                        const studentObj = studentMap[sub.student_id];
                        const studentName = studentObj ? `${studentObj.full_name} (${studentObj.admission_number})` : `Student #${sub.student_id}`;

                        return (
                          <tr key={sub.id} className="hover:bg-slate-50/60">
                            <td className="py-2.5 px-3 font-medium text-slate-900">
                              {studentName}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                              {formatUtcTimestamp(sub.submitted_at)}
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold capitalize ${
                                  sub.status === 'graded'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : 'bg-amber-100 text-amber-800'
                                }`}
                              >
                                {sub.status}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-bold font-mono text-indigo-700">
                              {sub.points_awarded !== null && sub.points_awarded !== undefined ? `${sub.points_awarded} pts` : '—'}
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 max-w-xs truncate">
                              {sub.feedback || '—'}
                            </td>
                            <td className="py-2.5 px-3">
                              <button
                                type="button"
                                onClick={() => {
                                  setGradingSubId(sub.id);
                                  setGradePoints(
                                    sub.points_awarded !== null && sub.points_awarded !== undefined ? String(sub.points_awarded) : ''
                                  );
                                  setGradeFeedback(sub.feedback || '');
                                }}
                                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                              >
                                {sub.status === 'graded' ? 'Regrade' : 'Grade'}
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Grading Drawer / Inline Editor */}
              {gradingSubId && (
                <div className="mt-4 p-4 rounded-xl border border-indigo-200 bg-indigo-50/60">
                  <h3 className="font-semibold text-xs text-indigo-900 mb-2">
                    Grading Submission #{gradingSubId} (Max: {selectedAssignment.max_points} pts)
                  </h3>

                  {(() => {
                    const activeSub = submissions.find((s) => s.id === gradingSubId);
                    if (!activeSub) return null;
                    return (
                      <div className="mb-3 p-3 bg-white rounded-lg border border-indigo-100 text-xs space-y-1.5">
                        <div className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider">Submitted Work:</div>
                        {activeSub.content && (
                          <p className="font-mono text-slate-700 whitespace-pre-wrap bg-slate-50 p-2.5 rounded border border-slate-200">
                            {activeSub.content}
                          </p>
                        )}
                        {activeSub.attachment_url && (
                          <div className="flex items-center gap-1.5 text-indigo-700 font-medium pt-1">
                            <Link2 className="w-3.5 h-3.5" />
                            <span>Attachment Link: </span>
                            <a
                              href={activeSub.attachment_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-indigo-600 underline font-mono inline-flex items-center gap-1"
                            >
                              {activeSub.attachment_url} <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        )}
                      </div>
                    );
                  })()}

                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-[11px] font-medium text-slate-700">
                        Points Awarded
                      </label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max={selectedAssignment.max_points}
                        value={gradePoints}
                        onChange={(e) => setGradePoints(e.target.value)}
                        className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-[11px] font-medium text-slate-700">Feedback</label>
                      <input
                        type="text"
                        placeholder="Constructive feedback for student..."
                        value={gradeFeedback}
                        onChange={(e) => setGradeFeedback(e.target.value)}
                        className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <div className="flex items-end gap-2">
                      <button
                        type="button"
                        onClick={() => handleGradeSubmit(gradingSubId)}
                        className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-sm"
                      >
                        Submit Grade
                      </button>
                      <button
                        type="button"
                        onClick={() => setGradingSubId(null)}
                        className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-700"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-400 py-12 text-center">
              Select an assignment on the left to view submissions.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
