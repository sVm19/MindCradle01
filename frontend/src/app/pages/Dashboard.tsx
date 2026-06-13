import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { mood as moodApi, resources as resourcesApi, ai as aiApi, profile as profileApi } from '@/lib/api';
import type { ResourceItem } from '@/lib/api';
import { Lock, Award, Sprout, BarChart3, Settings, Moon, Wind, PenTool } from 'lucide-react';

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const SHORT_DAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export default function Dashboard() {
  const { user } = useAuth();

  // Mood data
  const [moodItems, setMoodItems] = useState<{ created: string; level: number }[]>([]);
  const [calmScore, setCalmScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [weekBars, setWeekBars] = useState<{ day: string; score: number }[]>([]);

  // Resources
  const [recResources, setRecResources] = useState<ResourceItem[]>([]);

  // AI Insight
  const [ariaInsight, setAriaInsight] = useState('');
  const [ariaLoading, setAriaLoading] = useState(true);

  // Recovery patterns
  const [recoveryData, setRecoveryData] = useState<{ history: any[]; stats: any } | null>(null);
  const [showRecoveryWidget, setShowRecoveryWidget] = useState(true);

  // Engagement stats & settings
  const [engagementStats, setEngagementStats] = useState<any | null>(null);
  const [emergencyContact, setEmergencyContact] = useState('');
  const [savingContact, setSavingContact] = useState(false);

  const handleSaveContact = () => {
    setSavingContact(true);
    profileApi.update({ emergency_contact: emergencyContact })
      .then((res) => {
        alert('Emergency contact saved.');
      })
      .catch((err) => {
        console.error('Failed to update emergency contact:', err);
      })
      .finally(() => {
        setSavingContact(false);
      });
  };

  useEffect(() => {
    // Fetch mood history
    moodApi.history('7d').then((res) => {
      const items = res.items;
      setMoodItems(items);

      // Unique days with any activity → streak
      const uniqueDates = new Set(items.map((i) => i.created.slice(0, 10)));
      setStreak(uniqueDates.size);

      // Average level → calm score (scale 1-10 to 0-100)
      if (items.length > 0) {
        const avg = items.reduce((s, i) => s + i.level, 0) / items.length;
        setCalmScore(Math.round((avg / 10) * 100));
      }

      // Build week bar data (last 7 days)
      const today = new Date();
      const bars = Array.from({ length: 7 }, (_, idx) => {
        const d = new Date(today);
        d.setDate(today.getDate() - (6 - idx));
        const key = d.toISOString().slice(0, 10);
        const dayItems = items.filter((i) => i.created.slice(0, 10) === key);
        const score = dayItems.length
          ? Math.round((dayItems.reduce((s, i) => s + i.level, 0) / dayItems.length / 10) * 100)
          : 0;
        return { day: SHORT_DAYS[d.getDay()], score };
      });
      setWeekBars(bars);
    }).catch(() => {});

    // Fetch resources
    resourcesApi.list().then((res) => {
      setRecResources(res.items.slice(0, 3));
    }).catch(() => {});

    // Fetch ARIA daily insight
    aiApi.chat(
      'Give me a brief single-sentence daily insight or gentle encouragement based on my recent well-being patterns. Keep it under 30 words, warm and specific.'
    ).then((res) => {
      setAriaInsight(res.reply);
    }).catch(() => {
      setAriaInsight('Your steadier days tend to follow moments when you pair a small ritual with a clear boundary. Tonight would be a good night to close the loop gently.');
    }).finally(() => {
      setAriaLoading(false);
    });

    // Fetch recovery patterns
    aiApi.getRecoveryPatterns().then((data) => {
      setRecoveryData(data);
    }).catch(() => {});

    // Fetch profile settings
    profileApi.get().then((res) => {
      if (res) {
        setEmergencyContact(res.emergency_contact || '');
      }
    }).catch(() => {});

    // Fetch engagement stats
    aiApi.getEngagementStats().then((res) => {
      setEngagementStats(res);
    }).catch(() => {});
  }, []);

  const dashDots = (226 * calmScore) / 100;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Today's Rituals */}
      <section>
        <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium mb-4">
          Today's Rituals
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Link
            to="/morning"
            className="bg-bg2 border border-border rounded-[20px] px-6 py-5 cursor-pointer relative overflow-hidden"
          >
            <div className="text-[10px] tracking-[0.12em] uppercase text-text3 mb-2.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-accent shadow-[0_0_8px_var(--accent)]" /> Ritual
            </div>
            <div className="font-[family-name:var(--font-serif)] text-xl font-light text-text mb-3">
              Morning Ritual
            </div>
            <div className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-amber-dim text-amber border border-amber/20 mb-4">
              ⏳ Pending
            </div>
            <div className="flex items-center gap-1.5 text-[12.5px] text-accent font-medium mt-1">
              Begin →
            </div>
          </Link>

          <Link
            to="/wind-down"
            className="bg-bg2 border border-border rounded-[20px] px-6 py-5 cursor-pointer relative overflow-hidden"
          >
            <div className="text-[10px] tracking-[0.12em] uppercase text-text3 mb-2.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-teal shadow-[0_0_8px_var(--teal)]" /> Evening Ritual
            </div>
            <div className="font-[family-name:var(--font-serif)] text-xl font-light text-text mb-3">
              Wind Down
            </div>
            <div className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-amber-dim text-amber border border-amber/20 mb-4">
              ⏳ Pending
            </div>
            <div className="flex items-center gap-1.5 text-[12.5px] text-accent font-medium">
              Begin →
            </div>
            <div className="text-[11px] text-text3 mt-1.5">Available at 9:00 PM</div>
          </Link>
        </div>
      </section>

      {/* Status Strip */}
      <section>
        <div className="bg-bg2 border border-border rounded-[14px] px-5 py-4 flex gap-6 items-center">
          <div className="flex items-center gap-2.5 flex-1">
            <div className="w-2 h-2 rounded-full bg-green shadow-[0_0_8px_var(--green)] flex-shrink-0" />
            <div className="text-[13px]">
              <div className="text-text mb-0.5">Morning</div>
              <div className="text-[11px] text-text3">Still available today</div>
            </div>
          </div>
          <div className="w-px h-8 bg-border" />
          <div className="flex items-center gap-2.5 flex-1">
            <div className="w-2 h-2 rounded-full bg-amber shadow-[0_0_8px_var(--amber)] flex-shrink-0" />
            <div className="text-[13px]">
              <div className="text-text mb-0.5">Wind Down</div>
              <div className="text-[11px] text-text3">Unlocks at 9:00 PM</div>
            </div>
          </div>
          <div className="w-px h-8 bg-border" />
          <div className="text-right flex-0">
            <div className="text-[11px] text-text3 mb-0.5">Consecutive days</div>
            <div className="font-[family-name:var(--font-serif)] text-[22px] font-light text-text">{streak}</div>
          </div>
        </div>
      </section>

      {/* Weekly Calm + AI Insight */}
      <div className="grid grid-cols-2 gap-4">
        <section>
          <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium mb-4">
            Weekly Calm Score
          </div>
          <div className="bg-bg2 border border-border rounded-[20px] px-6 py-6 flex gap-6 items-start">
            <div className="w-[90px] h-[90px] flex-shrink-0 relative">
              <svg width="90" height="90" viewBox="0 0 90 90" className="-rotate-90">
                <circle cx="45" cy="45" r="36" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
                <circle
                  cx="45"
                  cy="45"
                  r="36"
                  fill="none"
                  stroke="url(#calmGrad)"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={`${dashDots} 226`}
                  style={{ transition: 'stroke-dasharray 0.8s ease' }}
                />
                <defs>
                  <linearGradient id="calmGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#6c5ce7" />
                    <stop offset="100%" stopColor="#4ecdc4" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="font-[family-name:var(--font-serif)] text-[22px] font-light text-text">{calmScore}</div>
                <div className="text-[9px] text-text3 uppercase tracking-[0.08em]">/ 100</div>
              </div>
            </div>
            <div className="flex-1">
              <div className="text-[15px] font-medium text-text mb-1">Your Weekly Score</div>
              <div className="text-[12.5px] text-text2 mb-3.5">
                {moodItems.length === 0 ? 'Complete rituals to build your score' : `Based on ${moodItems.length} check-in${moodItems.length !== 1 ? 's' : ''}`}
              </div>
              <div className="flex gap-1.5 items-end h-10">
                {weekBars.map((bar, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1.5">
                    <div
                      className="w-full rounded-t transition-all duration-500"
                      style={{
                        height: `${Math.max(4, (bar.score / 100) * 32)}px`,
                        background: bar.score > 0 ? 'linear-gradient(to top, #6c5ce7, #4ecdc4)' : 'rgba(255,255,255,0.08)',
                      }}
                    />
                    <div className="text-[10px] text-text3">{bar.day}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section>
          <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium mb-4">
            AI Companion
          </div>
          <div className="bg-bg2 border border-border rounded-[20px] px-6 py-5 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 bottom-0 bg-[radial-gradient(ellipse_at_top_right,rgba(139,124,248,0.06),transparent_60%)] pointer-events-none" />
            <div className="flex items-center gap-2.5 mb-3.5">
              <div className="text-[10px] tracking-[0.12em] uppercase text-accent bg-accent-glow border border-accent/20 px-2.5 py-1 rounded-full">
                ✦ ARIA Insight
              </div>
            </div>
            <div className="font-[family-name:var(--font-serif)] text-base font-light text-text leading-relaxed italic mb-4 min-h-[60px]">
              {ariaLoading ? (
                <span className="text-text3 text-sm not-italic">ARIA is thinking…</span>
              ) : (
                `"${ariaInsight}"`
              )}
            </div>
            <Link
              to="/aria"
              className="inline-flex items-center gap-1.5 text-[12.5px] text-accent font-medium bg-accent-glow border border-accent/25 px-4 py-2 rounded-full hover:bg-accent/20 transition-all"
            >
              Explore Toolkit →
            </Link>
          </div>
        </section>
      </div>

      {/* Recommended */}
      <section>
        <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium mb-4">
          Recommended For You
        </div>
        <div className="flex flex-col gap-2.5">
          {recResources.length > 0 ? (
            recResources.map((item, i) => (
              <div
                key={item.id}
                className="bg-bg2 border border-border rounded-[14px] px-5 py-4 flex items-center gap-4 cursor-pointer hover:border-border2 transition-all"
                onClick={() => item.url && window.open(item.url, '_blank')}
              >
                <div className="w-11 h-11 rounded-lg flex items-center justify-center text-lg flex-shrink-0 bg-accent-glow text-accent">
                  {item.icon || '✦'}
                </div>
                <div className="flex-1">
                  <div className="text-[10px] uppercase tracking-wider text-text3 mb-0.5">{item.category}</div>
                  <div className="text-sm text-text">{item.title}</div>
                </div>
                <div className="text-sm text-text3">→ Open</div>
              </div>
            ))
          ) : (
            [
              { type: 'Sleep Story', name: 'The Observatory', icon: <Moon className="w-5 h-5 text-teal-400" /> },
              { type: 'Breathwork', name: 'Box Breath', icon: <Wind className="w-5 h-5 text-sky-400" /> },
              { type: 'Micro-Journal', name: '3 Bullet Reflection', icon: <PenTool className="w-5 h-5 text-indigo-400" /> },
            ].map((item, i) => (
              <div
                key={i}
                className="bg-bg2 border border-border rounded-[14px] px-5 py-4 flex items-center gap-4 cursor-pointer hover:border-border2 transition-all"
              >
                <div className="w-11 h-11 rounded-lg flex items-center justify-center text-lg flex-shrink-0 bg-accent-glow text-accent">
                  {item.icon}
                </div>
                <div className="flex-1">
                  <div className="text-[10px] uppercase tracking-wider text-text3 mb-0.5">{item.type}</div>
                  <div className="text-sm text-text">{item.name}</div>
                </div>
                <div className="text-sm text-text3">
                  {i === 0 ? '▶ Play' : i === 1 ? '→ Start' : '→ Write'}
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Recovery Progress Widget */}
      {recoveryData && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium flex items-center gap-2">
              <span className="flex items-center gap-1.5">
                <Sprout size={16} /> Recovery Progress
              </span>
              {recoveryData.stats.average_recovery_days > 0 && (
                <span className="text-[9px] bg-accent/10 border border-accent/20 text-accent px-2 py-0.5 rounded-full font-sans normal-case tracking-normal">
                  {recoveryData.stats.trend_description}
                </span>
              )}
            </div>
            <button
              onClick={() => setShowRecoveryWidget(!showRecoveryWidget)}
              className="text-xs text-text3 hover:text-text hover:underline focus:outline-none bg-transparent border-0 cursor-pointer"
            >
              {showRecoveryWidget ? 'Hide Details' : 'Show Details'}
            </button>
          </div>

          {showRecoveryWidget && (
            <div className="bg-bg2 border border-border rounded-[20px] p-6 space-y-6">
              {recoveryData.stats.average_recovery_days === 0 ? (
                <div className="text-center py-8 text-xs text-text3 italic">
                  Not enough wellness logs to compute recovery patterns yet. Continue logging your mood!
                </div>
              ) : (
                <>
                  {/* Overview Stats Grid */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-bg3 border border-border/50 rounded-xl p-4 text-center">
                      <div className="text-2xl font-light font-[family-name:var(--font-serif)] text-accent">
                        {recoveryData.stats.average_recovery_days} <span className="text-xs">days</span>
                      </div>
                      <div className="text-[10px] text-text3 uppercase tracking-wider mt-1.5">
                        Avg Recovery Time
                      </div>
                    </div>

                    <div className="bg-bg3 border border-border/50 rounded-xl p-4 text-center">
                      <div className="text-2xl font-light font-[family-name:var(--font-serif)] text-teal">
                        {recoveryData.stats.fastest_recovery_days || 0} <span className="text-xs">days</span>
                      </div>
                      <div className="text-[10px] text-text3 uppercase tracking-wider mt-1.5 truncate">
                        Fastest: {recoveryData.stats.fastest_recovery_catalyst || 'baseline'}
                      </div>
                    </div>

                    <div className="bg-bg3 border border-border/50 rounded-xl p-4 text-center">
                      <div className="text-2xl font-light font-[family-name:var(--font-serif)] text-rose">
                        {recoveryData.stats.longest_recovery_days || 0} <span className="text-xs">days</span>
                      </div>
                      <div className="text-[10px] text-text3 uppercase tracking-wider mt-1.5 truncate">
                        Longest: {recoveryData.stats.longest_recovery_catalyst || 'isolation'}
                      </div>
                    </div>
                  </div>

                  {/* Recovery Logs Timeline */}
                  {recoveryData.history.length > 0 && (
                    <div className="space-y-3 pt-2">
                      <div className="text-[10px] tracking-wider uppercase text-text3 font-medium">
                        Recovery History
                      </div>
                      <div className="space-y-2.5 max-h-[220px] overflow-y-auto pr-1">
                        {recoveryData.history.slice(0, 5).map((log) => {
                          const dipDate = new Date(log.mood_dip_date).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                          });

                          return (
                            <div
                              key={log.id}
                              className="bg-bg3/40 border border-border/40 hover:border-border rounded-xl px-4 py-3 flex items-center justify-between gap-4 transition-all"
                            >
                              <div className="flex items-center gap-3">
                                <span className={`w-2 h-2 rounded-full ${log.severity === 'severe' ? 'bg-rose' : 'bg-amber'}`} />
                                <div>
                                  <div className="text-xs font-medium text-text">
                                    Dip to {log.lowest_level}/10 on {dipDate}
                                  </div>
                                  <div className="text-[10.5px] text-text3 mt-0.5">
                                    Catalyst: {log.catalyst || 'unknown'}
                                  </div>
                                </div>
                              </div>
                              <div className="text-right">
                                <span className="text-xs font-semibold text-accent">
                                  {log.recovery_days ? `${log.recovery_days}d recovery` : 'Ongoing dip'}
                                </span>
                                <div className="text-[9px] text-text3 uppercase tracking-wider mt-0.5">
                                  {log.severity}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </section>
      )}

      {/* Milestones */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium">Milestones</div>
          <a href="#" className="text-xs text-text3 no-underline">View All →</a>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { name: 'First Light', unlocked: moodItems.length >= 1 },
            { name: '7-Day Grounded', unlocked: streak >= 7 },
            { name: 'Night Owl', unlocked: false },
            { name: 'Pattern Seeker', unlocked: false },
            { name: '30-Day Observer', unlocked: false },
            { name: 'Clarity Seeker', unlocked: false },
          ].map((badge, i) => (
            <div
              key={i}
              className={`bg-bg2 border border-border rounded-[14px] px-4 py-4 text-center transition-all ${badge.unlocked ? 'opacity-100' : 'opacity-40'}`}
            >
              <div className="w-10 h-10 rounded-full bg-bg4 mx-auto mb-2.5 flex items-center justify-center text-base text-text3">
                {badge.unlocked ? (
                  <Award size={18} className="text-amber animate-pulse" />
                ) : (
                  <Lock size={18} className="text-text3" />
                )}
              </div>
              <div className="text-[12.5px] text-text mb-0.5">{badge.name}</div>
              <div className="text-[11px] text-text3">{badge.unlocked ? 'Earned' : 'Locked'}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Engagement Stats Section */}
      {engagementStats && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium flex items-center gap-2">
              <span className="flex items-center gap-1.5">
                <BarChart3 size={16} /> ARIA Engagement & A/B Insights
              </span>
            </div>
          </div>
          
          <div className="bg-bg2 border border-border rounded-[20px] p-6 space-y-6">
            {/* Overall stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-bg3 border border-border/50 rounded-xl p-4 text-center">
                <div className="text-2xl font-light font-[family-name:var(--font-serif)] text-accent">
                  {engagementStats.avg_response_time > 0 ? `${engagementStats.avg_response_time}s` : '--'}
                </div>
                <div className="text-[10px] text-text3 uppercase tracking-wider mt-1.5">
                  Average Response Speed
                </div>
              </div>

              <div className="bg-bg3 border border-border/50 rounded-xl p-4 text-center">
                <div className="text-2xl font-light font-[family-name:var(--font-serif)] text-teal">
                  {engagementStats.return_rate_24h}%
                </div>
                <div className="text-[10px] text-text3 uppercase tracking-wider mt-1.5">
                  24-Hour Return Visit Rate
                </div>
              </div>
            </div>

            {/* A/B Tests */}
            <div className="space-y-4 pt-2">
              <div className="text-[10px] tracking-wider uppercase text-text3 font-medium">
                Active Wellness A/B Experiments
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {engagementStats.ab_tests.map((test: any, idx: number) => (
                  <div key={idx} className="bg-bg3/40 border border-border/40 rounded-xl p-4 flex flex-col justify-between space-y-3">
                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-text">{test.test_name}</div>
                      <p className="text-[10.5px] text-text3 leading-relaxed italic">{test.conclusion}</p>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[9px] text-text3 uppercase font-medium">
                          <span>{test.group_a_label}</span>
                          <span className="text-accent">{test.group_a_metric}%</span>
                        </div>
                        <div className="h-1.5 bg-bg4 rounded-full overflow-hidden">
                          <div className="h-full bg-accent rounded-full" style={{ width: `${test.group_a_metric}%` }} />
                        </div>
                      </div>

                      <div className="space-y-1">
                        <div className="flex justify-between text-[9px] text-text3 uppercase font-medium">
                          <span>{test.group_b_label}</span>
                          <span className="text-teal">{test.group_b_metric}%</span>
                        </div>
                        <div className="h-1.5 bg-bg4 rounded-full overflow-hidden">
                          <div className="h-full bg-teal rounded-full" style={{ width: `${test.group_b_metric}%` }} />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Group by convo type */}
            {engagementStats.convo_type_engagement.length > 0 && (
              <div className="space-y-3 pt-2">
                <div className="text-[10px] tracking-wider uppercase text-text3 font-medium">
                  Engagement by Conversation Focus
                </div>
                <div className="space-y-2.5 max-h-[200px] overflow-y-auto pr-1">
                  {engagementStats.convo_type_engagement.map((item: any, idx: number) => (
                    <div key={idx} className="bg-bg3/30 border border-border/30 rounded-xl px-4 py-3 flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-medium text-text uppercase tracking-wider">{item.convo_type}</span>
                        <span className="text-[9px] bg-bg4 text-text3 px-2 py-0.5 rounded border border-border">
                          {item.total_convos} sessions
                        </span>
                      </div>
                      <div className="flex gap-6 text-right">
                        <div>
                          <div className="text-xs font-semibold text-accent">{item.avg_response_time}s</div>
                          <div className="text-[9px] text-text3 uppercase tracking-wider">Resp Speed</div>
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-teal">{item.return_rate_24h}%</div>
                          <div className="text-[9px] text-text3 uppercase tracking-wider">Return Rate</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Settings Section */}
      <section className="space-y-4">
        <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium flex items-center gap-1.5">
          <Settings size={16} /> Aria Settings
        </div>
        <div className="bg-bg2 border border-border rounded-[20px] p-6 space-y-4">
          <div className="space-y-1">
            <h3 className="text-sm font-medium text-text">Emergency Contact (Optional)</h3>
            <p className="text-xs text-text3 leading-relaxed">
              Register a contact (phone, email, or name) for peace of mind. ARIA is fully private, but if critical distress is detected, we will log a safety handover and alert this contact.
            </p>
          </div>
          <div className="flex gap-3 max-w-md">
            <input
              type="text"
              className="flex-1 bg-bg3 border border-border rounded-xl px-4 py-2 text-xs text-text placeholder-text3 focus:outline-none focus:border-accent"
              placeholder="e.g. Spouse, parent, or therapist (+1-555-0199)"
              value={emergencyContact}
              onChange={(e) => setEmergencyContact(e.target.value)}
            />
            <button
              onClick={handleSaveContact}
              disabled={savingContact}
              className="bg-accent text-white px-5 py-2.5 rounded-xl text-xs font-semibold hover:bg-accent/80 transition-all disabled:opacity-50"
            >
              {savingContact ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
