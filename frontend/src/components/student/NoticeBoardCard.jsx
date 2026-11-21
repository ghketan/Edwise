import React from 'react';
import { Megaphone } from 'lucide-react';
import { formatDateOnly } from '../../utils/format';

export default function NoticeBoardCard({ announcements = [] }) {
  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm min-w-0">
      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <Megaphone className="w-4 h-4 text-indigo-600 shrink-0" />
          <h2 className="font-semibold text-sm text-slate-900 truncate">
            Class Notice Board &amp; Announcements
          </h2>
        </div>
        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 shrink-0">
          {announcements.length} Notices
        </span>
      </div>

      {announcements.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
          No announcements posted for this session.
        </div>
      ) : (
        <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
          {announcements.map((ann) => {
            const isHigh = ann.priority === 'High';
            return (
              <div
                key={ann.id}
                className="p-3 rounded-lg border border-slate-200/80 bg-slate-50/50 min-w-0 break-words"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-xs text-slate-900 break-words min-w-0 flex-1">
                    {ann.title}
                  </h3>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0 ${
                      isHigh
                        ? 'bg-rose-100 text-rose-800 border border-rose-200'
                        : 'bg-sky-100 text-sky-800 border border-sky-200'
                    }`}
                  >
                    {isHigh ? 'High' : 'Normal'}
                  </span>
                </div>
                <p className="text-xs text-slate-600 mt-1.5 leading-relaxed break-words">
                  {ann.content}
                </p>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400 mt-2">
                  <span className="font-medium text-slate-500">
                    {ann.class_name || 'All Classes'}
                  </span>
                  <span>•</span>
                  <span>{ann.teacher_name || 'Administration'}</span>
                  <span>•</span>
                  <span className="font-mono">{formatDateOnly(ann.created_at)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
