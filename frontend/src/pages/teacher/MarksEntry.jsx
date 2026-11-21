import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { institutionApi } from '../../api/institution';
import { academicsApi } from '../../api/academics';
import AuditModal from '../../components/AuditModal';
import { extractApiError, getLocalDateString } from '../../utils/format';
import { Plus, Save, CheckCircle, AlertCircle, Upload, FileText, Download } from 'lucide-react';

export default function MarksEntry() {
  const { teacherProfile, teacherId, activeSession, isAdmin } = useAuth();
  const [scopes, setScopes] = useState([]);
  const [classes, setClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [classSubjects, setClassSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [examTypeFilter, setExamTypeFilter] = useState('all');
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');
  const [students, setStudents] = useState([]);
  const [existingMarks, setExistingMarks] = useState({});
  const [marksState, setMarksState] = useState({});

  // New exam form
  const [showCreateExam, setShowCreateExam] = useState(false);
  const [newExam, setNewExam] = useState({
    name: 'Unit Test 1',
    exam_type: 'unit_test',
    max_marks: 100,
    weightage: 1.0,
    date: getLocalDateString(),
    time_slot: '09:00 AM - 12:00 PM',
  });

  // Datesheet upload state
  const [datesheetFile, setDatesheetFile] = useState(null);
  const [uploadingDatesheet, setUploadingDatesheet] = useState(false);
  const datesheetInputRef = useRef(null);

  // Bulk CSV upload state
  const [csvFile, setCsvFile] = useState(null);
  const [csvReason, setCsvReason] = useState('Bulk marks CSV import');
  const [uploadingCsv, setUploadingCsv] = useState(false);
  const csvInputRef = useRef(null);

  // Audit modal state (R-014, T-008)
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);
  const [pendingPayload, setPendingPayload] = useState(null);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [marksRefreshTick, setMarksRefreshTick] = useState(0);
  const [msg, setMsg] = useState({ text: '', type: '' });

  const currentTeacherId = teacherId || teacherProfile?.id;
  const sessionId = activeSession?.id;

  // 1. Load teacher classes & scopes
  useEffect(() => {
    let cancelled = false;
    if (isAdmin) {
      institutionApi
        .getClasses(sessionId)
        .then((clsList) => {
          if (!cancelled && Array.isArray(clsList)) {
            setClasses(clsList);
            if (clsList.length > 0 && !selectedClassId) {
              setSelectedClassId(String(clsList[0].id));
            }
          }
        })
        .catch((err) => console.error('Admin classes load error:', err));
    } else if (currentTeacherId && sessionId) {
      institutionApi
        .getTeacherAssignments(currentTeacherId, sessionId)
        .then((asgs) => {
          if (!cancelled && Array.isArray(asgs)) {
            setScopes(asgs);
            const uniqueClassesMap = {};
            asgs.forEach((a) => {
              if (!uniqueClassesMap[a.class_id]) {
                uniqueClassesMap[a.class_id] = {
                  id: a.class_id,
                  name: `Class #${a.class_id}`,
                  section_id: a.section_id,
                };
              }
            });
            const clsList = Object.values(uniqueClassesMap);
            setClasses(clsList);
            if (clsList.length > 0 && !selectedClassId) {
              setSelectedClassId(String(clsList[0].id));
            }
          }
        })
        .catch((err) => {
          console.error('Failed to load teacher assignments:', err);
        });
    }
    return () => {
      cancelled = true;
    };
  }, [currentTeacherId, sessionId, isAdmin]);

  // 2. When selectedClassId changes, load subjects for this class and load whole class student list
  useEffect(() => {
    if (!selectedClassId) return;
    let cancelled = false;

    // Load whole class students
    institutionApi
      .getStudents(selectedClassId)
      .then((stuList) => {
        if (!cancelled) setStudents(Array.isArray(stuList) ? stuList : []);
      })
      .catch(() => {
        if (!cancelled) setStudents([]);
      });

    // Load class subjects
    institutionApi
      .getClassSubjects(selectedClassId)
      .then((subs) => {
        if (!cancelled) {
          const list = Array.isArray(subs) ? subs : [];
          setClassSubjects(list);
          if (list.length > 0) {
            setSelectedSubjectId((prev) =>
              list.some((s) => String(s.id) === String(prev)) ? prev : String(list[0].id)
            );
          } else {
            setSelectedSubjectId('');
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          // Fallback to scopes
          const fallbackSubs = scopes
            .filter((s) => String(s.class_id) === String(selectedClassId))
            .map((s) => ({ id: s.subject_id, name: `Subject #${s.subject_id}`, code: `SUB${s.subject_id}` }));
          setClassSubjects(fallbackSubs);
          if (fallbackSubs.length > 0) {
            setSelectedSubjectId(String(fallbackSubs[0].id));
          }
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedClassId, scopes]);

  // 3. Load exams for selected class and subject
  useEffect(() => {
    if (!selectedClassId || !selectedSubjectId) {
      setExams([]);
      setSelectedExamId('');
      return;
    }

    let cancelled = false;
    setLoading(true);

    academicsApi
      .getExams({
        session_id: sessionId,
        class_id: parseInt(selectedClassId, 10),
        subject_id: parseInt(selectedSubjectId, 10),
      })
      .then((examList) => {
        if (cancelled) return;
        const validExams = Array.isArray(examList) ? examList : [];
        setExams(validExams);
        if (validExams.length > 0) {
          setSelectedExamId((prev) =>
            validExams.some((e) => String(e.id) === String(prev))
              ? prev
              : String(validExams[0].id)
          );
        } else {
          setSelectedExamId('');
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('Failed to load exams:', err);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedClassId, selectedSubjectId, sessionId]);

  // 3. Load existing marks for selected exam with short debounce to avoid aborted reloads
  useEffect(() => {
    if (!selectedExamId) {
      setExistingMarks({});
      setMarksState({});
      return undefined;
    }

    let cancelled = false;
    const examIdNum = parseInt(selectedExamId, 10);
    const timer = setTimeout(() => {
      setLoading(true);
      academicsApi
        .getMarksForExam(examIdNum)
        .then((marksList) => {
          if (cancelled) return;
          const markMap = {};
          if (Array.isArray(marksList)) {
            marksList.forEach((m) => {
              markMap[m.student_id] = {
                score: m.score !== null && m.score !== undefined ? String(m.score) : '',
                is_absent: Boolean(m.is_absent),
                remarks: m.remarks || '',
              };
            });
          }
          setExistingMarks(markMap);
          setMarksState(markMap);
        })
        .catch((err) => {
          if (!cancelled) {
            setMsg({ text: extractApiError(err, 'Failed to load exam marks.'), type: 'error' });
          }
        })
        .finally(() => {
          if (!cancelled) {
            setLoading(false);
          }
        });
    }, 200);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [selectedExamId, marksRefreshTick]);

  const activeExam = exams.find((e) => e.id === parseInt(selectedExamId, 10));

  const handleScoreChange = (studentId, value) => {
    setMarksState((prev) => ({
      ...prev,
      [studentId]: {
        ...prev[studentId],
        score: value,
        is_absent: value !== '' ? false : prev[studentId]?.is_absent || false,
      },
    }));
  };

  const handleAbsentToggle = (studentId, checked) => {
    setMarksState((prev) => ({
      ...prev,
      [studentId]: {
        ...prev[studentId],
        is_absent: checked,
        score: checked ? '' : prev[studentId]?.score || '',
      },
    }));
  };

  const handleRemarksChange = (studentId, value) => {
    setMarksState((prev) => ({
      ...prev,
      [studentId]: {
        ...prev[studentId],
        remarks: value,
      },
    }));
  };

  const handleCreateExamSubmit = async (e) => {
    e.preventDefault();
    if (!selectedClassId || !selectedSubjectId) {
      setMsg({ text: 'Please select both a class and a subject before creating an exam.', type: 'error' });
      return;
    }

    try {
      const created = await academicsApi.createExam({
        session_id: sessionId || 1,
        class_id: parseInt(selectedClassId, 10),
        subject_id: parseInt(selectedSubjectId, 10),
        name: newExam.name.trim(),
        exam_type: newExam.exam_type,
        max_marks: parseFloat(newExam.max_marks),
        weightage: parseFloat(newExam.weightage),
        date: newExam.date,
        time_slot: newExam.time_slot || '09:00 AM - 12:00 PM',
      });
      setExams((prev) => [created, ...prev]);
      setSelectedExamId(String(created.id));
      setShowCreateExam(false);
      setMsg({ text: `Exam "${created.name}" created successfully!`, type: 'success' });
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to create exam.'), type: 'error' });
    }
  };

  const handleInitiateSave = () => {
    if (!activeExam) return;
    setMsg({ text: '', type: '' });

    let hasEdits = false;
    const entriesToSave = [];

    for (const student of students) {
      const state = marksState[student.id];
      if (!state) continue;

      const isAbsent = Boolean(state.is_absent);
      let numScore = null;

      if (!isAbsent && state.score !== '' && state.score !== null && state.score !== undefined) {
        numScore = parseFloat(state.score);
        if (isNaN(numScore) || numScore < 0 || numScore > activeExam.max_marks) {
          setMsg({
            text: `Invalid score for ${student.full_name}: must be between 0 and max marks (${activeExam.max_marks}).`,
            type: 'error',
          });
          return;
        }
      }

      const existing = existingMarks[student.id];
      const existingScore =
        existing && existing.score !== '' && existing.score !== null && existing.score !== undefined
          ? parseFloat(existing.score)
          : null;
      const existingAbsent = existing ? Boolean(existing.is_absent) : false;

      if (
        !existing ||
        existingScore !== numScore ||
        existingAbsent !== isAbsent ||
        (existing.remarks || '') !== (state.remarks || '')
      ) {
        if (existing) hasEdits = true;
        entriesToSave.push({
          student_id: student.id,
          score: numScore,
          is_absent: isAbsent,
          remarks: state.remarks || null,
        });
      }
    }

    if (entriesToSave.length === 0) {
      setMsg({ text: 'No changes detected to save.', type: 'info' });
      return;
    }

    const payload = {
      exam_id: activeExam.id,
      entries: entriesToSave,
    };

    if (hasEdits) {
      setPendingPayload(payload);
      setIsAuditModalOpen(true);
    } else {
      executeSave(payload, 'Initial marks entry');
    }
  };

  const executeSave = async (payload, reason) => {
    setSaving(true);
    try {
      const res = await academicsApi.saveMarks({
        ...payload,
        reason: reason,
      });
      setMsg({
        text: `Successfully recorded ${res.saved_count || payload.entries.length} marks with audit confirmation!`,
        type: 'success',
      });
      const marksList = await academicsApi.getMarksForExam(activeExam.id);
      const markMap = {};
      if (Array.isArray(marksList)) {
        marksList.forEach((m) => {
          markMap[m.student_id] = {
            score: m.score !== null && m.score !== undefined ? String(m.score) : '',
            is_absent: Boolean(m.is_absent),
            remarks: m.remarks || '',
          };
        });
      }
      setExistingMarks(markMap);
      setMarksState(markMap);
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to save marks.'), type: 'error' });
    } finally {
      setSaving(false);
      setIsAuditModalOpen(false);
      setPendingPayload(null);
    }
  };

  const handleUploadDatesheet = async () => {
    if (!activeExam) {
      setMsg({ text: 'Please select an exam before uploading a datesheet.', type: 'error' });
      return;
    }
    if (!datesheetFile) {
      setMsg({ text: 'Please select a datesheet file (PDF or image).', type: 'error' });
      return;
    }

    setUploadingDatesheet(true);
    setMsg({ text: '', type: '' });
    try {
      const res = await academicsApi.uploadDatesheet(activeExam.id, datesheetFile);
      const newFilename = res.datesheet_filename;
      setExams((prev) =>
        prev.map((ex) =>
          ex.id === activeExam.id ? { ...ex, datesheet_filename: newFilename } : ex
        )
      );
      setDatesheetFile(null);
      if (datesheetInputRef.current) {
        datesheetInputRef.current.value = '';
      }
      setMsg({
        text: `Datesheet "${newFilename}" uploaded successfully!`,
        type: 'success',
      });
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to upload datesheet.'), type: 'error' });
    } finally {
      setUploadingDatesheet(false);
    }
  };

  const handleDownloadActiveDatesheet = async () => {
    if (!activeExam?.datesheet_filename) return;
    try {
      await academicsApi.downloadDatesheet(activeExam.id, activeExam.datesheet_filename);
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to download datesheet.'), type: 'error' });
    }
  };

  const handleUploadCsv = async () => {
    if (!csvFile) {
      setMsg({ text: 'Please select a CSV file to upload.', type: 'error' });
      return;
    }
    const targetSessionId = activeSession?.id;
    if (!targetSessionId) {
      setMsg({ text: 'Active academic session is required for CSV upload.', type: 'error' });
      return;
    }

    setUploadingCsv(true);
    setMsg({ text: '', type: '' });
    try {
      const csvText = await csvFile.text();
      const firstLine = (csvText.split(/\r?\n/)[0] || '').toLowerCase();
      const hasExamColumn =
        firstLine.includes('exam id') ||
        firstLine.includes('exam_id') ||
        firstLine.includes('exam name') ||
        firstLine.includes('exam_name');

      const fallbackExamId =
        !hasExamColumn && selectedExamId ? Number(selectedExamId) : null;

      const res = await academicsApi.uploadMarksCsv(
        csvFile,
        targetSessionId,
        csvReason.trim() || 'Bulk marks CSV import',
        fallbackExamId
      );

      setCsvFile(null);
      if (csvInputRef.current) {
        csvInputRef.current.value = '';
      }
      setMsg({
        text: `Successfully uploaded: ${res.imported_count} marks imported from CSV.`,
        type: 'success',
      });

      if (activeExam) {
        setMarksRefreshTick((t) => t + 1);
      }
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to import CSV marks.'), type: 'error' });
    } finally {
      setUploadingCsv(false);
    }
  };

  return (
    <div className="space-y-6 min-w-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Exam Evaluation &amp; Marks</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit-protected marks entry (R-005, R-014, Invariant 2). Blanks remain distinct from zero.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setShowCreateExam(!showCreateExam)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            {showCreateExam ? 'Cancel Exam' : 'New Exam'}
          </button>
          <button
            type="button"
            onClick={handleInitiateSave}
            disabled={saving || !activeExam || students.length === 0}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Marks'}
          </button>
        </div>
      </div>

      {msg.text && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
            msg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : msg.type === 'info'
              ? 'bg-blue-50 text-blue-800 border border-blue-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {msg.type === 'success' ? (
            <CheckCircle className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          <span className="break-words min-w-0">{msg.text}</span>
        </div>
      )}

      {/* 3 Explicit Filters: 1. Class -> 2. Subject -> 3. Exam & Exam Type */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-wrap items-center gap-4">
        {/* 1. Class Selector */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 uppercase">
            1. Select Class
          </label>
          <select
            value={selectedClassId}
            onChange={(e) => setSelectedClassId(e.target.value)}
            className="mt-1 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {classes.length === 0 && <option value="">No classes available</option>}
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name || `Class #${c.id}`}
              </option>
            ))}
          </select>
        </div>

        {/* 2. Subject Selector */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 uppercase">
            2. Select Subject
          </label>
          <select
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(e.target.value)}
            className="mt-1 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {classSubjects.length === 0 && <option value="">No subjects in class</option>}
            {classSubjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.code})
              </option>
            ))}
          </select>
        </div>

        {/* 3. Exam Type Filter & Exam Selector */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 uppercase">
            3. Exam Type &amp; Assessment
          </label>
          <div className="flex items-center gap-2 mt-1">
            <select
              value={examTypeFilter}
              onChange={(e) => setExamTypeFilter(e.target.value)}
              className="text-xs font-medium px-2.5 py-1.5 rounded-lg border border-slate-300 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Types</option>
              <option value="unit_test">Unit Tests</option>
              <option value="midterm">Midterm Exams</option>
              <option value="final">Final Exams</option>
              <option value="quiz">Quizzes</option>
            </select>

            <select
              value={selectedExamId}
              onChange={(e) => setSelectedExamId(e.target.value)}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[200px]"
            >
              {exams.length === 0 ? (
                <option value="">No exams created yet</option>
              ) : (
                exams
                  .filter((e) => examTypeFilter === 'all' || e.exam_type === examTypeFilter)
                  .map((e) => (
                    <option key={e.id} value={e.id}>
                      [{e.exam_type?.toUpperCase() || 'EXAM'}] {e.name} • Max: {e.max_marks}
                    </option>
                  ))
              )}
            </select>
          </div>
        </div>

        {activeExam && (
          <div className="ml-auto text-xs bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-slate-600">
            <span className="font-semibold text-slate-800">{activeExam.name}</span>
            <span className="mx-2">•</span>
            <span className="font-medium text-indigo-700 capitalize">Type: {activeExam.exam_type}</span>
            <span className="mx-2">•</span>
            <span>Max Marks: <strong className="text-indigo-600">{activeExam.max_marks}</strong></span>
          </div>
        )}
      </div>

      {/* Create New Exam Collapsible Panel */}
      {showCreateExam && (
        <form
          onSubmit={handleCreateExamSubmit}
          className="bg-indigo-50/60 border border-indigo-200 rounded-xl p-5 shadow-sm grid grid-cols-1 sm:grid-cols-6 gap-3"
        >
          <div className="sm:col-span-2">
            <label className="block text-[11px] font-semibold text-slate-700">Exam Title (e.g. Unit Test 1)</label>
            <input
              type="text"
              required
              placeholder="e.g. Unit Test 1"
              value={newExam.name}
              onChange={(e) => setNewExam({ ...newExam, name: e.target.value })}
              className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-700">Exam Type</label>
            <select
              value={newExam.exam_type}
              onChange={(e) => setNewExam({ ...newExam, exam_type: e.target.value })}
              className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="unit_test">Unit Test</option>
              <option value="midterm">Midterm Exam</option>
              <option value="final">Final Exam</option>
              <option value="quiz">Quiz</option>
              <option value="assignment_test">Assignment Test</option>
              <option value="exam">Standard Exam</option>
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-700">Max Marks</label>
            <input
              type="number"
              required
              min="1"
              value={newExam.max_marks}
              onChange={(e) => setNewExam({ ...newExam, max_marks: e.target.value })}
              className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-700">Weightage</label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              value={newExam.weightage}
              onChange={(e) => setNewExam({ ...newExam, weightage: e.target.value })}
              className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-700">Date</label>
            <input
              type="date"
              required
              value={newExam.date}
              onChange={(e) => setNewExam({ ...newExam, date: e.target.value })}
              className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-[11px] font-semibold text-slate-700">Time Slot</label>
            <input
              type="text"
              placeholder="09:00 AM - 12:00 PM"
              value={newExam.time_slot}
              onChange={(e) => setNewExam({ ...newExam, time_slot: e.target.value })}
              className="mt-1 w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-sm"
            >
              Create Exam
            </button>
          </div>
        </form>
      )}

      {/* Exam Datesheet Upload & Bulk Marks CSV Upload Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Exam Datesheet Panel */}
        <section className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3 min-w-0">
          <hgroup className="flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-600 shrink-0" />
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Exam Datesheet Attachment
              </h2>
            </span>

            {activeExam?.datesheet_filename && (
              <span className="flex items-center gap-2">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 truncate max-w-[180px]">
                  {activeExam.datesheet_filename}
                </span>
                <button
                  type="button"
                  onClick={handleDownloadActiveDatesheet}
                  className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-semibold rounded bg-slate-100 hover:bg-slate-200 text-slate-700"
                >
                  <Download className="w-3 h-3" />
                  Download
                </button>
              </span>
            )}
          </hgroup>

          <p className="text-[11px] text-slate-500">
            Attach a PDF or image schedule for the selected exam ({activeExam?.name || 'none selected'}).
          </p>

          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={datesheetInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv"
              onChange={(e) => setDatesheetFile(e.target.files?.[0] || null)}
              className="text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 flex-1 min-w-0"
            />
            <button
              type="button"
              onClick={handleUploadDatesheet}
              disabled={!activeExam || uploadingDatesheet}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50"
            >
              <Upload className="w-3.5 h-3.5" />
              {uploadingDatesheet ? 'Uploading...' : 'Upload Datesheet'}
            </button>
          </div>
        </section>

        {/* Bulk Marks CSV Upload Panel */}
        <section className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3 min-w-0">
          <hgroup className="flex items-center gap-2">
            <Upload className="w-4 h-4 text-emerald-600 shrink-0" />
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Bulk Marks CSV Upload
            </h2>
          </hgroup>

          <p className="text-[11px] text-slate-500">
            Columns: <code className="font-mono text-slate-700">Admission Number, Exam ID, Score</code> (or Exam Name).
          </p>

          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={csvInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
              className="text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 flex-1 min-w-0"
            />
            <input
              type="text"
              value={csvReason}
              onChange={(e) => setCsvReason(e.target.value)}
              placeholder="Audit reason..."
              className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white w-44"
            />
            <button
              type="button"
              onClick={handleUploadCsv}
              disabled={uploadingCsv}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition disabled:opacity-50"
            >
              <Upload className="w-3.5 h-3.5" />
              {uploadingCsv ? 'Importing...' : 'Upload CSV'}
            </button>
          </div>
        </section>
      </div>

      {/* Marks Sheet Table (UI-004) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Roll</th>
                <th className="py-2.5 px-3 font-semibold">Admission No.</th>
                <th className="py-2.5 px-3 font-semibold">Student Name</th>
                <th className="py-2.5 px-3 font-semibold w-36">Score (Max: {activeExam?.max_marks || 100})</th>
                <th className="py-2.5 px-3 font-semibold text-center w-24">Absent</th>
                <th className="py-2.5 px-3 font-semibold">Remarks / Evaluation Feedback</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {students.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    {loading ? 'Loading student roster...' : 'No enrolled students found in this class.'}
                  </td>
                </tr>
              ) : (
                students.map((student) => {
                  const state = marksState[student.id] || { score: '', is_absent: false, remarks: '' };
                  const numScore = parseFloat(state.score);
                  const isOutOfRange =
                    activeExam &&
                    !state.is_absent &&
                    state.score !== '' &&
                    (isNaN(numScore) || numScore < 0 || numScore > activeExam.max_marks);

                  return (
                    <tr key={student.id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-500">
                        {student.roll_number || '—'}
                      </td>
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-900">
                        {student.admission_number}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-slate-800">{student.full_name}</td>
                      <td className="py-2.5 px-3">
                        <div className="relative">
                          <input
                            type="number"
                            step="0.5"
                            min="0"
                            max={activeExam?.max_marks || 100}
                            disabled={state.is_absent}
                            placeholder="Blank"
                            value={state.score}
                            onChange={(e) => handleScoreChange(student.id, e.target.value)}
                            className={`w-full px-2.5 py-1 text-xs rounded-lg border ${
                              isOutOfRange
                                ? 'border-rose-500 bg-rose-50 text-rose-900 focus:ring-rose-500'
                                : 'border-slate-300 focus:ring-indigo-500'
                            } disabled:bg-slate-100 disabled:text-slate-400`}
                          />
                          {isOutOfRange && (
                            <span className="block text-[10px] text-rose-600 mt-0.5">
                              Out of range (0-{activeExam.max_marks})
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <input
                          type="checkbox"
                          checked={state.is_absent}
                          onChange={(e) => handleAbsentToggle(student.id, e.target.checked)}
                          className="rounded text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                        />
                      </td>
                      <td className="py-2.5 px-3">
                        <input
                          type="text"
                          placeholder="Optional remarks"
                          value={state.remarks}
                          onChange={(e) => handleRemarksChange(student.id, e.target.value)}
                          className="w-full text-xs px-2 py-1 rounded border border-slate-200"
                        />
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mandatory Audit Justification Modal (R-014, T-008) */}
      <AuditModal
        isOpen={isAuditModalOpen}
        title="Audited Evaluation Update (R-014)"
        message="You are modifying existing marks for one or more students. Academic regulations require a mandatory reason for this update."
        onConfirm={(reason) => executeSave(pendingPayload, reason)}
        onCancel={() => {
          setIsAuditModalOpen(false);
          setPendingPayload(null);
        }}
      />
    </div>
  );
}
