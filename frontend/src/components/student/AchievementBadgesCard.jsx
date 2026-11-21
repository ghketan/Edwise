import React from 'react';
import { Trophy, CalendarCheck, Zap, Star, Rocket, Award, Lock } from 'lucide-react';

const ICON_MAP = {
  trophy: Trophy,
  'calendar-check': CalendarCheck,
  zap: Zap,
  star: Star,
  rocket: Rocket,
};

export default function AchievementBadgesCard({ badgeData = null }) {
  const badges = Array.isArray(badgeData?.badges) ? badgeData.badges : [];
  const rank = badgeData?.rank;
  const totalInClass = badgeData?.total_students_in_class;

  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <Award className="w-4 h-4 text-amber-500 shrink-0" />
          <h2 className="font-semibold text-sm text-slate-900">Achievement Badges</h2>
        </div>

        {rank !== null && rank !== undefined && (
          <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
            Class Rank: #{rank}
            {totalInClass ? ` of ${totalInClass}` : ''}
          </span>
        )}
      </div>

      {badges.length === 0 ? (
        <div className="py-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
          No badge criteria loaded for this session.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {badges.map((badge) => {
            const IconComponent = ICON_MAP[badge.icon] || Award;
            const unlocked = Boolean(badge.unlocked);
            const accentColor = badge.color || '#4f46e5';

            return (
              <div
                key={badge.id}
                className={`p-3.5 rounded-xl border flex flex-col justify-between transition min-w-0 ${
                  unlocked
                    ? 'bg-white border-indigo-200 shadow-sm ring-1 ring-indigo-100'
                    : 'bg-slate-50 border-slate-200 opacity-75'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2.5">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                      style={{
                        backgroundColor: unlocked ? `${accentColor}1a` : '#e2e8f0',
                        color: unlocked ? accentColor : '#64748b',
                      }}
                    >
                      <IconComponent className="w-4 h-4" />
                    </div>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${
                        unlocked
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {!unlocked && <Lock className="w-2.5 h-2.5" />}
                      {unlocked ? 'Unlocked' : 'Locked'}
                    </span>
                  </div>
                  <h3 className="font-semibold text-xs text-slate-900 break-words">
                    {badge.title}
                  </h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed break-words">
                    {badge.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
