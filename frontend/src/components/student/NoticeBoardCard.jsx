import React from 'react';
import { Bell, Tag, Clock, User } from 'lucide-react';
import { formatUtcTimestamp } from '../../utils/format';

export default function NoticeBoardCard({ announcements = [] }) {
  return (
    <section className="glass-panel rounded-2xl p-5 shadow-sm min-w-0">
      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-status-sky-bg text-status-sky-text flex items-center justify-center shadow-sm">
            <Bell className="w-4 h-4 shrink-0" />
          </div>
          <h2 className="font-bold text-sm text-on-surface truncate">
            Notice Board &amp; Announcements
          </h2>
        </div>
        <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-surface-container-low text-secondary border border-glass-border font-mono shrink-0">
          {announcements.length} Notices
        </span>
      </div>

      {announcements.length === 0 ? (
        <div className="py-8 text-center text-xs text-outline border border-dashed border-slate-200 rounded-xl font-mono">
          No notices posted for your class yet.
        </div>
      ) : (
        <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
          {announcements.map((item) => {
            const isHigh = item.priority === 'urgent' || item.priority === 'high';
            return (
              <div
                key={item.id}
                className="p-3.5 rounded-xl border border-glass-border bg-surface-container-lowest/80 shadow-xs hover:border-slate-300 transition-all min-w-0 break-words"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full font-mono ${
                      isHigh
                        ? 'bg-status-rose-bg text-status-rose-text border border-rose-200'
                        : 'bg-surface-container-high text-outline'
                    }`}
                  >
                    {item.priority ? `${item.priority} Priority` : 'Notice'}
                  </span>
                  <div className="flex items-center gap-1.5 text-[11px] text-outline font-mono">
                    <Clock className="w-3 h-3" />
                    <span>{formatUtcTimestamp(item.created_at)}</span>
                  </div>
                </div>

                <h3 className="font-bold text-xs text-on-surface break-words">{item.title}</h3>
                <p className="text-xs text-on-surface-variant mt-1 leading-relaxed break-words font-medium">
                  {item.content}
                </p>

                <div className="mt-2.5 pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[10px] text-outline font-mono">
                  <span className="inline-flex items-center gap-1 font-sans">
                    <Tag className="w-3 h-3 text-secondary" />
                    {item.target_class_name || 'All Classes'}
                  </span>
                  <span className="inline-flex items-center gap-1 font-sans">
                    <User className="w-3 h-3 text-primary" />
                    {item.author_name || 'Administration'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
