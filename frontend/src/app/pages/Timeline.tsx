import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '@/lib/auth';
import { ai as aiApi, TimelineEvent } from '@/lib/api';
import GuestGate from '@/app/components/GuestGate';
import {
  Loader2, Clock, Sun, Smile, BookOpen, Brain, Moon, Award,
  Sparkles, Search, X, ArrowLeft, ChevronDown, Calendar,
} from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────────────────

type EventType = 'morning' | 'mood' | 'journal' | 'discovery' | 'milestone' | 'achievement' | 'wind_down' | 'letter' | 'memory';

interface GroupedEvents {
  [year: string]: {
    [month: string]: TimelineEvent[];
  };
}

// ─── Constants ─────────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<EventType, { label: string; icon: React.ReactNode; color: string; border: string; bg: string }> = {
  morning:    { label: 'Morning Focus',  icon: <Sun size={14} />,      color: 'text-amber',   border: 'border-amber/30',   bg: 'bg-amber/8' },
  mood:       { label: 'Reflections',    icon: <Smile size={14} />,    color: 'text-teal',    border: 'border-teal/30',    bg: 'bg-teal/8' },
  journal:    { label: 'Journal',        icon: <BookOpen size={14} />, color: 'text-accent',  border: 'border-accent/30',  bg: 'bg-accent/8' },
  discovery:  { label: 'ARIA Discovery', icon: <Brain size={14} />,    color: 'text-cyan-400',border: 'border-cyan-400/30',bg: 'bg-cyan-400/8' },
  milestone:  { label: 'Milestone',      icon: <Award size={14} />,    color: 'text-yellow-400', border: 'border-yellow-400/30', bg: 'bg-yellow-400/8' },
  achievement:{ label: 'Achievement',    icon: <Award size={14} />,    color: 'text-amber-400', border: 'border-amber-400/30', bg: 'bg-amber-400/8' },
  wind_down:  { label: 'Wind Down',      icon: <Moon size={14} />,     color: 'text-indigo-400', border: 'border-indigo-400/30', bg: 'bg-indigo-400/8' },
  letter:     { label: 'Solstice Letter',icon: <Sparkles size={14} />, color: 'text-rose-400', border: 'border-rose-400/30', bg: 'bg-rose-400/8' },
  memory:     { label: 'Important Memory',icon: <Sparkles size={14} />, color: 'text-purple-400', border: 'border-purple-400/30', bg: 'bg-purple-400/8' },
};

const ALL_TYPES: EventType[] = ['morning', 'mood', 'journal', 'discovery', 'milestone', 'achievement', 'wind_down', 'letter', 'memory'];

const MONTH_NAMES = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
];

// ─── Helpers ───────────────────────────────────────────────────────────────────

function groupEvents(events: TimelineEvent[]): GroupedEvents {
  const grouped: GroupedEvents = {};
  for (const evt of events) {
    const date = new Date(evt.event_ts);
    const year = String(date.getFullYear());
    const month = String(date.getMonth()); // 0-indexed for MONTH_NAMES
    if (!grouped[year]) grouped[year] = {};
    if (!grouped[year][month]) grouped[year][month] = [];
    grouped[year][month].push(evt);
  }
  return grouped;
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function formatDay(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  } catch {
    return ts.slice(0, 10);
  }
}

// ─── EventCard ─────────────────────────────────────────────────────────────────

