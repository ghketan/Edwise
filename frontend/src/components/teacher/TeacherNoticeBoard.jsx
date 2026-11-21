import React, { useState, useRef } from 'react';
import { Megaphone, Trash2, Send, CheckCircle2, AlertCircle } from 'lucide-react';
import { announcementsApi } from '../../api/announcements';
import { extractApiError, formatDateOnly } from '../../utils/format';

export default function TeacherNoticeBoard({
  announcements = [],
  scopedClasses = [],
  sessionId,
  currentTeacherId = null,
  role = 'TEACHER',
  onCreated,
  onDeleted,
}) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [priority, setPriority] = useState('Normal');
  const [targetClassId, setTargetClassId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [msg, setMsg] = useState({ text: '', type: '' });
  const submittingRef = useRef(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submittingRef.current) return;
    setMsg({ text: '', type: '' });

    const cleanTitle = title.trim();
    const cleanContent = content.trim();
    if (!cleanTitle || !cleanContent) {
      setMsg({ text: 'Title and content are required.', type: 'error' });
      return;
    }
    if (!sessionId) {
      setMsg({ text: 'Active academic session is required.', type: 'error' });
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    try {
      const created = await announcementsApi.createAnnouncement({
        session_id: sessionId,
        class_id: targetClassId ? Number(targetClassId) : null,
        title: cleanTitle,
        content: cleanContent,
        priority,
      });
      setTitle('');
      setContent('');
      setPriority('Normal');
      setMsg({ text: 'Announcement published successfully.', type: 'success' });
      onCreated?.(created);
    } catch (err) {
      setMsg({
        text: extractApiError(err, 'Failed to publish announcement.'),
        type: 'error',
      });
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  const handleDelete = async (annId) => {
    setMsg({ text: '', type: '' });
    setDeletingId(annId);
    try {
      await announcementsApi.deleteAnnouncement(annId);
      onDeleted?.(annId);
    } catch (err) {
      setMsg({
        text: extractApiError(err, 'Failed to delete announcement.'),
        type: 'error',
      });
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm min-w-0">
      <hgroup className="flex items-center justify-between gap-2 mb-4">
        <span className="flex items-center gap-2 min-w-0">
          <Megaphone className="w-4 h-4 text-indigo-600 shrink-0" />
          <h2 className="font-semibold text-sm text-slate-900">
            Class Notice Board &amp; Announcements
          </h2>
        </span>
        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 shrink-0">
          {announcements.length} Posted
        </span>
      </hgroup>

      {/* Create Announcement Form */}
      <form
        onSubmit={handleSubmit}
        className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 mb-5 space-y-3"
      >
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-1">
            <label className="block text-[11px] font-semibold text-slate-500 uppercase mb-1">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Announcement title..."
              className="w-full text-xs px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase mb-1">
              Priority
            </label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="Normal">Normal</option>
              <option value="High">High</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase mb-1">
              Target Class (All Classes / Specific)
            </label>
            <select
              value={targetClassId}
              onChange={(e) => setTargetClassId(e.target.value)}
              className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Classes</option>
              {scopedClasses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <textarea
            rows="2"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Announcement content and details..."
            className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {msg.text && (
          <div
            className={`p-2 rounded-lg text-xs flex items-center gap-1.5 ${
              msg.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}
          >
            {msg.type === 'success' ? (
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            )}
            <span className="break-words min-w-0">{msg.text}</span>
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            {submitting ? 'Posting...' : 'Post Announcement'}
          </button>
        </div>
      </form>

      {/* Announcements List */}
      {announcements.length === 0 ? (
        <p className="py-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
          No announcements posted for this session.
        </p>
      ) : (
        <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
          {announcements.map((ann) => {
            const isHigh = ann.priority === 'High';
            const canDelete =
              role === 'ADMINISTRATOR' ||
              (currentTeacherId && ann.teacher_id === currentTeacherId);

            return (
              <div
                key={ann.id}
                className="p-3.5 rounded-lg border border-slate-200/80 bg-slate-50/50 flex flex-col sm:flex-row sm:items-start justify-between gap-3 min-w-0 break-words"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-xs text-slate-900 break-words">
                      {ann.title}
                    </h3>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                        isHigh
                          ? 'bg-rose-100 text-rose-800 border border-rose-200'
                          : 'bg-sky-100 text-sky-800 border border-sky-200'
                      }`}
                    >
                      {isHigh ? 'High' : 'Normal'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed break-words">
                    {ann.content}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400 mt-1.5">
                    <span className="font-medium text-slate-600">
                      {ann.class_name || 'All Classes'}
                    </span>
                    <span>•</span>
                    <span>{ann.teacher_name || 'Administration'}</span>
                    <span>•</span>
                    <span className="font-mono">{formatDateOnly(ann.created_at)}</span>
                  </div>
                </div>

                {canDelete && (
                  <button
                    type="button"
                    onClick={() => handleDelete(ann.id)}
                    disabled={deletingId === ann.id}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-white border border-rose-200 text-rose-700 hover:bg-rose-50 transition shrink-0 self-start disabled:opacity-50"
                  >
                    <Trash2 className="w-3 h-3" />
                    {deletingId === ann.id ? 'Deleting...' : 'Delete'}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
