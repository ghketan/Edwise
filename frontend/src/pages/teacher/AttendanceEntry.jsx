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
} from 'lucide-react';

export default function AttendanceEntry() {
  const { teacherProfile, teacherId, activeSession } = useAuth();
  const [scopes, setScopes] = useState([]);
  const [selectedScope, setSelectedScope] = useState('');
  const [date, setDate] = useState(() => getLocalDateString());
  const [students, setStudents] = useState([]);
  const [entries, setEntries] = useState({}); // { [student_id]: status }
  const [notes, setNotes] = useState({});

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); // { time, count, unsaved }
  const [error, setError] = useState('');

  const currentTeacherId = teacherId || teacherProfile?.id;

  // Load teacher's authorized class-subject scopes (D-004)
  useEffect(() => {
    if (currentTeacherId) {
      institutionApi
        .getTeacherAssignments(currentTeacherId, activeSession?.id)
        .then((asgs) => {
          if (Array.isArray(asgs)) {
            setScopes(asgs);
            if (asgs.length > 0) {
              setSelectedScope(String(asgs[0].id));
            }
          }
        })
        .catch((err) => {
          console.error('Failed to load teacher assignments:', err);
        });
    }
  }, [currentTeacherId, activeSession]);

  // When scope or date changes, load students and existing attendance records
  useEffect(() => {
    if (!selectedScope) return;
    const currentScope = scopes.find((s) => s.id === parseInt(selectedScope, 10));
    if (!currentScope) return;

    setLoading(true);
    setError('');
    // Clear previous entries immediately to prevent cross-scope contamination
    setEntries({});
    setNotes({});
    setSaveStatus(null);

    Promise.all([
      institutionApi.getStudents(currentScope.class_id, currentScope.section_id),
      academicsApi.getAttendance({
        session_id: currentScope.session_id,
        class_id: currentScope.class_id,
        subject_id: currentScope.subject_id,
        date: date, // Correct parameter alias
      }),
    ])
      .then(([stuList, attList]) => {
        setStudents(stuList || []);
        const map = {};
        const noteMap = {};
        let lastUpdated = null;
        if (Array.isArray(attList)) {
          attList.forEach((a) => {
            map[a.student_id] = a.status;
            if (a.notes) noteMap[a.student_id] = a.notes;
            if (a.updated_at) lastUpdated = a.updated_at;
          });
        }
        setEntries(map);
        setNotes(noteMap);
        setSaveStatus({
          time: lastUpdated ? `Recorded ${formatUtcTimestamp(lastUpdated)}` : (attList?.length > 0 ? 'Previously Recorded' : null),
          count: attList?.length || 0,
          unsaved: false,
        });
      })
      .catch((err) => {
        setError(extractApiError(err, 'Failed to load class attendance.'));
      })
      .finally(() => setLoading(false));
  }, [selectedScope, date, scopes]);

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
    const currentScope = scopes.find((s) => s.id === parseInt(selectedScope, 10));
    if (!currentScope) return;

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
      const res = await academicsApi.saveAttendance({
        session_id: currentScope.session_id,
        class_id: currentScope.class_id,
        section_id: currentScope.section_id,
        subject_id: currentScope.subject_id,
        date: date,
        records: entryList,
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

  const currentScopeObj = scopes.find((s) => s.id === parseInt(selectedScope, 10));

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Daily Attendance Entry</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Server-scoped attendance sheet (API-001, R-004). Unmarked students remain unrecorded.
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

      {/* Class & Date Selector Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase">
              Teaching Scope (D-004)
            </label>
            <select
              value={selectedScope}
              onChange={(e) => setSelectedScope(e.target.value)}
              className="mt-1 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {scopes.length === 0 && <option value="">No authorized scopes assigned</option>}
              {scopes.map((s) => (
                <option key={s.id} value={s.id}>
                  Class #{s.class_id} {s.section_id ? `(Sec #${s.section_id})` : ''} • Subject #{s.subject_id}
                </option>
              ))}
            </select>
          </div>

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