function EventCard({ evt }: { evt: TimelineEvent }) {
  const cfg = TYPE_CONFIG[evt.event_type as EventType] ?? TYPE_CONFIG.journal;
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`relative flex gap-4 group`}>
      {/* Timeline spine dot */}
      <div className="flex flex-col items-center">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${cfg.bg} border ${cfg.border} ${cfg.color} transition-all group-hover:scale-110`}>
          {cfg.icon}
        </div>
        <div className="w-px flex-1 bg-border/30 mt-1" />
      </div>

      {/* Card body */}
      <div className={`flex-1 mb-4 p-4 rounded-xl border ${cfg.border} ${cfg.bg} backdrop-blur-sm transition-all hover:shadow-lg hover:shadow-black/20`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className={`text-[11px] font-semibold uppercase tracking-wider ${cfg.color}`}>
                {cfg.label}
              </span>
              {evt.event_type === 'mood' && evt.mood_level != null && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${cfg.border} ${cfg.color} font-medium`}>
                  {evt.mood_level}/10
                </span>
              )}
              {evt.event_type === 'discovery' && evt.metadata?.confidence_score != null && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${cfg.border} ${cfg.color} font-medium`}>
                  {evt.metadata.confidence_score}% confidence
                </span>
              )}
            </div>

            {evt.title && (
              <p className="text-sm font-medium text-text leading-snug mb-1">
                {evt.title}
              </p>
            )}

            {evt.summary && (
              <p className={`text-xs text-text2 leading-relaxed ${evt.event_type === 'memory' ? 'whitespace-pre-wrap bg-white/5 border border-border/20 rounded-lg p-3 mt-1.5' : 'line-clamp-3'}`}>
                {evt.summary}
              </p>
            )}

            {evt.event_type === 'letter' && evt.metadata?.letter_content && (
              <div className="mt-3">
                {expanded ? (
                  <div className="space-y-2">
                    <div className="text-xs text-text leading-relaxed bg-white/5 border border-border/20 rounded-lg p-3 whitespace-pre-wrap font-sans">
                      {evt.metadata.letter_content}
                    </div>
                    <button
                      onClick={() => setExpanded(false)}
                      className="text-[11px] text-accent hover:underline font-medium cursor-pointer"
                    >
                      Show Less
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setExpanded(true)}
                    className="text-[11px] text-accent hover:underline font-medium cursor-pointer"
                  >
                    Read Solstice Letter →
                  </button>
                )}
              </div>
            )}

            {evt.emotion && (
              <div className="flex flex-wrap gap-1 mt-2">
                {evt.emotion.split(',').slice(0, 4).map((e, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 bg-white/5 border border-border/40 rounded-md text-text3">
                    {e.trim()}
                  </span>
                ))}
              </div>
            )}
          </div>

          <time className="text-[10px] text-text3 whitespace-nowrap flex-shrink-0 mt-0.5">
            {formatTime(evt.event_ts)}
          </time>
        </div>
      </div>
    </div>
  );
}

// ─── Timeline Page ─────────────────────────────────────────────────────────────

export default function Timeline() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // State
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [activeTypes, setActiveTypes] = useState<Set<EventType>>(new Set());

  // Grouping
  const [grouped, setGrouped] = useState<GroupedEvents>({});
  const [expandedYears, setExpandedYears] = useState<Set<string>>(new Set());

  // Refs
  const sentinelRef = useRef<HTMLDivElement>(null);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce search query
  useEffect(() => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      setDebouncedQ(searchQuery);
    }, 300);
    return () => { if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current); };
  }, [searchQuery]);

  // Fetch timeline (fresh load when filters change)
  const fetchTimeline = useCallback(async (p: number, append = false) => {
    if (!user) return;
    if (p === 1) setLoading(true);
    else setLoadingMore(true);

    try {
      const params: Parameters<typeof aiApi.getTimeline>[0] = {
        page: p,
        page_size: 30,
      };
      if (debouncedQ) params.q = debouncedQ;
      if (activeTypes.size > 0) params.types = [...activeTypes].join(',');

      const res = await aiApi.getTimeline(params);

      if (append) {
        setEvents(prev => {
          const updated = [...prev, ...res.events];
          setGrouped(groupEvents(updated));
          return updated;
        });
      } else {
        setEvents(res.events);
        setGrouped(groupEvents(res.events));
        // Auto-expand the most recent year
        if (res.events.length > 0) {
          const firstYear = String(new Date(res.events[0].event_ts).getFullYear());
          setExpandedYears(new Set([firstYear]));
        }
      }

      setHasMore(res.has_more);
      setTotal(res.total);
    } catch (err: any) {
      // If no events cached yet, trigger a rebuild first
      if (p === 1 && !append) {
        await triggerRebuild();
      } else {
        setError(err.message || 'Failed to load timeline.');
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [user, debouncedQ, activeTypes]);

  const triggerRebuild = async () => {
    setRebuilding(true);
    try {
      await aiApi.rebuildTimeline();
      // After rebuild, fetch page 1 again
      await fetchTimeline(1, false);
    } catch {
      setError('Could not load your timeline. Please try again.');
    } finally {
      setRebuilding(false);
    }
  };

  // Initial load and on filter change
  useEffect(() => {
    setPage(1);
    fetchTimeline(1, false);
  }, [debouncedQ, activeTypes]);

  // IntersectionObserver for infinite scroll
  useEffect(() => {
    if (!sentinelRef.current || !hasMore) return;
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && !loadingMore && hasMore) {
          const nextPage = page + 1;
          setPage(nextPage);
          fetchTimeline(nextPage, true);
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasMore, loadingMore, page, fetchTimeline]);

  const toggleType = (type: EventType) => {
    setActiveTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const clearFilters = () => {
    setSearchQuery('');
    setActiveTypes(new Set());
  };

  const toggleYear = (year: string) => {
    setExpandedYears(prev => {
      const next = new Set(prev);
      if (next.has(year)) next.delete(year);
      else next.add(year);
      return next;
    });
  };

  const hasActiveFilters = searchQuery || activeTypes.size > 0;

  if (!user) {
    return (
      <GuestGate
        title="Personal Growth Timeline"
        description="Sign in to explore your complete personal growth journey — every mood, journal, and ARIA discovery in one place."
        icon={<Clock className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  return (
    <div className="max-w-[820px] mx-auto px-4 sm:px-6 py-8 space-y-8 animate-fadeIn">

      {/* Header */}
      <div className="space-y-1">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-xs text-text3 hover:text-text transition-colors mb-3 cursor-pointer"
        >
          <ArrowLeft size={13} /> Back
        </button>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="font-[family-name:var(--font-serif)] text-2xl sm:text-3xl font-light text-text italic">
              Your Growth Timeline
            </h1>
            <p className="text-xs text-text3 mt-1">
              {total > 0 ? (
                <>Every step of your journey — {total.toLocaleString()} moments recorded</>
              ) : (
                <>Your complete personal history in one place</>
              )}
            </p>
          </div>
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center">
            <Clock size={18} className="text-accent" />
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="space-y-3">
        {/* Search input */}
        <div className="relative">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text3 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search your moments…"
            className="w-full bg-bg2/60 border border-border rounded-xl pl-9 pr-10 py-2.5 text-sm text-text placeholder-text3 focus:outline-none focus:border-accent/60 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text3 hover:text-text transition-colors cursor-pointer"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Type filter pills */}
        <div className="flex flex-wrap gap-2">
          {ALL_TYPES.map(type => {
            const cfg = TYPE_CONFIG[type];
            const active = activeTypes.has(type);
            return (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium border transition-all cursor-pointer ${
                  active
                    ? `${cfg.bg} ${cfg.border} ${cfg.color}`
                    : 'bg-bg2/40 border-border text-text3 hover:border-border2 hover:text-text'
                }`}
              >
                {cfg.icon}
                {cfg.label}
              </button>
            );
          })}

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 px-3 py-1.5 rounded-full text-[11px] font-medium border border-rose/30 bg-rose/8 text-rose hover:bg-rose/15 transition-all cursor-pointer"
            >
              <X size={11} /> Clear
            </button>
          )}
        </div>
      </div>

      {/* Timeline content */}
      {(loading || rebuilding) ? (
        <div className="min-h-[40vh] flex flex-col items-center justify-center space-y-4">
          <Loader2 className="w-8 h-8 text-accent animate-spin" />
          <p className="text-sm text-text3">
            {rebuilding ? 'Assembling your growth timeline…' : 'Loading your moments…'}
          </p>
        </div>
      ) : error ? (
        <div className="text-center py-16 space-y-3">
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={() => { setError(''); fetchTimeline(1, false); }}
            className="text-xs text-accent hover:underline cursor-pointer"
          >
            Try again
          </button>
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-20 space-y-3">
          <div className="w-14 h-14 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center mx-auto">
            <Calendar size={22} className="text-accent" />
          </div>
          <p className="text-sm text-text2 font-light">
            {hasActiveFilters ? 'No moments match your search.' : 'Your timeline will populate as you use MindCradle.'}
          </p>
          {hasActiveFilters && (
            <button onClick={clearFilters} className="text-xs text-accent hover:underline cursor-pointer">
              Clear filters
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {Object.keys(grouped)
            .sort((a, b) => Number(b) - Number(a))
            .map(year => {
              const isExpanded = expandedYears.has(year);
              const yearMonths = grouped[year];
              const yearCount = Object.values(yearMonths).reduce((sum, evts) => sum + evts.length, 0);

              return (
                <div key={year} className="space-y-4">
                  {/* Year header */}
                  <button
                    onClick={() => toggleYear(year)}
                    className="w-full flex items-center gap-3 group cursor-pointer"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <div className="h-px flex-1 bg-border/50" />
                      <span className="font-[family-name:var(--font-serif)] text-2xl font-light text-text/60 group-hover:text-text transition-colors select-none italic">
                        {year}
                      </span>
                      <span className="text-[10px] text-text3 font-medium px-2 py-0.5 bg-bg2/60 border border-border rounded-full">
                        {yearCount} moments
                      </span>
                      <div className="h-px flex-1 bg-border/50" />
                    </div>
                    <ChevronDown
                      size={16}
                      className={`text-text3 transition-transform flex-shrink-0 ${isExpanded ? '' : '-rotate-90'}`}
                    />
                  </button>

                  {isExpanded && (
                    <div className="space-y-8 pl-2">
                      {Object.keys(yearMonths)
                        .sort((a, b) => Number(b) - Number(a))
                        .map(monthIdx => {
                          const monthEvents = yearMonths[monthIdx];
                          return (
                            <div key={monthIdx} className="space-y-2">
                              {/* Month label */}
                              <div className="flex items-center gap-2 mb-3">
                                <span className="text-[11px] text-text3 font-semibold uppercase tracking-widest">
                                  {MONTH_NAMES[Number(monthIdx)]}
                                </span>
                                <span className="text-[10px] text-text3/60">
                                  · {monthEvents.length} events
                                </span>
                              </div>

                              {/* Day-grouped events */}
                              {(() => {
                                // Group by day within month
                                const byDay: Record<string, TimelineEvent[]> = {};
                                for (const e of monthEvents) {
                                  const day = e.event_date;
                                  if (!byDay[day]) byDay[day] = [];
                                  byDay[day].push(e);
                                }
                                return Object.keys(byDay)
                                  .sort((a, b) => (a > b ? -1 : 1))
                                  .map(day => (
                                    <div key={day} className="space-y-1 mb-4">
                                      <p className="text-[10px] text-text3 font-medium mb-2 ml-12">
                                        {formatDay(byDay[day][0].event_ts)}
                                      </p>
                                      {byDay[day].map(evt => (
                                        <EventCard key={evt.id} evt={evt} />
                                      ))}
                                    </div>
                                  ));
                              })()}
                            </div>
                          );
                        })}
                    </div>
                  )}
                </div>
              );
            })}

          {/* Infinite scroll sentinel */}
          <div ref={sentinelRef} className="h-8 flex items-center justify-center">
            {loadingMore && (
              <div className="flex items-center gap-2 text-xs text-text3">
                <Loader2 size={14} className="animate-spin" />
                Loading more moments…
              </div>
            )}
          </div>

          {!hasMore && events.length > 0 && (
            <div className="text-center py-6">
              <p className="text-xs text-text3 italic">
                ✦ You've reached the beginning of your story
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
