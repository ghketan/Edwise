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
    <section className="glass-panel rounded-2xl p-5 shadow-sm min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-amber-100 text-accent-gold flex items-center justify-center shadow-sm">
            <Award className="w-4 h-4 shrink-0" />
          </div>
          <h2 className="font-bold text-sm text-on-surface">Achievement Badges</h2>
        </div>

        {rank !== null && rank !== undefined && (
          <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-status-amber-bg text-status-amber-text border border-amber-200 font-mono shadow-xs">
            Class Rank: #{rank}
            {totalInClass ? ` of ${totalInClass}` : ''}
          </span>
        )}
      </div>

      {badges.length === 0 ? (
        <div className="py-6 text-center text-xs text-outline border border-dashed border-slate-200 rounded-xl font-mono">
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
                className={`p-3.5 rounded-xl border flex flex-col justify-between transition-all min-w-0 ${
                  unlocked
                    ? 'glass-card border-indigo-200/90 shadow-xs ring-1 ring-indigo-100 hover:shadow-md'
                    : 'bg-surface-container-low/60 border-glass-border opacity-70'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2.5">
                    <div
                      className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
                      style={{
                        backgroundColor: unlocked ? `${accentColor}1a` : '#e2e8f0',
                        color: unlocked ? accentColor : '#64748b',
                      }}
                    >
                      <IconComponent className="w-4 h-4" />
                    </div>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full inline-flex items-center gap-1 font-mono ${
                        unlocked
                          ? 'bg-status-emerald-bg text-status-emerald-text border border-emerald-200'
                          : 'bg-surface-container-high text-outline'
                      }`}
                    >
                      {!unlocked && <Lock className="w-2.5 h-2.5" />}
                      {unlocked ? 'Unlocked' : 'Locked'}
                    </span>
                  </div>
                  <h3 className="font-bold text-xs text-on-surface break-words">
                    {badge.title}
                  </h3>
                  <p className="text-[11px] text-on-surface-variant mt-1 leading-relaxed break-words font-medium">
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
