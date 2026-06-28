import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useAuth } from '@/lib/auth';
import { mood as moodApi, resources as resourcesApi, ai as aiApi, rituals as ritualsApi, journal as journalApi } from '@/lib/api';
import type { ResourceItem } from '@/lib/api';
import { Lock, Award, Moon, Wind, PenTool, CheckCircle2, TrendingUp, Brain, Star, Flame, BookOpen, Target } from 'lucide-react';
import GuestGate from '@/app/components/GuestGate';
import { WellnessInsightCard } from '@/app/components/WellnessInsightCard';

const SHORT_DAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export default function Dashboard() {
  const { user, setAuthModalOpen } = useAuth();
  const navigate = useNavigate();

  // Sleep Logger state
  const [sleepStartTime, setSleepStartTime] = useState<number | null>(null);
  const [currentTime, setCurrentTime] = useState<number>(Date.now());

  // Load saved sleep start time from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('mc_sleep_start_time');
    if (saved) {
      setSleepStartTime(parseInt(saved, 10));
    }
  }, []);

  // Update current time every second if the user is sleeping
  useEffect(() => {
    if (!sleepStartTime) return;
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, [sleepStartTime]);

  const handleGoingToSleep = () => {
    const now = Date.now();
    setSleepStartTime(now);
    setCurrentTime(now);
    localStorage.setItem('mc_sleep_start_time', now.toString());
  };

  const handleWokeUp = () => {
    if (!sleepStartTime) return;
    const now = Date.now();
    const elapsedMs = now - sleepStartTime;

    const totalSecs = Math.floor(elapsedMs / 1000);
    const totalMins = Math.floor(totalSecs / 60);
    const hours = Math.floor(totalMins / 60);
    const minutes = totalMins % 60;

    localStorage.removeItem('mc_sleep_start_time');
    setSleepStartTime(null);

    let durationStr = '';
    if (hours === 0 && minutes === 0) {
      durationStr = 'less than a minute (micro-sleep/quick logger test)';
    } else {
      durationStr = `${hours} hours and ${minutes} minutes`;
    }

    const sleepPrompt = `I logged my sleep duration: I slept for ${durationStr}. Please analyze my sleep duration. Tell me if I slept more or less than the recommended 7-9 hours, suggest guidelines/tips for my wellness, talk about random naps if applicable, and basically use this sleeping info to guide me.`;

    localStorage.setItem('mc_aria_context', sleepPrompt);
    navigate('/aria');
  };

  const formatElapsed = (ms: number) => {
    if (ms < 0) return '0s';
    const totalSecs = Math.floor(ms / 1000);
    const secs = totalSecs % 60;
    const totalMins = Math.floor(totalSecs / 60);
    const mins = totalMins % 60;
    const hrs = Math.floor(totalMins / 60);

    if (hrs > 0) {
      return `${hrs}h ${mins}m`;
    }
    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  };

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

  // Wellness stats
  const [ritualsCompleted, setRitualsCompleted] = useState<number | null>(null);
  const [insightPatternsCount, setInsightPatternsCount] = useState<number | null>(null);
  const [journalCount, setJournalCount] = useState<number | null>(null);

  useEffect(() => {
    if (!user) return;
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
      'Give me a brief single-sentence daily insight or gentle encouragement based on my recent well-being patterns. Keep it simple, warm, and completely free of clinical jargon. Keep it under 25 words.'
    ).then((res) => {
      setAriaInsight(res.reply);
    }).catch(() => {
      setAriaInsight('Your mood is trending up this week. Focus on taking a few deep breaths and taking time for yourself today.');
    }).finally(() => {
      setAriaLoading(false);
    });

    // Fetch rituals completed stats
    ritualsApi.getStats().then((res) => {
      setRitualsCompleted(res.completed);
    }).catch(() => {});

    // Fetch ARIA memory insights
    aiApi.getMemoryInsights().then((res) => {
      const oneWeekAgo = new Date();
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
      const newPatterns = res.filter(insight => {
        const createdDate = new Date(insight.created);
        return createdDate >= oneWeekAgo;
      }).length;
      setInsightPatternsCount(newPatterns);
    }).catch(() => {});

    // Fetch journal entries count
    journalApi.list().then((res) => {
      setJournalCount(res.items.length);
    }).catch(() => {});
  }, [user]);

  const getMoodTrend = () => {
    if (moodItems.length < 2) {
      return { text: 'Getting Better', arrow: '↗', color: 'text-teal bg-teal-dim border-teal/20' };
    }
    
    const sorted = [...moodItems].sort((a, b) => new Date(a.created).getTime() - new Date(b.created).getTime());
    const mid = Math.floor(sorted.length / 2);
    const firstHalf = sorted.slice(0, mid);
    const secondHalf = sorted.slice(mid);
    
    const avgFirst = firstHalf.reduce((sum, item) => sum + item.level, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((sum, item) => sum + item.level, 0) / secondHalf.length;
    
    if (avgSecond > avgFirst) {
      return { text: 'Getting Better', arrow: '↗', color: 'text-teal bg-teal-dim border-teal/20' };
    } else if (avgSecond < avgFirst) {
      return { text: 'Feeling Heavy', arrow: '↘', color: 'text-rose bg-rose-dim border-rose/20' };
    } else {
      return { text: 'Stable Calm', arrow: '→', color: 'text-amber bg-amber-dim border-amber/20' };
    }
  };

  if (!user) {
    return (
      <div className="space-y-8 animate-fadeIn">
        {/* Welcome & Discovery Hero Card */}
        <section className="animate-fadeIn">
          <div className="bg-bg2 border border-border rounded-[20px] p-6 relative overflow-hidden flex flex-col lg:flex-row lg:items-center justify-between gap-8">
            {/* Ambient Glow */}
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(139,124,248,0.1),transparent_60%)] pointer-events-none" />
            
            <div className="relative z-10 flex-1 space-y-4 text-left">
              <h1 className="font-[family-name:var(--font-serif)] text-2xl sm:text-3xl font-light text-text leading-tight">
                What will you discover today?
              </h1>
              <p className="text-sm text-text3 leading-relaxed max-w-2xl">
                Your <span className="text-rose font-medium">mood</span> tells a story. Your <span className="text-amber font-medium">rituals</span> create patterns. Your <span className="text-teal font-medium">journal</span> holds wisdom. <span className="text-text font-semibold">ARIA</span> connects the dots.
              </p>
              <div>
                <button
                  type="button"
                  onClick={() => setAuthModalOpen(true)}
                  className="inline-flex items-center justify-center px-6 py-3 bg-accent hover:opacity-90 rounded-full text-xs font-semibold tracking-wider transition-all cursor-pointer"
                >
                  Start here →
                </button>
              </div>

              {/* Testimonial Box */}
              <div className="pt-4 border-t border-border flex flex-col sm:flex-row sm:items-center gap-4 text-[11.5px] text-text3">
                <div className="flex items-center gap-2">
                  <span className="flex h-2 w-2 rounded-full bg-green shadow-[0_0_8px_var(--green)] animate-pulse" />
                  <span className="font-semibold text-text2">12,547</span> people found calm today
                </div>
                <div className="hidden sm:block w-1.5 h-1.5 rounded-full bg-border" />
                <div className="italic">
                  "This app saved my mental health" <span className="text-text2 not-italic font-medium">— Sarah, 23</span>
                </div>
              </div>
            </div>

            {/* Right Stack of Cards */}
            <div className="flex flex-col sm:flex-row lg:flex-col gap-4 flex-shrink-0 w-full lg:w-auto">
              {/* This Week's Wellness Card */}
              <div className="relative z-10 w-full sm:w-[320px] bg-bg3 border border-border2 rounded-[16px] p-5 backdrop-blur-md shadow-2xl space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="font-[family-name:var(--font-serif)] text-[15px] font-light text-text">
                    This Week's Wellness
                  </span>
                  <span className="w-2 h-2 rounded-full bg-accent animate-pulse shadow-[0_0_8px_var(--accent)]" />
                </div>

                <div className="space-y-3.5 text-left">
                  {/* Rituals Row */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-green-dim flex items-center justify-center text-green shadow-[0_0_8px_var(--green-dim)]">
                          <CheckCircle2 className="w-4 h-4" />
                        </div>
                        <span className="text-xs text-text2 font-medium">Rituals Completed</span>
                      </div>
                      <span className="text-xs font-semibold text-green bg-green-dim border border-green/20 px-2 py-0.5 rounded-full">
                        5/7
                      </span>
                    </div>
                    <div className="w-full bg-border h-1 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-green to-teal rounded-full" 
                        style={{ width: '71.4%' }} 
                      />
                    </div>
                  </div>

                  {/* Mood Trend Row */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-teal-dim flex items-center justify-center text-teal shadow-[0_0_8px_var(--teal-dim)]">
                        <TrendingUp className="w-4 h-4" />
                      </div>
                      <span className="text-xs text-text2 font-medium">Mood Trend</span>
                    </div>
                    <span className="text-xs font-semibold text-teal bg-teal-dim border border-teal/20 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                      ↗ Getting Better
                    </span>
                  </div>

                  {/* ARIA Insights Row */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-rose-dim flex items-center justify-center text-rose shadow-[0_0_8px_var(--rose-dim)]">
                        <Brain className="w-4 h-4" />
                      </div>
                      <span className="text-xs text-text2 font-medium">ARIA Insights</span>
                    </div>
                    <span className="text-xs font-semibold text-rose bg-rose-dim border border-rose/20 px-2.5 py-0.5 rounded-full">
                      3 New Patterns
                    </span>
                  </div>
                </div>
              </div>

              {/* Your Achievements Card */}
              <div className="relative z-10 w-full sm:w-[320px] bg-bg3 border border-border2 rounded-[16px] p-5 backdrop-blur-md shadow-2xl space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <span className="font-[family-name:var(--font-serif)] text-[15px] font-light text-text flex items-center gap-2">
                    🏆 Your Achievements
                  </span>
                  <span className="text-[10px] text-text3 uppercase tracking-wider">
                    2 / 4 Unlocked
                  </span>
                </div>

                <div className="space-y-3 text-left">
                  {/* First Check-in */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-amber-dim flex items-center justify-center text-amber shadow-[0_0_8px_var(--amber-dim)]">
                        <Star className="w-4 h-4" fill="currentColor" />
                      </div>
                      <span className="text-xs text-text2 font-medium">First Check-in</span>
                    </div>
                    <span className="text-[10px] font-semibold text-green bg-green-dim border border-green/20 px-2 py-0.5 rounded-full">
                      Unlocked
                    </span>
                  </div>

                  {/* 7-Day Streak */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-rose-dim flex items-center justify-center text-rose shadow-[0_0_8px_var(--rose-dim)]">
                        <Flame className="w-4 h-4" fill="currentColor" />
                      </div>
                      <span className="text-xs text-text2 font-medium">7-Day Streak</span>
                    </div>
                    <span className="text-[10px] font-semibold text-text3 bg-bg4 border border-border px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Lock className="w-2.5 h-2.5" /> Locked
                    </span>
                  </div>

                  {/* Journal Enthusiast */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-teal-dim flex items-center justify-center text-teal shadow-[0_0_8px_var(--teal-dim)]">
                        <BookOpen className="w-4 h-4" />
                      </div>
                      <span className="text-xs text-text2 font-medium">Journal Enthusiast</span>
                    </div>
                    <span className="text-[10px] font-semibold text-green bg-green-dim border border-green/20 px-2 py-0.5 rounded-full">
                      Unlocked
                    </span>
                  </div>

                  {/* Ritual Master */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-accent-glow flex items-center justify-center text-text shadow-[0_0_8px_var(--accent-glow)]">
                        <Target className="w-4 h-4" />
                      </div>
                      <span className="text-xs text-text2 font-medium">Ritual Master</span>
                    </div>
                    <span className="text-[10px] font-semibold text-text3 bg-bg4 border border-border px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Lock className="w-2.5 h-2.5" /> Locked
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <WellnessInsightCard />

        <GuestGate
          title="Your Wellness Dashboard"
          description="Create a secure account or sign in to track your rituals, monitor your calm index, and see AI-guided wellness recommendations."
          icon={<Lock size={28} />}
        />
      </div>
    );
  }

  const dashDots = (226 * calmScore) / 100;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Welcome & Discovery Hero Card */}
      <section className="animate-fadeIn">
        <div className="bg-bg2 border border-border rounded-[20px] p-6 relative overflow-hidden flex flex-col lg:flex-row lg:items-center justify-between gap-8">
          {/* Ambient Glow */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(139,124,248,0.1),transparent_60%)] pointer-events-none" />
          
          <div className="relative z-10 flex-1 space-y-4 text-left">
            <h1 className="font-[family-name:var(--font-serif)] text-2xl sm:text-3xl font-light text-text leading-tight">
              What will you discover today?
            </h1>
            <p className="text-sm text-text3 leading-relaxed max-w-2xl">
              Your <span className="text-rose font-medium">mood</span> tells a story. Your <span className="text-amber font-medium">rituals</span> create patterns. Your <span className="text-teal font-medium">journal</span> holds wisdom. <span className="text-text font-semibold">ARIA</span> connects the dots.
            </p>
            <div>
              <Link
                to="/mood"
                className="inline-flex items-center justify-center px-6 py-3 bg-accent hover:opacity-90 rounded-full text-xs font-semibold tracking-wider transition-all"
              >
                Start here →
              </Link>
            </div>

            {/* Testimonial Box */}
            <div className="pt-4 border-t border-border flex flex-col sm:flex-row sm:items-center gap-4 text-[11.5px] text-text3">
              <div className="flex items-center gap-2">
                <span className="flex h-2 w-2 rounded-full bg-green shadow-[0_0_8px_var(--green)] animate-pulse" />
                <span className="font-semibold text-text2">12,547</span> people found calm today
              </div>
              <div className="hidden sm:block w-1.5 h-1.5 rounded-full bg-border" />
              <div className="italic">
                "This app saved my mental health" <span className="text-text2 not-italic font-medium">— Sarah, 23</span>
              </div>
            </div>
          </div>

          {/* Right Stack of Cards */}
          {(() => {
            const hasCheckIn = moodItems.length >= 1;
            const hasStreak = streak >= 7;
            const hasJournal = journalCount !== null ? journalCount >= 3 : true; // Fallback to true if not loaded
            const hasRitualMaster = ritualsCompleted !== null ? ritualsCompleted >= 7 : false;

            const unlockedCount = [hasCheckIn, hasStreak, hasJournal, hasRitualMaster].filter(Boolean).length;

            return (
              <div className="flex flex-col sm:flex-row lg:flex-col gap-4 flex-shrink-0 w-full lg:w-auto animate-fadeIn">
                {/* This Week's Wellness Card */}
                <div className="relative z-10 w-full sm:w-[320px] bg-bg3 border border-border2 rounded-[16px] p-5 backdrop-blur-md shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-border pb-2">
                    <span className="font-[family-name:var(--font-serif)] text-[15px] font-light text-text">
                      This Week's Wellness
                    </span>
                    <span className="w-2 h-2 rounded-full bg-accent animate-pulse shadow-[0_0_8px_var(--accent)]" />
                  </div>

                  <div className="space-y-3.5 text-left">
                    {/* Rituals Row */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-full bg-green-dim flex items-center justify-center text-green shadow-[0_0_8px_var(--green-dim)]">
                            <CheckCircle2 className="w-4 h-4" />
                          </div>
                          <span className="text-xs text-text2 font-medium">Rituals Completed</span>
                        </div>
                        <span className="text-xs font-semibold text-green bg-green-dim border border-green/20 px-2 py-0.5 rounded-full">
                          {ritualsCompleted !== null ? `${ritualsCompleted}/7` : '5/7'}
                        </span>
                      </div>
                      <div className="w-full bg-border h-1 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-green to-teal rounded-full" 
                          style={{ width: `${((ritualsCompleted !== null ? ritualsCompleted : 5) / 7) * 100}%` }} 
                        />
                      </div>
                    </div>

                    {/* Mood Trend Row */}
                    {(() => {
                      const trend = getMoodTrend();
                      return (
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="w-7 h-7 rounded-full bg-teal-dim flex items-center justify-center text-teal shadow-[0_0_8px_var(--teal-dim)]">
                              <TrendingUp className="w-4 h-4" />
                            </div>
                            <span className="text-xs text-text2 font-medium">Mood Trend</span>
                          </div>
                          <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1 ${trend.color}`}>
                            {trend.arrow} {trend.text}
                          </span>
                        </div>
                      );
                    })()}

                    {/* ARIA Insights Row */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-rose-dim flex items-center justify-center text-rose shadow-[0_0_8px_var(--rose-dim)]">
                          <Brain className="w-4 h-4" />
                        </div>
                        <span className="text-xs text-text2 font-medium">ARIA Insights</span>
                      </div>
                      <span className="text-xs font-semibold text-rose bg-rose-dim border border-rose/20 px-2.5 py-0.5 rounded-full">
                        {insightPatternsCount !== null ? `${insightPatternsCount} New Pattern${insightPatternsCount !== 1 ? 's' : ''}` : '3 New Patterns'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Your Achievements Card */}
                <div className="relative z-10 w-full sm:w-[320px] bg-bg3 border border-border2 rounded-[16px] p-5 backdrop-blur-md shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-border pb-2">
                    <span className="font-[family-name:var(--font-serif)] text-[15px] font-light text-text flex items-center gap-2">
                      🏆 Your Achievements
                    </span>
                    <span className="text-[10px] text-text3 uppercase tracking-wider">
                      {unlockedCount} / 4 Unlocked
                    </span>
                  </div>

                  <div className="space-y-3 text-left">
                    {/* First Check-in */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-amber-dim flex items-center justify-center text-amber shadow-[0_0_8px_var(--amber-dim)]">
                          <Star className="w-4 h-4" fill="currentColor" />
                        </div>
                        <span className="text-xs text-text2 font-medium">First Check-in</span>
                      </div>
                      {hasCheckIn ? (
                        <span className="text-[10px] font-semibold text-green bg-green-dim border border-green/20 px-2 py-0.5 rounded-full">
                          Unlocked
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold text-text3 bg-bg4 border border-border px-2 py-0.5 rounded-full flex items-center gap-1">
                          <Lock className="w-2.5 h-2.5" /> Locked
                        </span>
                      )}
                    </div>

                    {/* 7-Day Streak */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-rose-dim flex items-center justify-center text-rose shadow-[0_0_8px_var(--rose-dim)]">
                          <Flame className="w-4 h-4" fill="currentColor" />
                        </div>
                        <span className="text-xs text-text2 font-medium">7-Day Streak</span>
                      </div>
                      {hasStreak ? (
                        <span className="text-[10px] font-semibold text-green bg-green-dim border border-green/20 px-2 py-0.5 rounded-full">
                          Unlocked
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold text-text3 bg-bg4 border border-border px-2 py-0.5 rounded-full flex items-center gap-1">
                          <Lock className="w-2.5 h-2.5" /> Locked
                        </span>
                      )}
                    </div>

                    {/* Journal Enthusiast */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-teal-dim flex items-center justify-center text-teal shadow-[0_0_8px_var(--teal-dim)]">
                          <BookOpen className="w-4 h-4" />
                        </div>
                        <span className="text-xs text-text2 font-medium">Journal Enthusiast</span>
                      </div>
                      {hasJournal ? (
                        <span className="text-[10px] font-semibold text-green bg-green-dim border border-green/20 px-2 py-0.5 rounded-full">
                          Unlocked
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold text-text3 bg-bg4 border border-border px-2 py-0.5 rounded-full flex items-center gap-1">
                          <Lock className="w-2.5 h-2.5" /> Locked
                        </span>
                      )}
                    </div>

                    {/* Ritual Master */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-accent-glow flex items-center justify-center text-text shadow-[0_0_8px_var(--accent-glow)]">
                          <Target className="w-4 h-4" />
                        </div>
                        <span className="text-xs text-text2 font-medium">Ritual Master</span>
                      </div>
                      {hasRitualMaster ? (
                        <span className="text-[10px] font-semibold text-green bg-green-dim border border-green/20 px-2 py-0.5 rounded-full">
                          Unlocked
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold text-text3 bg-bg4 border border-border px-2 py-0.5 rounded-full flex items-center gap-1">
                          <Lock className="w-2.5 h-2.5" /> Locked
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      </section>

      <WellnessInsightCard />

      {/* Quick Stats Summary */}
      <section>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-bg2 border border-border rounded-[20px] p-4 sm:p-5 text-center relative overflow-hidden flex flex-col justify-center min-h-[110px]">
            <div className="text-[10px] text-text3 uppercase tracking-wider mb-1">Current Streak</div>
            <div className="text-xl sm:text-2xl font-light font-[family-name:var(--font-serif)] text-amber">{streak} Days</div>
          </div>
          <div className="bg-bg2 border border-border rounded-[20px] p-4 sm:p-5 text-center relative overflow-hidden flex flex-col justify-center min-h-[110px]">
            <div className="text-[10px] text-text3 uppercase tracking-wider mb-1">Calm Score</div>
            <div className="text-xl sm:text-2xl font-light font-[family-name:var(--font-serif)] text-accent">{calmScore}%</div>
          </div>
          <div className="bg-bg2 border border-border rounded-[20px] p-4 sm:p-5 text-center relative overflow-hidden flex flex-col justify-center min-h-[110px]">
            <div className="text-[10px] text-text3 uppercase tracking-wider mb-1">Weekly Logs</div>
            <div className="text-xl sm:text-2xl font-light font-[family-name:var(--font-serif)] text-teal">{moodItems.length} Check-ins</div>
          </div>
          
          <div className="bg-bg2 border border-border rounded-[20px] p-4 sm:p-5 text-center relative overflow-hidden flex flex-col justify-between min-h-[110px]">
            <div>
              <div className="text-[10px] text-text3 uppercase tracking-wider mb-1 flex items-center justify-center gap-1.5 select-none">
                <Moon className="w-3.5 h-3.5 text-purple-400" />
                Sleep Tracker
              </div>
              {sleepStartTime ? (
                <div className="text-sm font-light text-text2 mt-1 animate-pulse">
                  Sleeping: {formatElapsed(currentTime - sleepStartTime)}
                </div>
              ) : (
                <div className="text-[11px] font-light text-text3 mt-1.5 leading-tight">
                  Aria will know how much you slept last night.
                </div>
              )}
            </div>

            <div className="mt-2.5">
              {sleepStartTime ? (
                <button
                  onClick={handleWokeUp}
                  className="w-full h-8 px-4 bg-teal-dim hover:bg-teal/20 text-teal border border-teal/30 hover:border-teal/50 rounded-full text-[11px] font-semibold tracking-wider transition-all cursor-pointer"
                >
                  Woke Up
                </button>
              ) : (
                <button
                  onClick={handleGoingToSleep}
                  className="w-full h-8 px-4 bg-rose-dim hover:bg-rose/25 text-rose border border-rose/30 hover:border-rose/50 rounded-full text-[11px] font-semibold tracking-wider transition-all cursor-pointer"
                >
                  Going to Sleep
                </button>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Today's Rituals */}
      <section>
        <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium mb-4">
          Today's Rituals
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
              Pending
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
              Pending
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
        <div className="bg-bg2 border border-border rounded-[14px] px-5 py-4 flex flex-col sm:flex-row gap-4 sm:gap-6 items-stretch sm:items-center">
          <div className="flex items-center gap-2.5 flex-1">
            <div className="w-2 h-2 rounded-full bg-green shadow-[0_0_8px_var(--green)] flex-shrink-0" />
            <div className="text-[13px]">
              <div className="text-text mb-0.5">Morning</div>
              <div className="text-[11px] text-text3">Still available today</div>
            </div>
          </div>
          <div className="hidden sm:block w-px h-8 bg-border" />
          <div className="sm:hidden w-full h-px bg-border/50" />
          <div className="flex items-center gap-2.5 flex-1">
            <div className="w-2 h-2 rounded-full bg-amber shadow-[0_0_8px_var(--amber)] flex-shrink-0" />
            <div className="text-[13px]">
              <div className="text-text mb-0.5">Wind Down</div>
              <div className="text-[11px] text-text3">Unlocks at 9:00 PM</div>
            </div>
          </div>
          <div className="hidden sm:block w-px h-8 bg-border" />
          <div className="sm:hidden w-full h-px bg-border/50" />
          <div className="text-left sm:text-right flex-0 flex justify-between sm:block items-center">
            <div className="text-[11px] text-text3 mb-0.5 sm:mb-0">Consecutive days</div>
            <div className="font-[family-name:var(--font-serif)] text-[22px] font-light text-text">{streak}</div>
          </div>
        </div>
      </section>

      {/* Weekly Calm + AI Insight */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <section>
          <div className="text-[10.5px] tracking-[0.14em] uppercase text-accent font-medium mb-4">
            Weekly Calm Score
          </div>
          <div className="bg-bg2 border border-border rounded-[20px] p-5 sm:p-6 flex flex-col sm:flex-row gap-5 sm:gap-6 items-center sm:items-start text-center sm:text-left w-full">
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
            <div className="flex-1 w-full">
              <div className="text-[15px] font-medium text-text mb-1">Your Weekly Score</div>
              <div className="text-[12.5px] text-text2 mb-3.5">
                {moodItems.length === 0 ? 'Complete rituals to build your score' : `Based on ${moodItems.length} check-in${moodItems.length !== 1 ? 's' : ''}`}
              </div>
              <div className="flex gap-1.5 items-end h-10 justify-center sm:justify-start">
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
          <div className="bg-bg2 border border-border rounded-[20px] p-5 sm:p-6 relative overflow-hidden flex flex-col justify-between h-full text-center sm:text-left">
            <div className="absolute top-0 left-0 right-0 bottom-0 bg-[radial-gradient(ellipse_at_top_right,rgba(139,124,248,0.06),transparent_60%)] pointer-events-none" />
            <div>
              <div className="flex items-center justify-center sm:justify-start gap-2.5 mb-3">
                <div className="text-[10px] tracking-[0.12em] uppercase text-accent bg-accent-glow border border-accent/20 px-2.5 py-1 rounded-full">
                  ARIA Insight
                </div>
              </div>
              <div className="text-xs font-semibold text-green mb-2.5">
                Your mood is trending up this week
              </div>
              <div className="font-[family-name:var(--font-serif)] text-base font-light text-text leading-relaxed italic mb-4 min-h-[50px]">
                {ariaLoading ? (
                  <span className="text-text3 text-sm not-italic">ARIA is thinking…</span>
                ) : (
                  `"${ariaInsight}"`
                )}
              </div>
            </div>
            <Link
              to="/aria"
              className="inline-flex items-center gap-1.5 text-[12.5px] text-accent font-medium bg-accent-glow border border-accent/25 px-4 py-2 rounded-full hover:bg-accent/20 transition-all self-center sm:self-start"
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
                  {i === 0 ? 'Play' : i === 1 ? '→ Start' : '→ Write'}
                </div>
              </div>
            ))
          )}
        </div>
      </section>

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
          ].slice(0, 3).map((badge, i) => (
            <div
              key={i}
              className={`bg-bg2 border border-border rounded-[14px] px-4 py-4 text-center transition-all ${badge.unlocked ? 'opacity-100' : 'opacity-60'}`}
            >
              <div className="w-10 h-10 rounded-full bg-bg4 mx-auto mb-2.5 flex items-center justify-center text-base text-text2">
                <Award size={18} className={badge.unlocked ? 'text-amber' : 'text-text3'} />
              </div>
              <div className="text-[13px] font-medium text-text mb-0.5">{badge.name}</div>
              <div className="text-[11px] text-text3">{badge.unlocked ? 'Earned' : 'Active'}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
