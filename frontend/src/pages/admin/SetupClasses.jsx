import React, { useState, useEffect } from 'react';
import { institutionApi } from '../../api/institution';
import { extractApiError } from '../../utils/format';
import { School, BookOpen, Users, Plus, Check, AlertCircle, Trash2, Layers } from 'lucide-react';

export default function SetupClasses() {
  const [sessions, setSessions] = useState([]);
  const [classes, setClasses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [assignments, setAssignments] = useState([]);

  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState({ text: '', type: '' });

  // Form states
  const [newClass, setNewClass] = useState({ name: '', session_id: '', subject_ids: [] });
  const [newSubject, setNewSubject] = useState({ name: '', code: '' });
  const [newAssignment, setNewAssignment] = useState({
    session_id: '',
    class_id: '',
    section_id: '',
    subject_id: '',
    teacher_id: '',
  });

  // Class-specific subject management
  const [selectedClassId, setSelectedClassId] = useState('');
  const [classSubjects, setClassSubjects] = useState([]);
  const [assignExistingSubjectId, setAssignExistingSubjectId] = useState('');
  const [newClassSubject, setNewClassSubject] = useState({ name: '', code: '' });
  const [loadingClassSubjects, setLoadingClassSubjects] = useState(false);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [sess, cls, sub, tch, asg] = await Promise.all([
        institutionApi.getSessions().catch(() => []),
        institutionApi.getClasses().catch(() => []),
        institutionApi.getSubjects().catch(() => []),
        institutionApi.getTeachers().catch(() => []),
        institutionApi.getAllTeacherAssignments().catch(() => []),
      ]);
      setSessions(Array.isArray(sess) ? sess : []);
      setClasses(Array.isArray(cls) ? cls : []);
      setSubjects(Array.isArray(sub) ? sub : []);
      setTeachers(Array.isArray(tch) ? tch : []);
      setAssignments(Array.isArray(asg) ? asg : []);

      if (Array.isArray(sess) && sess.length > 0) {
        const active = sess.find((s) => s.is_active) || sess[0];
        setNewClass((prev) => ({ ...prev, session_id: String(active.id) }));
        setNewAssignment((prev) => ({ ...prev, session_id: String(active.id) }));
      }
      if (Array.isArray(cls) && cls.length > 0) {
        setSelectedClassId((prev) => prev || String(cls[0].id));
        setNewAssignment((prev) => ({ ...prev, class_id: String(cls[0].id) }));
      }
      if (Array.isArray(sub) && sub.length > 0) {
        setAssignExistingSubjectId((prev) => prev || String(sub[0].id));
        setNewAssignment((prev) => ({ ...prev, subject_id: String(sub[0].id) }));
      }
      if (Array.isArray(tch) && tch.length > 0) {
        setNewAssignment((prev) => ({ ...prev, teacher_id: String(tch[0].id) }));
      }
    } catch (err) {
      console.error(err);
      setMsg({ text: extractApiError(err, 'Error loading institution structure.'), type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedClassId) {
      loadClassSubjects(selectedClassId);
    }
  }, [selectedClassId]);

  const loadClassSubjects = async (classId) => {
    if (!classId) return;
    setLoadingClassSubjects(true);
    try {
      const subs = await institutionApi.getClassSubjects(classId);
      setClassSubjects(Array.isArray(subs) ? subs : []);
    } catch (err) {
      console.warn('Failed to load class subjects:', err);
      setClassSubjects([]);
    } finally {
      setLoadingClassSubjects(false);
    }
  };

  const handleCreateClass = async (e) => {
    e.preventDefault();
    try {
      const created = await institutionApi.createClass({
        name: newClass.name.trim(),
        session_id: parseInt(newClass.session_id, 10),
        subject_ids: newClass.subject_ids.length > 0 ? newClass.subject_ids.map((id) => parseInt(id, 10)) : undefined,
      });
      setMsg({ text: `Class "${newClass.name}" created successfully!`, type: 'success' });
      setNewClass((prev) => ({ ...prev, name: '', subject_ids: [] }));
      loadAll();
      if (created?.id) {
        setSelectedClassId(String(created.id));
      }
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to create class.'), type: 'error' });
    }
  };

  const handleAssignExistingSubjectToClass = async (e) => {
    e.preventDefault();
    if (!selectedClassId || !assignExistingSubjectId) return;
    try {
      await institutionApi.assignClassSubject(selectedClassId, {
        subject_id: parseInt(assignExistingSubjectId, 10),
      });
      setMsg({ text: 'Subject linked to class successfully!', type: 'success' });
      loadClassSubjects(selectedClassId);
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to assign subject to class.'), type: 'error' });
    }
  };

  const handleCreateAndAssignSubjectToClass = async (e) => {
    e.preventDefault();
    if (!selectedClassId || !newClassSubject.name.trim() || !newClassSubject.code.trim()) return;
    try {
      await institutionApi.assignClassSubject(selectedClassId, {
        name: newClassSubject.name.trim(),
        code: newClassSubject.code.trim().toUpperCase(),
      });
      setMsg({ text: `Subject "${newClassSubject.name}" created and configured for class!`, type: 'success' });
      setNewClassSubject({ name: '', code: '' });
      loadClassSubjects(selectedClassId);
      loadAll();
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to create and assign subject.'), type: 'error' });
    }
  };

  const handleRemoveSubjectFromClass = async (subjectId) => {
    if (!selectedClassId) return;
    try {
      await institutionApi.removeClassSubject(selectedClassId, subjectId);
      setMsg({ text: 'Subject unlinked from this class.', type: 'success' });
      loadClassSubjects(selectedClassId);
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to remove subject from class.'), type: 'error' });
    }
  };

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    try {
      await institutionApi.createSubject({
        name: newSubject.name.trim(),
        code: newSubject.code.trim().toUpperCase(),
      });
      setMsg({ text: `Subject "${newSubject.name}" created!`, type: 'success' });
      setNewSubject({ name: '', code: '' });
      loadAll();
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to create subject.'), type: 'error' });
    }
  };

  const handleAssignTeacher = async (e) => {
    e.preventDefault();
    try {
      await institutionApi.assignTeacher({
        session_id: parseInt(newAssignment.session_id, 10),
        class_id: parseInt(newAssignment.class_id, 10),
        section_id: newAssignment.section_id ? parseInt(newAssignment.section_id, 10) : null,
        subject_id: parseInt(newAssignment.subject_id, 10),
        teacher_id: parseInt(newAssignment.teacher_id, 10),
      });
      setMsg({ text: 'Teacher scope assignment registered successfully!', type: 'success' });
      loadAll();
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to assign teacher.'), type: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Classes & Faculty Setup</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Configure academic sessions, class grades, subjects, and bind teacher scoping per D-004.
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
          {msg.type === 'success' ? <Check className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          <span>{msg.text}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Classes Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4 text-indigo-700">
            <School className="w-4 h-4" />
            <h2 className="font-semibold text-sm text-slate-900">Configured Classes</h2>
          </div>

          <form onSubmit={handleCreateClass} className="flex gap-2 mb-4">
            <input
              type="text"
              required
              placeholder="e.g. Class 10"
              value={newClass.name}
              onChange={(e) => setNewClass({ ...newClass, name: e.target.value })}
              className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <select
              value={newClass.session_id}
              onChange={(e) => setNewClass({ ...newClass, session_id: e.target.value })}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            <button
              type="submit"
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg flex items-center gap-1 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" /> Add Class
            </button>
          </form>

          <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
            {classes.length === 0 ? (
              <p className="py-4 text-xs text-slate-400 text-center">No classes registered.</p>
            ) : (
              classes.map((c) => (
                <div
                  key={c.id}
                  onClick={() => setSelectedClassId(String(c.id))}
                  className={`py-2 px-2 flex items-center justify-between text-xs rounded-lg cursor-pointer transition ${
                    selectedClassId === String(c.id) ? 'bg-indigo-50 border border-indigo-200' : 'hover:bg-slate-50'
                  }`}
                >
                  <span className="font-medium text-slate-800">{c.name}</span>
                  <span className="text-slate-400 font-mono text-[11px]">Click to manage subjects</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Subjects Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4 text-indigo-700">
            <BookOpen className="w-4 h-4" />
            <h2 className="font-semibold text-sm text-slate-900">Curriculum Subjects Master List</h2>
          </div>

          <form onSubmit={handleCreateSubject} className="flex gap-2 mb-4">
            <input
              type="text"
              required
              placeholder="Name (e.g. Mathematics)"
              value={newSubject.name}
              onChange={(e) => setNewSubject({ ...newSubject, name: e.target.value })}
              className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <input
              type="text"
              required
              placeholder="Code (e.g. MATH10)"
              value={newSubject.code}
              onChange={(e) => setNewSubject({ ...newSubject, code: e.target.value })}
              className="w-24 px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg flex items-center gap-1 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" /> Add
            </button>
          </form>

          <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
            {subjects.length === 0 ? (
              <p className="py-4 text-xs text-slate-400 text-center">No curriculum subjects registered.</p>
            ) : (
              subjects.map((sub) => (
                <div key={sub.id} className="py-2 flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-800">{sub.name}</span>
                  <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-slate-600">
                    {sub.code}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Grade-Specific Subject Management (Independent Subjects per Grade) */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2 text-indigo-700">
            <Layers className="w-4 h-4" />
            <div>
              <h2 className="font-semibold text-sm text-slate-900">
                Independent Class Subjects Configuration
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Assign subjects independently to each class/grade so each grade has its own tailored curriculum.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-600">Select Grade:</label>
            <select
              value={selectedClassId}
              onChange={(e) => setSelectedClassId(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white font-medium focus:ring-2 focus:ring-indigo-500"
            >
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Current Class's Configured Subjects */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 mb-5">
          <div className="text-xs font-semibold text-slate-700 mb-2.5">
            Subjects for {classes.find((c) => String(c.id) === selectedClassId)?.name || 'Selected Grade'}:
          </div>

          {loadingClassSubjects ? (
            <p className="text-xs text-slate-400 py-2">Loading grade subjects...</p>
          ) : classSubjects.length === 0 ? (
            <p className="text-xs text-amber-700 bg-amber-50 p-3 rounded-lg border border-amber-200">
              No subjects currently configured for this grade. Use the forms below to link or create subjects for this grade.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {classSubjects.map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-200 shadow-sm text-xs font-medium text-slate-800"
                >
                  <span className="font-mono text-indigo-600 font-semibold text-[11px]">{sub.code}</span>
                  <span>{sub.name}</span>
                  <button
                    type="button"
                    title="Unlink subject from this grade"
                    onClick={() => handleRemoveSubjectFromClass(sub.id)}
                    className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Link / Create Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Link Existing Subject */}
          <form
            onSubmit={handleAssignExistingSubjectToClass}
            className="p-3.5 rounded-xl border border-slate-200 bg-white flex flex-col justify-between gap-3"
          >
            <div>
              <h4 className="text-xs font-semibold text-slate-800 mb-1">Link Existing Subject</h4>
              <p className="text-[11px] text-slate-500 mb-2">
                Choose an existing subject from master curriculum to add to this grade.
              </p>
              <select
                value={assignExistingSubjectId}
                onChange={(e) => setAssignExistingSubjectId(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-indigo-500"
              >
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={!selectedClassId || !assignExistingSubjectId}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-1 shadow-sm disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" /> Link Subject to Grade
            </button>
          </form>

          {/* Create & Link Brand New Subject */}
          <form
            onSubmit={handleCreateAndAssignSubjectToClass}
            className="p-3.5 rounded-xl border border-slate-200 bg-white flex flex-col justify-between gap-3"
          >
            <div>
              <h4 className="text-xs font-semibold text-slate-800 mb-1">Create New Subject for this Grade</h4>
              <p className="text-[11px] text-slate-500 mb-2">
                Create a subject specifically for this grade level.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  required
                  placeholder="Subject Name (e.g. Sanskrit)"
                  value={newClassSubject.name}
                  onChange={(e) => setNewClassSubject({ ...newClassSubject, name: e.target.value })}
                  className="flex-1 px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500"
                />
                <input
                  type="text"
                  required
                  placeholder="Code (e.g. SANS10)"
                  value={newClassSubject.code}
                  onChange={(e) => setNewClassSubject({ ...newClassSubject, code: e.target.value })}
                  className="w-24 px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 uppercase"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={!selectedClassId}
              className="px-3 py-1.5 bg-slate-900 hover:bg-black text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-1 shadow-sm disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" /> Create & Assign to Grade
            </button>
          </form>
        </div>
      </div>

      {/* Teacher Scoping (ClassSubjectTeacher) */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3 text-indigo-700">
          <Users className="w-4 h-4" />
          <h2 className="font-semibold text-sm text-slate-900">
            Teacher Scope Assignments (D-004 Enforcement)
          </h2>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Teachers receive server-enforced access to attendance, exams, and student analytics <em>only</em> for the classes and subjects assigned below.
        </p>

        <form onSubmit={handleAssignTeacher} className="grid grid-cols-1 sm:grid-cols-4 gap-2 mb-6">
          <select
            value={newAssignment.class_id}
            onChange={(e) => setNewAssignment({ ...newAssignment, class_id: e.target.value })}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                Class: {c.name}
              </option>
            ))}
          </select>

          <select
            value={newAssignment.subject_id}
            onChange={(e) => setNewAssignment({ ...newAssignment, subject_id: e.target.value })}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                Subject: {s.name}
              </option>
            ))}
          </select>

          <select
            value={newAssignment.teacher_id}
            onChange={(e) => setNewAssignment({ ...newAssignment, teacher_id: e.target.value })}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {teachers.map((t) => (
              <option key={t.id} value={t.id}>
                Teacher: {t.full_name} ({t.employee_id})
              </option>
            ))}
          </select>

          <button
            type="submit"
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-1 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" /> Bind Assignment
          </button>
        </form>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="py-2 px-3 font-semibold">Teacher</th>
                <th className="py-2 px-3 font-semibold">Class</th>
                <th className="py-2 px-3 font-semibold">Subject</th>
                <th className="py-2 px-3 font-semibold">Section</th>
                <th className="py-2 px-3 font-semibold">Authorization Scope</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {assignments.length === 0 ? (
                <tr>
                  <td colSpan="5" className="py-4 text-center text-slate-400">
                    No teacher scoping assignments configured yet.
                  </td>
                </tr>
              ) : (
                assignments.map((a) => {
                  const teach = teachers.find((t) => t.id === a.teacher_id);
                  const cls = classes.find((c) => c.id === a.class_id);
                  const sub = subjects.find((s) => s.id === a.subject_id);
                  return (
                    <tr key={a.id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-medium text-slate-900">
                        {teach ? `${teach.full_name} (${teach.employee_id})` : `Teacher #${a.teacher_id}`}
                      </td>
                      <td className="py-2.5 px-3">{cls ? cls.name : `Class #${a.class_id}`}</td>
                      <td className="py-2.5 px-3 font-semibold text-indigo-700">
                        {sub ? sub.name : `Subject #${a.subject_id}`}
                      </td>
                      <td className="py-2.5 px-3">{a.section_id ? `Section #${a.section_id}` : 'All Sections'}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                          Granted
                        </span>
                      </td>
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
