/**
 * SemanticSearch — MindCradle's cross-history search overlay.
 *
 * Usage:
 *   <SemanticSearch open={open} onClose={() => setOpen(false)} />          // overlay mode
 *   <SemanticSearch embedded onClose={() => {}} open />                     // inline mode (Timeline page)
 *
 * Features:
 *   - ⌘K / Ctrl+K to open from anywhere (when registered in Layout)
 *   - Dynamic suggestion pills from /ai/search/suggestions
 *   - Debounced search (400 ms) → hybrid semantic + keyword results
 *   - Type filter pills (Morning / Mood / Journal / Discovery / Milestone)
 *   - Date range pickers
 *   - Keyboard navigation: ↑↓ arrows, Enter to navigate, Escape to close
 *   - Session-level result cache (3 entries) to avoid re-fetching same query
 */

import { useEffect, useRef, useState, useCallback, KeyboardEvent } from 'react';
import { useNavigate } from 'react-router';
import { ai as aiApi, SearchResultItem } from '@/lib/api';
import {
  Search, X, Loader2, Sun, Smile, BookOpen, Brain,
  Moon, Award, Sparkles, ChevronRight, Clock,
} from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  open: boolean;
  onClose: () => void;
  embedded?: boolean;   // true = render inline (no overlay backdrop)
}

type EventType = 'morning' | 'mood' | 'journal' | 'discovery' | 'milestone' | 'wind_down';

// ─── Constants ─────────────────────────────────────────────────────────────────

const TYPE_CFG: Record<string, { label: string; icon: React.ReactNode; color: string; border: string; bg: string }> = {
  morning:   { label: 'Morning',   icon: <Sun size={13} />,      color: 'text-amber-400',    border: 'border-amber-400/30',    bg: 'bg-amber-400/8' },
  mood:      { label: 'Mood',      icon: <Smile size={13} />,    color: 'text-teal-400',     border: 'border-teal-400/30',     bg: 'bg-teal-400/8' },
  journal:   { label: 'Journal',   icon: <BookOpen size={13} />, color: 'text-accent',       border: 'border-accent/30',       bg: 'bg-accent/8' },
  discovery: { label: 'Discovery', icon: <Brain size={13} />,    color: 'text-cyan-400',     border: 'border-cyan-400/30',     bg: 'bg-cyan-400/8' },
  milestone: { label: 'Milestone', icon: <Award size={13} />,    color: 'text-yellow-400',   border: 'border-yellow-400/30',   bg: 'bg-yellow-400/8' },
  wind_down: { label: 'Wind Down', icon: <Moon size={13} />,     color: 'text-indigo-400',   border: 'border-indigo-400/30',   bg: 'bg-indigo-400/8' },
  letter:    { label: 'Letter',    icon: <Sparkles size={13} />, color: 'text-rose-400',     border: 'border-rose-400/30',     bg: 'bg-rose-400/8' },
};

const FILTER_TYPES: EventType[] = ['morning', 'mood', 'journal', 'discovery', 'milestone', 'wind_down'];

// Simple session-level result cache
const _cache = new Map<string, SearchResultItem[]>();
function _cacheKey(q: string, types: string, start: string, end: string) {
  return `${q}|${types}|${start}|${end}`;
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

function formatRelativeDate(ts: string): string {
  try {
    const d = new Date(ts);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000);
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    if (diffDays < 365) return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return ts.slice(0, 10);
  }
}

function truncateSummary(text: string | undefined, max = 120): string {
  if (!text) return '';
  return text.length > max ? text.slice(0, max) + '…' : text;
}

// ─── ResultCard ────────────────────────────────────────────────────────────────

