import React, { useState, useEffect } from 'react';
import { institutionApi } from '../../api/institution';
import { extractApiError } from '../../utils/format';
import { Users, Upload, UserPlus, CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react';

export default function RosterImport() {
  const [students, setStudents] = useState([]);
  const [classes, setClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState('');
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState({ text: '', type: '' });

  // Single student form
  const [newStudent, setNewStudent] = useState({
    admission_number: '',
    full_name: '',
    class_id: '',
    roll_number: '',
    contact_email: '',
  });

  // Bulk CSV parser state (UI-002: preview with row-level rejects before commit)
  const [csvText, setCsvText] = useState('');
  const [previewRows, setPreviewRows] = useState([]);
  const [parseErrors, setParseErrors] = useState([]);

  useEffect(() => {
    loadData();
  }, [selectedClass]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [clsList, stuList] = await Promise.all([
        institutionApi.getClasses(),
        institutionApi.getStudents(selectedClass ? parseInt(selectedClass, 10) : null),
      ]);
      setClasses(Array.isArray(clsList) ? clsList : []);
      setStudents(Array.isArray(stuList) ? stuList : []);
      if (Array.isArray(clsList) && clsList.length > 0 && !newStudent.class_id) {
        setNewStudent((prev) => ({ ...prev, class_id: String(clsList[0].id) }));
      }
    } catch (err) {
      console.error(err);
      setMsg({ text: extractApiError(err, 'Failed to load roster data.'), type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStudent = async (e) => {
    e.preventDefault();
    try {
      // Single student is imported via audited roster import protocol
      const payload = [{
        admission_number: newStudent.admission_number.trim(),
        full_name: newStudent.full_name.trim(),
        class_id: parseInt(newStudent.class_id, 10),
        roll_number: newStudent.roll_number.trim() || null,
        contact_email: newStudent.contact_email.trim() || null,
      }];
      const res = await institutionApi.importRoster(payload);
      setMsg({ text: res.message || `Student ${newStudent.full_name} added to roster!`, type: 'success' });
      setNewStudent({
        admission_number: '',
        full_name: '',
        class_id: classes[0]?.id ? String(classes[0].id) : '',
        roll_number: '',
        contact_email: '',
      });
      loadData();
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Failed to add student to roster.'), type: 'error' });
    }
  };

  const handleParseCsv = () => {
    setParseErrors([]);
    setPreviewRows([]);

    if (!csvText.trim()) return;

    const lines = csvText.trim().split('\n');
    const rows = [];
    const errors = [];

    // Format expected: admission_number, full_name, class_id, roll_number, contact_email
    lines.forEach((line, index) => {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) return;

      const cols = trimmed.split(',').map((c) => c.trim());
      if (cols.length < 3) {
        errors.push(`Row ${index + 1}: Insufficient columns (must have admission_no, full_name, class_id)`);
        return;
      }

      const [adm, name, cid, roll, email] = cols;
      const parsedCid = parseInt(cid, 10);
      if (isNaN(parsedCid)) {
        errors.push(`Row ${index + 1}: Invalid class_id "${cid}". Must be an integer.`);
        return;
      }

      rows.push({
        admission_number: adm,
        full_name: name,
        class_id: parsedCid,
        roll_number: roll || null,
        contact_email: email || null,
      });
    });

    setParseErrors(errors);
    setPreviewRows(rows);
  };

  const handleCommitImport = async () => {
    if (parseErrors.length > 0) {
      setMsg({ text: 'Resolve parse errors before committing import.', type: 'error' });
      return;
    }
    if (previewRows.length === 0) return;

    try {
      const res = await institutionApi.importRoster(previewRows);
      setMsg({ text: res.message || `Successfully imported ${previewRows.length} students!`, type: 'success' });
      setCsvText('');
      setPreviewRows([]);
      loadData();
    } catch (err) {
      setMsg({ text: extractApiError(err, 'Import failed.'), type: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Student Roster Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Maintain institutional student records and admission numbers for self-service claim (R-003, D-006).
          </p>
        </div>
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

      {/* Roster Import & Add Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Single Student Add */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4 text-indigo-700">
            <UserPlus className="w-4 h-4" />
            <h2 className="font-semibold text-sm text-slate-900">Add Individual Roster Record</h2>
          </div>

          <form onSubmit={handleCreateStudent} className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-slate-700">
                  Admission No. <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. STU1005"
                  value={newStudent.admission_number}
                  onChange={(e) => setNewStudent({ ...newStudent, admission_number: e.target.value })}
                  className="mt-1 block w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Emma Watson"
                  value={newStudent.full_name}
                  onChange={(e) => setNewStudent({ ...newStudent, full_name: e.target.value })}
                  className="mt-1 block w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-slate-700">Class</label>
                <select
                  value={newStudent.class_id}
                  onChange={(e) => setNewStudent({ ...newStudent, class_id: e.target.value })}
                  className="mt-1 block w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Roll Number</label>
                <input
                  type="text"
                  placeholder="e.g. 05"
                  value={newStudent.roll_number}
                  onChange={(e) => setNewStudent({ ...newStudent, roll_number: e.target.value })}
                  className="mt-1 block w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700">Official Email</label>
              <input
                type="email"
                placeholder="emma.watson@school.edu"
                value={newStudent.contact_email}
                onChange={(e) => setNewStudent({ ...newStudent, contact_email: e.target.value })}
                className="mt-1 block w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <button
              type="submit"
              className="mt-2 w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
            >
              Add Student to Roster
            </button>
          </form>
        </div>

        {/* Bulk CSV Import (UI-002: preview before commit) */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-2 text-indigo-700">
            <Upload className="w-4 h-4" />
            <h2 className="font-semibold text-sm text-slate-900">Bulk CSV Roster Import</h2>
          </div>
          <p className="text-[11px] text-slate-500 mb-3">
            Format: <code className="bg-slate-100 px-1 py-0.5 rounded">admission_number, full_name, class_id, roll_no, email</code>
          </p>

          <textarea
            rows={4}
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            placeholder={`STU2001, Grace Hopper, 1, 01, grace@school.edu\nSTU2002, Ada Lovelace, 1, 02, ada@school.edu`}
            className="w-full text-xs font-mono rounded-lg border border-slate-300 p-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />

          <div className="mt-2 flex justify-between items-center">
            <button
              type="button"
              onClick={handleParseCsv}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
            >
              Parse & Preview Rows
            </button>
            {previewRows.length > 0 && parseErrors.length === 0 && (
              <button
                type="button"
                onClick={handleCommitImport}
                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                Commit {previewRows.length} Rows
              </button>
            )}
          </div>

          {/* Row-level errors */}
          {parseErrors.length > 0 && (
            <div className="mt-3 p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 space-y-1">
              <div className="font-semibold flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> Parse Errors (No rows committed)
              </div>
              {parseErrors.map((err, i) => (
                <div key={i} className="text-[11px] font-mono">
                  {err}
                </div>
              ))}
            </div>
          )}

          {/* Preview rows table */}
          {previewRows.length > 0 && parseErrors.length === 0 && (
            <div className="mt-3 border border-emerald-200 rounded-lg overflow-hidden bg-emerald-50/30">
              <div className="px-3 py-1.5 bg-emerald-100/60 font-semibold text-[11px] text-emerald-800">
                Preview ({previewRows.length} rows ready for import)
              </div>
              <div className="max-h-36 overflow-y-auto text-[11px] p-2 space-y-1 font-mono">
                {previewRows.map((r, i) => (
                  <div key={i} className="flex justify-between border-b border-emerald-100 pb-0.5">
                    <span>{r.admission_number}: {r.full_name}</span>
                    <span className="text-slate-500">Class #{r.class_id}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Roster Records Table */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-indigo-600" />
            <h2 className="font-semibold text-sm text-slate-900">Current Student Rosters</h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 font-medium text-slate-600">
              {students.length} students
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">Filter Class:</span>
            <select
              value={selectedClass}
              onChange={(e) => setSelectedClass(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="py-2 px-3 font-semibold">Admission No.</th>
                <th className="py-2 px-3 font-semibold">Full Name</th>
                <th className="py-2 px-3 font-semibold">Class</th>
                <th className="py-2 px-3 font-semibold">Roll No.</th>
                <th className="py-2 px-3 font-semibold">Contact Email</th>
                <th className="py-2 px-3 font-semibold">Claim Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {students.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-4 text-center text-slate-400">
                    No students found for this class.
                  </td>
                </tr>
              ) : (
                students.map((s) => {
                  const cls = classes.find((c) => c.id === s.class_id);
                  return (
                    <tr key={s.id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-900">
                        {s.admission_number}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-slate-800">{s.full_name}</td>
                      <td className="py-2.5 px-3">{cls ? cls.name : `Class #${s.class_id}`}</td>
                      <td className="py-2.5 px-3">{s.roll_number || '—'}</td>
                      <td className="py-2.5 px-3 text-slate-500">{s.contact_email || '—'}</td>
                      <td className="py-2.5 px-3">
                        {s.is_roster_claimed ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                            <CheckCircle className="w-3 h-3" /> Claimed
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">
                            Unclaimed Roster
                          </span>
                        )}
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
