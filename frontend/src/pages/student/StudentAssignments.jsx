import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { academicsApi } from '../../api/academics';
import { extractApiError, formatUtcTimestamp } from '../../utils/format';
import { BookOpen, Upload, CheckCircle, Clock, AlertCircle, Link2, ExternalLink, FileText, Image } from 'lucide-react';

export default function StudentAssignments() {
  const { studentProfile, studentId, activeSession } = useAuth();
  const [assignments, setAssignments] = useState([]);
  const [activeAssign, setActiveAssign] = useState(null);
  const [submissions, setSubmissions] = useState({}); // { [assign_id]: submission_obj }
  const [submitContent, setSubmitContent] = useState('');
  const [attachmentUrl, setAttachmentUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState({ text: '', type: '' });

  const currentStudentId = studentId || studentProfile?.id;
  const currentClassId = studentProfile?.class_id;

  useEffect(() => {
    if (currentStudentId) {
      loadAssignments();
    }
  }, [currentStudentId, currentClassId, activeSession]);

  const loadAssignments = async () => {
    setLoading(true);
    try {
      const sessionId = activeSession?.id;
      const list = await academicsApi.getAssignments({
        session_id: sessionId,
        class_id: currentClassId,
      });
      const asgList = Array.isArray(list) ? list : [];
      setAssignments(asgList);

      // Check existing submissions for each assignment
      const subMap = {};
      await Promise.all(
        asgList.map(async (a) => {
          try {
            const subs = await academicsApi.getSubmissions(a.id);
            if (Array.isArray(subs) && subs.length > 0) {
              // For student, backend returns only student's own submission
              const mine = subs.find((s) => s.student_id === currentStudentId) || subs[0];
              if (mine) subMap[a.id] = mine;
            }
          } catch (e) {
            // Out of scope / no submissions
          }
        })
      );
      setSubmissions(subMap);
      if (asgList.length > 0) setActiveAssign(asgList[0]);
    } catch (err) {
      console.error('Failed to load assignments:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!activeAssign) return;
    if (!submitContent.trim() && !attachmentUrl.trim() && !selectedFile) {
      setMsg({
        text: 'Please provide a written solution, an attachment link, or upload your handwritten assignment file.',
        type: 'error',
      });
      return;
    }

    setSubmitting(true);
    setMsg({ text: '', type: '' });

    try {
      let res;
      if (selectedFile) {
        res = await academicsApi.uploadAssignmentSubmission(
          activeAssign.id,
          selectedFile,
          submitContent.trim()
        );
      } else {
        res = await academicsApi.submitAssignment(activeAssign.id, {
          assignment_id: activeAssign.id,
          content: submitContent.trim() || undefined,
          attachment_url: attachmentUrl.trim() || undefined,
        });
      }
      setMsg({ text: 'Assignment submitted successfully!', type: 'success' });
      setSubmissions((prev) => ({ ...prev, [activeAssign.id]: res }));
      setSubmitContent('');
      setAttachmentUrl('');
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to submit assignment.'), type: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const currentSubmission = activeAssign ? submissions[activeAssign.id] : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Coursework Assignments</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Submit coursework solutions and review qualitative evaluations from your teachers.
        </p>
      </div>

      {msg.text && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
            msg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {msg.type === 'success' ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          <span>{msg.text}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Assignment List */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h2 className="font-semibold text-xs text-slate-900 uppercase tracking-wider mb-3">
            Your Coursework ({assignments.length})
          </h2>
          <div className="space-y-2">
            {assignments.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">No assignments assigned.</p>
            ) : (
              assignments.map((a) => {
                const sub = submissions[a.id];
                return (
                  <div
                    key={a.id}
                    onClick={() => setActiveAssign(a)}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition ${
                      activeAssign?.id === a.id
                        ? 'border-indigo-500 bg-indigo-50/50'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-900">{a.title}</span>
                      {sub && (
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                            sub.status === 'graded'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {sub.status === 'graded' ? `${sub.points_awarded} pts` : 'Submitted'}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between mt-1 text-[11px] text-slate-500">
                      <span>Max: {a.max_points} pts</span>
                      <span>Due: {formatUtcTimestamp(a.due_date)}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Assignment Detail & Submission Form */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          {activeAssign ? (
            <div>
              <div className="border-b border-slate-100 pb-4 mb-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">{activeAssign.title}</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Max Score: <strong>{activeAssign.max_points} points</strong> • Due:{' '}
                      {formatUtcTimestamp(activeAssign.due_date)}
                    </p>
                  </div>
                  {currentSubmission ? (
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                        currentSubmission.status === 'graded'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {currentSubmission.status === 'graded' ? 'Evaluated' : 'Submitted (Pending Review)'}
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                      Not Submitted
                    </span>
                  )}
                </div>

                {activeAssign.description && (
                  <div className="mt-4 p-3.5 bg-slate-50 rounded-xl text-xs text-slate-700 leading-relaxed border border-slate-200/60">
                    <div className="font-semibold text-slate-900 mb-1 text-[11px] uppercase tracking-wider">
                      Teacher Instructions:
                    </div>
                    {activeAssign.description}
                  </div>
                )}
              </div>

              {/* Evaluation Feedback Section if graded */}
              {currentSubmission?.status === 'graded' && (
                <div className="mb-6 p-4 rounded-xl border border-emerald-200 bg-emerald-50/60">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-900 uppercase tracking-wider">
                      Evaluation Result
                    </span>
                    <span className="text-base font-bold font-mono text-emerald-700">
                      {currentSubmission.points_awarded} / {activeAssign.max_points} Points
                    </span>
                  </div>
                  {currentSubmission.feedback && (
                    <div className="mt-2 text-xs text-emerald-800 italic">
                      "{currentSubmission.feedback}"
                    </div>
                  )}
                </div>
              )}

              {/* Submission Form / View */}
              {currentSubmission ? (
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-slate-700">Your Submitted Work:</div>
                  {currentSubmission.content && (
                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs font-mono whitespace-pre-wrap text-slate-800">
                      {currentSubmission.content}
                    </div>
                  )}
                  {currentSubmission.attachment_url && (
                    <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-200 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2 text-indigo-700">
                        <Link2 className="w-4 h-4 shrink-0" />
                        <span className="font-semibold text-slate-800">Attachment / Solution Link:</span>
                      </div>
                      <a
                        href={currentSubmission.attachment_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-mono text-indigo-600 hover:text-indigo-800 underline font-medium truncate max-w-xs"
                      >
                        {currentSubmission.attachment_url} <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}
                  <div className="text-[11px] text-slate-400">
                    Submitted on {formatUtcTimestamp(currentSubmission.submitted_at)}
                  </div>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Written Answer / Solution Notes
                    </label>
                    <textarea
                      rows={5}
                      value={submitContent}
                      onChange={(e) => setSubmitContent(e.target.value)}
                      placeholder="Type or paste your completed assignment solution here..."
                      className="w-full text-xs font-mono rounded-lg border border-slate-300 p-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>

                  {/* Upload Handwritten File Option */}
                  <div className="p-3.5 rounded-xl border border-dashed border-indigo-300 bg-indigo-50/40">
                    <label className="block text-xs font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
                      <Upload className="w-4 h-4 text-indigo-600" /> Upload Handwritten Solution / Assignment File
                    </label>
                    <p className="text-[11px] text-slate-500 mb-2">
                      Upload photos of handwritten pages, scanned work, PDF, or document (PNG, JPG, PDF, DOCX up to 10MB).
                    </p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,image/*,.doc,.docx,.txt"
                      onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                      className="block w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 cursor-pointer"
                    />
                    {selectedFile && (
                      <div className="mt-2 text-xs font-medium text-emerald-700 flex items-center gap-1.5">
                        <CheckCircle className="w-3.5 h-3.5" /> Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Attachment Link / Project URL (Optional)
                    </label>
                    <div className="relative">
                      <Link2 className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                      <input
                        type="url"
                        value={attachmentUrl}
                        onChange={(e) => setAttachmentUrl(e.target.value)}
                        placeholder="https://drive.google.com/... or https://github.com/..."
                        className="w-full pl-8 pr-3 py-1.5 text-xs font-mono rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                      />
                    </div>
                    <span className="text-[10px] text-slate-400">
                      Submit handwritten photo/file upload, written text, or an external link.
                    </span>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-sm transition disabled:opacity-50"
                    >
                      {submitting ? 'Submitting...' : 'Turn In Assignment'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate-400 py-12 text-center">
              Select an assignment on the left to view details and submit.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
