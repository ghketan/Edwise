import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { institutionApi } from '../../api/institution';
import { academicsApi } from '../../api/academics';
import { extractApiError, getLocalDateString, formatUtcTimestamp } from '../../utils/format';
import {
  CalendarCheck,
  Save,
  CheckCircle,
  AlertCircle,
  Clock,
  UserCheck,
  UserX,
  Layers,
  BookOpen,
} from 'lucide-react';

export default function AttendanceEntry() {
  const { teacherProfile, teacherId, activeSession, isAdmin } = useAuth();
  const [scopes, setScopes] = useState([]);
  const [classes, setClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [classSubjects, setClassSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('all'); // 'all' or subject_id
  const [date, setDate] = useState(() => getLocalDateString());
  const [students, setStudents] = useState([]);
  const [entries, setEntries] = useState({}); // { [student_id]: status }
  const [notes, setNotes] = useState({});

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); // { time, count, unsaved }
  const [error, setError] = useState('');

  const currentTeacherId = teacherId || teacherProfile?.id;

  // Load teacher scopes and classes
  useEffect(() => {
    const sessionId = activeSession?.id;
    if (isAdmin) {
      institutionApi
        .getClasses(sessionId)
        .then((clsList) => {
          if (Array.isArray(clsList)) {
            setClasses(clsList);
            if (clsList.length > 0 && !selectedClassId) {
              setSelectedClassId(String(clsList[0].id));
            }
          }
        })
        .catch((err) => console.error('Admin classes load error:', err));
    } else if (currentTeacherId) {
      institutionApi
        .getTeacherAssignments(currentTeacherId, sessionId)
        .then((asgs) => {
          if (Array.isArray(asgs)) {
            setScopes(asgs);
            // Unique classes from scopes
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
  }, [currentTeacherId, activeSession, isAdmin]);

  // When class changes, fetch subjects configured for this class
  useEffect(() => {
    if (!selectedClassId) return;
    institutionApi
      .getClassSubjects(selectedClassId)
      .then((subs) => {
        setClassSubjects(Array.isArray(subs) ? subs : []);
      })
      .catch(() => {
        // Fallback: filter from scopes
        const scopeSubs = scopes
          .filter((s) => String(s.class_id) === String(selectedClassId))
          .map((s) => ({ id: s.subject_id, name: `Subject #${s.subject_id}`, code: `SUB${s.subject_id}` }));
        setClassSubjects(scopeSubs);
      });
  }, [selectedClassId, scopes]);

  // When class, subject, or date changes, load students and existing attendance records
  useEffect(() => {
    if (!selectedClassId) return;

    setLoading(true);
    setError('');
    setEntries({});
    setNotes({});
    setSaveStatus(null);

    const isFullDay = selectedSubjectId === 'all';
    const params = {
      session_id: activeSession?.id || 1,
      class_id: parseInt(selectedClassId, 10),
      date: date,
    };
    if (!isFullDay && selectedSubjectId) {
      params.subject_id = parseInt(selectedSubjectId, 10);
    }

    Promise.all([
      institutionApi.getStudents(selectedClassId),
      academicsApi.getAttendance(params).catch(() => []),
    ])
      .then(([stuList, attList]) => {
        setStudents(stuList || []);
        const map = {};
        const noteMap = {};
        let lastUpdated = null;
        if (Array.isArray(attList)) {
          attList.forEach((a) => {
            // In full-day mode, if student is absent in any subject, reflect it
            if (!map[a.student_id] || a.status === 'absent') {
              map[a.student_id] = a.status;
            }
            if (a.notes) noteMap[a.student_id] = a.notes;
            if (a.updated_at) lastUpdated = a.updated_at;
          });
        }
        setEntries(map);
        setNotes(noteMap);
        setSaveStatus({
          time: lastUpdated
            ? `Recorded ${formatUtcTimestamp(lastUpdated)}`
            : attList?.length > 0
            ? 'Previously Recorded'
            : null,
          count: attList?.length || 0,
          unsaved: false,
        });
      })
      .catch((err) => {
        setError(extractApiError(err, 'Failed to load class attendance.'));
      })
      .finally(() => setLoading(false));
  }, [selectedClassId, selectedSubjectId, date, activeSession]);

  const handleStatusChange = (studentId, status) => {
    setEntries((prev) => ({ ...prev, [studentId]: status }));
    setSaveStatus((prev) => ({ ...prev, unsaved: true }));
  };

  const handleMarkAll = (status) => {
    const updated = {};
    students.forEach((s) => {
      updated[s.id] = status;
    });
    setEntries(updated);
    setSaveStatus((prev) => ({ ...prev, unsaved: true }));
  };

  const handleSave = async () => {
    if (!selectedClassId) return;

    setSaving(true);
    setError('');

    // Transform entries into array (API-001)
    const entryList = Object.entries(entries)
      .filter(([_, status]) => Boolean(status))
      .map(([stuId, status]) => ({
        student_id: parseInt(stuId, 10),
        status: status,
        notes: notes[stuId] || null,
      }));

    if (entryList.length === 0) {
      setError('Please record attendance status (Present, Absent, Late, or Excused) for at least one student.');
      setSaving(false);
      return;
    }

    try {
      const isFullDay = selectedSubjectId === 'all';
      const targetSubId = isFullDay ? null : parseInt(selectedSubjectId, 10);

      const res = await academicsApi.saveAttendance({
        session_id: activeSession?.id || 1,
        class_id: parseInt(selectedClassId, 10),
        subject_id: targetSubId,
        is_full_day: isFullDay,
        date: date,
        entries: entryList,
        records: entryList, // sent for compatibility
      });

      setSaveStatus({
        time: `Saved just now (${res.saved_count || entryList.length} records)`,
        count: res.saved_count || entryList.length,
        unsaved: false,
      });
    } catch (err) {
      setError(extractApiError(err, 'Failed to save attendance.'));
    } finally {
      setSaving(false);
    }
  };

  const selectedSubjectObj = classSubjects.find((s) => String(s.id) === selectedSubjectId);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Daily Attendance Entry</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Mark full-day class attendance or select an individual subject to record subject-specific absence.
          </p>
        </div>

        {/* Save button and status indicator */}
        <div className="flex items-center gap-3">
          {saveStatus?.unsaved && (
            <span className="text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-lg flex items-center gap-1.5 animate-pulse">
              <Clock className="w-3.5 h-3.5" /> Unsaved Changes
            </span>
          )}
          {saveStatus?.time && !saveStatus?.unsaved && (
            <span className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg flex items-center gap-1.5">
              <CheckCircle className="w-3.5 h-3.5" /> {saveStatus.time}
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={saving || students.length === 0}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Attendance'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Class, Subject & Date Selector Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* 1. Class Option */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase flex items-center gap-1">
              <Layers className="w-3.5 h-3.5 text-indigo-600" /> Class / Grade
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

          {/* 2. Subject Option (All Subjects or Specific Subject) */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase flex items-center gap-1">
              <BookOpen className="w-3.5 h-3.5 text-indigo-600" /> Subject Scope
            </label>
            <select
              value={selectedSubjectId}
              onChange={(e) => setSelectedSubjectId(e.target.value)}
              className="mt-1 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">★ All Subjects (Full Day Attendance)</option>
              {classSubjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.code})
                </option>
              ))}
            </select>
          </div>

          {/* Date Picker */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="mt-1 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Bulk Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleMarkAll('present')}
            disabled={students.length === 0}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition disabled:opacity-50"
          >
            <UserCheck className="w-3.5 h-3.5" /> All Present
          </button>
          <button
            type="button"
            onClick={() => handleMarkAll('absent')}
            disabled={students.length === 0}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100 transition disabled:opacity-50"
          >
            <UserX className="w-3.5 h-3.5" /> All Absent
          </button>
        </div>
      </div>

      {/* Scope banner info */}
      <div className="px-3.5 py-2 rounded-lg bg-indigo-50/70 border border-indigo-100 flex items-center justify-between text-xs text-indigo-900">
        <div>
          {selectedSubjectId === 'all' ? (
            <span>
              <strong>Full Day Attendance:</strong> Status entered will apply across all subjects for this class on {date}.
            </span>
          ) : (
            <span>
              <strong>Subject-Specific Attendance:</strong> Marking status specifically for <strong>{selectedSubjectObj?.name || 'Selected Subject'}</strong>. Other subjects remain unaffected.
            </span>
          )}
        </div>
        <div className="text-[11px] font-mono text-indigo-700">
          Enrolled: {students.length} students
        </div>
      </div>

      {/* Attendance Roster Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-12 text-center text-xs text-slate-500">
            Loading class roster and attendance records...
          </div>
        ) : students.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400">
            No students found enrolled in this class and section.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50 text-slate-500 text-left">
                <tr>
                  <th className="py-2.5 px-4 font-semibold w-16">Roll</th>
                  <th className="py-2.5 px-4 font-semibold">Student Name</th>
                  <th className="py-2.5 px-4 font-semibold">Admission No.</th>
                  <th className="py-2.5 px-4 font-semibold text-center w-72">Status</th>
                  <th className="py-2.5 px-4 font-semibold">Notes / Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {students.map((student) => {
                  const currentStatus = entries[student.id];
                  return (
                    <tr key={student.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-2.5 px-4 font-mono text-slate-500">
                        {student.roll_number || '—'}
                      </td>
                      <td className="py-2.5 px-4 font-medium text-slate-900">
                        {student.full_name}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-slate-500">
                        {student.admission_number}
                      </td>
                      <td className="py-2.5 px-4">
                        <div className="flex justify-center gap-1.5">
                          {['present', 'absent', 'late', 'excused'].map((st) => (
                            <button
                              key={st}
                              type="button"
                              onClick={() => handleStatusChange(student.id, st)}
                              className={`px-2.5 py-1 text-[11px] font-semibold rounded-md capitalize transition ${
                                currentStatus === st
                                  ? st === 'present'
                                    ? 'bg-emerald-600 text-white shadow-sm'
                                    : st === 'absent'
                                    ? 'bg-rose-600 text-white shadow-sm'
                                    : st === 'late'
                                    ? 'bg-amber-600 text-white shadow-sm'
                                    : 'bg-indigo-600 text-white shadow-sm'
                                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                              }`}
                            >
                              {st}
                            </button>
                          ))}
                        </div>
                      </td>
                      <td className="py-2.5 px-4">
                        <input
                          type="text"
                          value={notes[student.id] || ''}
                          onChange={(e) => {
                            const val = e.target.value;
                            setNotes((prev) => ({ ...prev, [student.id]: val }));
                            setSaveStatus((prev) => ({ ...prev, unsaved: true }));
                          }}
                          placeholder="Optional note"
                          className="w-full text-xs px-2.5 py-1 rounded border border-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