function ResultCard({
  result,
  isActive,
  onClick,
  onMouseEnter,
}: {
  result: SearchResultItem;
  isActive: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
}) {
  const cfg = TYPE_CFG[result.event_type] ?? TYPE_CFG.journal;

  return (
    <button
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      className={`w-full text-left px-4 py-3 rounded-xl border transition-all cursor-pointer group ${
        isActive
          ? `${cfg.bg} ${cfg.border} shadow-sm`
          : 'border-transparent hover:border-border hover:bg-bg2/40'
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${cfg.bg} border ${cfg.border} ${cfg.color}`}>
          {cfg.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`text-[10px] font-semibold uppercase tracking-wider ${cfg.color}`}>
              {cfg.label}
            </span>
            {result.mood_level != null && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${cfg.border} ${cfg.color}`}>
                {result.mood_level}/10
              </span>
            )}
            {result.similarity != null && result.similarity > 0.7 && (
              <span className="text-[9px] text-text3 opacity-60">● high match</span>
            )}
          </div>

          {result.title && (
            <p className="text-sm font-medium text-text leading-snug truncate">
              {result.title}
            </p>
          )}

          {result.summary && (
            <p className="text-xs text-text2 mt-0.5 leading-relaxed">
              {truncateSummary(result.summary)}
            </p>
          )}

          {result.emotion && (
            <div className="flex gap-1 mt-1.5 flex-wrap">
              {result.emotion.split(',').slice(0, 3).map((e, i) => (
                <span key={i} className="text-[10px] text-text3 bg-white/5 border border-border/40 rounded-md px-1.5 py-0.5">
                  {e.trim()}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Date + arrow */}
        <div className="flex-shrink-0 flex flex-col items-end gap-1 ml-2">
          <span className="text-[10px] text-text3 whitespace-nowrap flex items-center gap-1">
            <Clock size={9} />
            {formatRelativeDate(result.event_ts)}
          </span>
          <ChevronRight size={12} className={`transition-all ${isActive ? `${cfg.color}` : 'text-text3 opacity-0 group-hover:opacity-100'}`} />
        </div>
      </div>
    </button>
  );
}

// ─── SkeletonCard ──────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="px-4 py-3 rounded-xl border border-border/30 animate-pulse">
      <div className="flex items-start gap-3">
        <div className="w-7 h-7 rounded-lg bg-bg3/50 flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-2.5 bg-bg3/50 rounded w-20" />
          <div className="h-3 bg-bg3/40 rounded w-3/4" />
          <div className="h-2.5 bg-bg3/30 rounded w-1/2" />
        </div>
      </div>
    </div>
  );
}

// ─── SemanticSearch ────────────────────────────────────────────────────────────

export default function SemanticSearch({ open, onClose, embedded = false }: Props) {
  const navigate = useNavigate();

  // Input / query state
  const [query, setQuery] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Results state
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchMode, setSearchMode] = useState<string>('');
  const [hasEmbeddings, setHasEmbeddings] = useState(true);
  const [totalFound, setTotalFound] = useState(0);

  // Suggestions
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Filters
  const [activeTypes, setActiveTypes] = useState<Set<EventType>>(new Set());
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Keyboard navigation
  const [activeIndex, setActiveIndex] = useState(-1);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // ── Focus input on open ──────────────────────────────────────────────────
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
      setResults([]);
      setActiveIndex(-1);
    }
  }, [open]);

  // ── Load suggestions once on mount ──────────────────────────────────────
  useEffect(() => {
    aiApi.getSearchSuggestions()
      .then(res => setSuggestions(res.suggestions || []))
      .catch(() => {});
  }, []);

  // ── Debounce query ────────────────────────────────────────────────────────
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedQ(query.trim()), 400);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query]);

  // ── Fire search when debouncedQ / filters change ──────────────────────────
  const doSearch = useCallback(async () => {
    const q = debouncedQ;
    if (!q) {
      setResults([]);
      setTotalFound(0);
      return;
    }

    const cacheKey = _cacheKey(q, [...activeTypes].join(','), startDate, endDate);
    if (_cache.has(cacheKey)) {
      const cached = _cache.get(cacheKey)!;
      setResults(cached);
      setTotalFound(cached.length);
      return;
    }

    setLoading(true);
    setActiveIndex(-1);
    try {
      const res = await aiApi.semanticSearch({
        q,
        types: activeTypes.size > 0 ? [...activeTypes].join(',') : undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        limit: 15,
      });

      setResults(res.results);
      setTotalFound(res.total);
      setSearchMode(res.search_mode);
      setHasEmbeddings(res.has_embeddings);

      // Cache — keep only last 5 entries
      if (_cache.size >= 5) {
        const firstKey = _cache.keys().next().value;
        if (firstKey !== undefined) _cache.delete(firstKey);
      }
      _cache.set(cacheKey, res.results);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [debouncedQ, activeTypes, startDate, endDate]);

  useEffect(() => { doSearch(); }, [doSearch]);

  // ── Keyboard navigation ────────────────────────────────────────────────────
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }
    if (!results.length) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      handleResultClick(results[activeIndex]);
    }
  };

  // ── Scroll active item into view ───────────────────────────────────────────
  useEffect(() => {
    if (activeIndex < 0 || !listRef.current) return;
    const children = listRef.current.querySelectorAll('[data-result-item]');
    const el = children[activeIndex] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  // ── Navigate to the relevant page when a result is clicked ─────────────────
  const handleResultClick = (result: SearchResultItem) => {
    onClose();
    switch (result.event_type) {
      case 'mood':      navigate('/mood'); break;
      case 'journal':   navigate('/journal'); break;
      case 'morning':   navigate('/morning'); break;
      case 'wind_down': navigate('/wind-down'); break;
      case 'discovery': navigate('/discoveries'); break;
      default:          navigate('/timeline'); break;
    }
  };

  const toggleType = (type: EventType) => {
    setActiveTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const clearAll = () => {
    setQuery('');
    setActiveTypes(new Set());
    setStartDate('');
    setEndDate('');
    inputRef.current?.focus();
  };

  const hasFilters = activeTypes.size > 0 || startDate || endDate;

  if (!open) return null;

  // ── Render ──────────────────────────────────────────────────────────────────

  const containerCls = embedded
    ? 'w-full'
    : 'fixed inset-0 z-50 flex items-start justify-center pt-[10vh] px-4';

  const backdropCls = embedded
    ? ''
    : 'fixed inset-0 bg-bg/80 backdrop-blur-md z-40';

  const panelCls = embedded
    ? 'w-full'
    : 'relative z-50 w-full max-w-[640px] max-h-[82vh] flex flex-col bg-bg border border-border/70 rounded-2xl shadow-2xl shadow-black/40 overflow-hidden animate-fadeIn';

  return (
    <>
      {/* Backdrop (overlay mode only) */}
      {!embedded && (
        <div className={backdropCls} onClick={onClose} aria-hidden="true" />
      )}

      {/* Panel */}
      <div className={containerCls}>
        <div className={panelCls}>

          {/* ── Search bar ─────────────────────────────────────────────────── */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-border/50 flex-shrink-0">
            <Search size={16} className="text-text3 flex-shrink-0" />
            <input
              ref={inputRef}
              id="semantic-search-input"
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search your history…  e.g. When was I happiest?"
              className="flex-1 bg-transparent text-sm text-text placeholder-text3 focus:outline-none"
              autoComplete="off"
              spellCheck={false}
            />
            {loading && <Loader2 size={14} className="text-text3 animate-spin flex-shrink-0" />}
            {query && !loading && (
              <button
                onClick={clearAll}
                className="text-text3 hover:text-text transition-colors flex-shrink-0 cursor-pointer"
              >
                <X size={14} />
              </button>
            )}
            {!embedded && (
              <button
                onClick={onClose}
                className="text-text3 hover:text-text transition-colors flex-shrink-0 text-xs border border-border rounded-md px-1.5 py-0.5 cursor-pointer"
              >
                esc
              </button>
            )}
          </div>

          {/* ── Filter bar ─────────────────────────────────────────────────── */}
          <div className="flex items-center gap-2 px-4 py-2 border-b border-border/30 flex-shrink-0 flex-wrap">
            {FILTER_TYPES.map(type => {
              const cfg = TYPE_CFG[type];
              const active = activeTypes.has(type);
              return (
                <button
                  key={type}
                  onClick={() => toggleType(type)}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold border transition-all cursor-pointer ${
                    active
                      ? `${cfg.bg} ${cfg.border} ${cfg.color}`
                      : 'bg-transparent border-border text-text3 hover:border-border2 hover:text-text'
                  }`}
                >
                  {cfg.icon}
                  {cfg.label}
                </button>
              );
            })}

            <button
              onClick={() => setShowFilters(v => !v)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold border transition-all cursor-pointer ${
                showFilters || (startDate || endDate)
                  ? 'border-accent/40 bg-accent/8 text-accent'
                  : 'border-border text-text3 hover:text-text'
              }`}
            >
              Date range
            </button>

            {hasFilters && (
              <button
                onClick={() => { setActiveTypes(new Set()); setStartDate(''); setEndDate(''); }}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold border border-rose-400/30 bg-rose-400/8 text-rose-400 hover:bg-rose-400/15 transition-all cursor-pointer"
              >
                <X size={10} /> Clear
              </button>
            )}
          </div>

          {/* Date pickers */}
          {showFilters && (
            <div className="flex items-center gap-3 px-4 py-2 border-b border-border/30 flex-shrink-0">
              <span className="text-[10px] text-text3 font-medium">From</span>
              <input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className="bg-bg2/60 border border-border rounded-lg px-2 py-1 text-xs text-text focus:outline-none focus:border-accent/60 transition-all"
              />
              <span className="text-[10px] text-text3 font-medium">To</span>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="bg-bg2/60 border border-border rounded-lg px-2 py-1 text-xs text-text focus:outline-none focus:border-accent/60 transition-all"
              />
            </div>
          )}

          {/* ── Results / Suggestions area ──────────────────────────────────── */}
          <div className="flex-1 overflow-y-auto min-h-0 px-3 py-3 space-y-1" ref={listRef}>

            {/* Loading skeletons */}
            {loading && (
              <div className="space-y-2">
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </div>
            )}

            {/* Empty query — show suggestions */}
            {!loading && !query && suggestions.length > 0 && (
              <div className="py-2 space-y-1">
                <p className="text-[10px] text-text3 uppercase tracking-wider font-semibold px-1 mb-2">
                  Try asking…
                </p>
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => { setQuery(s); inputRef.current?.focus(); }}
                    className="w-full text-left flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-bg2/60 transition-all group cursor-pointer"
                  >
                    <Sparkles size={12} className="text-accent flex-shrink-0" />
                    <span className="text-sm text-text2 group-hover:text-text transition-colors">{s}</span>
                  </button>
                ))}
              </div>
            )}

            {/* No results */}
            {!loading && debouncedQ && results.length === 0 && (
              <div className="py-10 text-center space-y-3">
                <div className="w-10 h-10 rounded-full bg-bg2/60 border border-border flex items-center justify-center mx-auto">
                  <Search size={16} className="text-text3" />
                </div>
                <p className="text-sm text-text2">No results for <em>"{debouncedQ}"</em></p>
                {!hasEmbeddings && (
                  <p className="text-xs text-text3 max-w-xs mx-auto">
                    Build your Timeline first to enable full semantic search.
                  </p>
                )}
                <p className="text-xs text-text3">Try different keywords or remove filters</p>
              </div>
            )}

            {/* Results */}
            {!loading && results.length > 0 && (
              <>
                <div className="flex items-center justify-between px-1 mb-2">
                  <p className="text-[10px] text-text3 uppercase tracking-wider font-semibold">
                    {totalFound} result{totalFound !== 1 ? 's' : ''}{' '}
                    {searchMode === 'hybrid' && '· semantic + keyword'}
                    {searchMode === 'semantic' && '· semantic'}
                    {searchMode === 'keyword' && '· keyword'}
                  </p>
                </div>
                {results.map((result, i) => (
                  <div key={result.id} data-result-item="">
                    <ResultCard
                      result={result}
                      isActive={activeIndex === i}
                      onClick={() => handleResultClick(result)}
                      onMouseEnter={() => setActiveIndex(i)}
                    />
                  </div>
                ))}
              </>
            )}
          </div>

          {/* ── Footer ─────────────────────────────────────────────────────── */}
          {!embedded && (
            <div className="flex items-center justify-between px-4 py-2 border-t border-border/30 flex-shrink-0">
              <div className="flex items-center gap-3 text-[10px] text-text3">
                <span>↑↓ navigate</span>
                <span>Enter to open</span>
                <span>Esc to close</span>
              </div>
              <span className="text-[10px] text-text3 italic">powered by ARIA</span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
