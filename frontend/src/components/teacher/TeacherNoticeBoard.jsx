import React, { useState, useRef } from 'react';
import { Megaphone, Trash2, Send, CheckCircle2, AlertCircle, Clock, Tag } from 'lucide-react';
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
    <section className="glass-panel rounded-2xl p-5 shadow-sm min-w-0">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-xl bg-primary-container text-white flex items-center justify-center shadow-sm">
          <Megaphone className="w-4 h-4 shrink-0" />
        </div>
        <h2 className="font-bold text-sm text-on-surface">Class Notice Board &amp; Bulletins</h2>
      </div>

      {/* Publish Form */}
      <form
        onSubmit={handleSubmit}
        className="p-4 rounded-xl bg-surface-container-low/70 border border-glass-border mb-5 space-y-3"
      >
        <span className="text-xs font-bold text-on-surface block">Create New Notice</span>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <div className="sm:col-span-2">
            <label htmlFor="notice-title" className="sr-only">
              Notice Title
            </label>
            <input
              id="notice-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Notice Title (e.g. Science Fair Datesheet)"
              className="w-full text-xs rounded-xl border border-glass-border bg-surface-container-lowest px-3 py-2 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container"
            />
          </div>

          <div>
            <label htmlFor="notice-priority" className="sr-only">
              Priority
            </label>
            <select
              id="notice-priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full text-xs rounded-xl border border-glass-border bg-surface-container-lowest px-3 py-2 text-on-surface font-semibold focus:outline-none focus:ring-2 focus:ring-primary-container"
            >
              <option value="Normal">Normal Priority</option>
              <option value="High">High Priority</option>
              <option value="Urgent">Urgent Priority</option>
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="notice-target-class" className="sr-only">
            Target Cohort
          </label>
          <select
            id="notice-target-class"
            value={targetClassId}
            onChange={(e) => setTargetClassId(e.target.value)}
            className="w-full text-xs rounded-xl border border-glass-border bg-surface-container-lowest px-3 py-2 text-on-surface font-semibold focus:outline-none focus:ring-2 focus:ring-primary-container"
          >
            <option value="">All Classes</option>
            {scopedClasses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="notice-content" className="sr-only">
            Notice Body
          </label>
          <textarea
            id="notice-content"
            rows={2}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Detailed announcement content and instructions..."
            className="w-full text-xs rounded-xl border border-glass-border bg-surface-container-lowest p-3 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container"
          />
        </div>

        {msg.text && (
          <div
            className={`p-2.5 rounded-xl text-xs font-medium flex items-center gap-2 ${
              msg.type === 'success'
                ? 'bg-status-emerald-bg text-status-emerald-text border border-emerald-200'
                : 'bg-status-rose-bg text-status-rose-text border border-rose-200'
            }`}
          >
            {msg.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{msg.text}</span>
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-primary-container hover:opacity-95 rounded-xl shadow-md shadow-indigo-200 transition-all active:scale-[0.98] disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{submitting ? 'Publishing...' : 'Publish Notice'}</span>
          </button>
        </div>
      </form>

      {/* Notices List */}
      <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
        {announcements.length === 0 ? (
          <div className="py-6 text-center text-xs text-outline border border-dashed border-slate-200 rounded-xl font-mono">
            No notices published yet.
          </div>
        ) : (
          announcements.map((item) => {
            const itemTeacherId = item.teacher_id ?? item.author_teacher_id;
            const isAuthor =
              role === 'ADMINISTRATOR' ||
              (currentTeacherId && itemTeacherId === currentTeacherId);
            const isHigh = item.priority === 'urgent' || item.priority === 'high' || item.priority === 'High';

            return (
              <div
                key={item.id}
                className="p-3.5 rounded-xl border border-glass-border bg-surface-container-lowest/80 shadow-xs space-y-2 hover:border-slate-300 transition-all min-w-0 break-words"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full font-mono ${
                        isHigh
                          ? 'bg-status-rose-bg text-status-rose-text border border-rose-200'
                          : 'bg-surface-container-high text-outline'
                      }`}
                    >
                      {item.priority ? `${item.priority} Priority` : 'Normal'}
                    </span>
                    <span className="text-xs font-bold text-on-surface">{item.title}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-outline font-mono">
                      {formatDateOnly(item.created_at)}
                    </span>
                    {isAuthor && (
                      <button
                        onClick={() => handleDelete(item.id)}
                        disabled={deletingId === item.id}
                        title="Delete Notice"
                        aria-label="Delete Notice"
                        className="p-1 text-outline hover:text-rose-600 hover:bg-status-rose-bg rounded-lg transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                <p className="text-xs text-on-surface-variant leading-relaxed break-words font-medium">
                  {item.content}
                </p>

                <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[10px] text-outline font-mono">
                  <span className="inline-flex items-center gap-1 font-sans">
                    <Tag className="w-3 h-3 text-secondary" />
                    {item.target_class_name || 'All Classes'}
                  </span>
                  <span>By {item.author_name || 'Administration'}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
