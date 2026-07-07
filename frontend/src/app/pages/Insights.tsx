import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '@/lib/auth';
import { ai as aiApi, profile as profileApi } from '@/lib/api';
import GuestGate from '@/app/components/GuestGate';
import { Loader2, Sparkles, Smile, Compass, Flame, Activity, TrendingUp, Heart } from 'lucide-react';

export default function Insights() {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [insightsData, setInsightsData] = useState<{
    calmness_score: number;
    consistency_index: number;
    interaction_focus: string;
    insights: string[];
  } | null>(null);
  
  const [stats, setStats] = useState<{
    total_moods: number;
    avg_mood: number;
    total_journals: number;
    total_rituals: number;
    total_clicks: number;
    total_navigations: number;
    top_page: string;
  } | null>(null);

  const [isPremium, setIsPremium] = useState(false);
  const [solsticeLetter, setSolsticeLetter] = useState<string | null>(null);
  const [loadingSolstice, setLoadingSolstice] = useState(false);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    async function fetchInsights() {
      try {
        const res = await aiApi.get30DayInsights();
        if (res.success) {
          setInsightsData(res.data);
          setStats(res.stats);
        } else {
          throw new Error('Failed to generate insights.');
        }

        // Check subscription status
        try {
          const prof = await profileApi.get();
          const premium = !!prof.is_premium;
          setIsPremium(premium);

          if (premium) {
            setLoadingSolstice(true);
            const letterRes = await aiApi.getSolsticeLetter();
            setSolsticeLetter(letterRes.letter);
          }
        } catch (profileErr) {
          console.error("Failed to fetch profile/solstice letter in Insights page:", profileErr);
        }
      } catch (err: any) {
        setError(err.message || 'An error occurred while analyzing wellness report.');
      } finally {
        setLoading(false);
        setLoadingSolstice(false);
      }
    }

    fetchInsights();
  }, [user]);

  if (!user) {
    return (
      <GuestGate
        title="30-Day Reflection & Growth Report"
        description="Sign in to unlock personalized habit patterns, calm score trends, and guidance from ARIA."
        icon={<Activity className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  if (loading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
        <p className="text-sm text-text3">Analyzing your 30-day reflection history and building your habit profile...</p>
      </div>
    );
  }

  if (error || !insightsData || !stats) {
    return (
      <div className="max-w-md mx-auto text-center space-y-4 py-12">
        <div className="text-rose text-lg">⚠️ Insight Generation Failed</div>
        <p className="text-sm text-text3">{error || 'Please ensure you have tracked some check-ins or rituals this month.'}</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fadeIn text-left">
      {/* Title */}
      <div>
        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">PERSONALIZED REPORT</div>
        <h1 className="text-3xl sm:text-4xl font-light text-text font-[family-name:var(--font-serif)]">30-Day AI Insights</h1>
        <p className="text-sm text-text3 font-light mt-1">Personalized habit trends and custom routines suggested by ARIA.</p>
      </div>

      {/* Grid of Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Calmness Score Card (Hero) */}
        <div className="bg-bg2 border-2 border-emerald-500/30 rounded-[24px] p-8 space-y-4 relative overflow-hidden shadow-xl md:col-span-3">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(16,185,129,0.08),transparent_60%)] pointer-events-none" />
          <div className="flex items-center justify-between">
            <span className="text-xs text-emerald-400 font-semibold uppercase tracking-wider">Primary Wellness Metric</span>
            <Smile className="w-6 h-6 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-[56px] font-extralight text-text tracking-tight">{insightsData.calmness_score}</span>
            <span className="text-lg text-text3">/ 100</span>
          </div>
          <div>
            <h3 className="text-base font-semibold text-text mb-1">Calmness Score</h3>
            <p className="text-xs text-text2 font-light leading-relaxed max-w-2xl">
              Measures your daily rhythm and level of balance based on your check-ins. A higher score reflects a consistent calm rhythm across your week.
            </p>
          </div>
        </div>

        {/* Consistency Index Card */}
        <div className="bg-bg2 border border-border rounded-[20px] p-6 space-y-4 relative overflow-hidden shadow-lg md:col-span-2">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(245,158,11,0.05),transparent_60%)] pointer-events-none" />
          <div className="flex items-center justify-between">
            <span className="text-xs text-text3 font-medium uppercase tracking-wider">Consistency Index</span>
            <Flame className="w-5 h-5 text-amber" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-extralight text-text tracking-tight">{insightsData.consistency_index}</span>
            <span className="text-sm text-text3">/ 100</span>
          </div>
          <p className="text-xs text-text2 font-light leading-relaxed">
            Tracks how consistently you complete morning focuses and evening reflections.
          </p>
        </div>

        {/* Focus Feature Card */}
        <div className="bg-bg2 border border-border rounded-[20px] p-6 space-y-4 relative overflow-hidden shadow-lg md:col-span-1">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(139,92,246,0.05),transparent_60%)] pointer-events-none" />
          <div className="flex items-center justify-between">
            <span className="text-xs text-text3 font-medium uppercase tracking-wider">Primary Habit</span>
            <Compass className="w-5 h-5 text-violet-400" />
          </div>
          <div className="flex items-baseline">
            <span className="text-2xl font-light text-text tracking-tight truncate w-full">{insightsData.interaction_focus}</span>
          </div>
          <p className="text-xs text-text2 font-light leading-relaxed pt-2">
            The tool you used most to build consistency.
          </p>
        </div>

      </div>

      {/* Main AI Advisory Panel */}
      <div className="bg-bg2 border border-border rounded-[24px] p-6 sm:p-8 space-y-6 relative overflow-hidden shadow-xl">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(233,75,111,0.06),transparent_60%)] pointer-events-none" />
        
        <div className="flex items-center gap-3 border-b border-border/80 pb-4">
          <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center text-accent">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 className="font-semibold text-text text-base">ARIA's Memory & Guidance</h3>
            <p className="text-xs text-text3">Personalized recommendations based on your daily reflections and consistency patterns.</p>
          </div>
        </div>

        {insightsData.insights.length === 0 ? (
          <div className="py-6 text-center space-y-3">
            <p className="text-sm text-text2 leading-relaxed">
              We're still gathering your rhythm patterns. You've completed {stats.total_rituals} routine(s) and logged {stats.total_moods} check-in(s) so far.
            </p>
            <p className="text-xs text-text3 font-light">
              Complete a few more daily routines to unlock ARIA's custom recommendations.
            </p>
          </div>
        ) : (
          <ul className="space-y-4">
            {insightsData.insights.map((insight, idx) => (
              <li key={idx} className="flex items-start gap-4 text-sm text-text2 leading-relaxed">
                <div className="w-6 h-6 rounded-full bg-accent/10 border border-accent/20 text-accent flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs">
                  {idx + 1}
                </div>
                <span className="font-light">{insight}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Telemetry Engagement Details */}
      <div className="bg-bg3 border border-border2 rounded-[20px] p-6 space-y-6 text-left">
        <h3 className="font-[family-name:var(--font-serif)] text-lg font-light text-text flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-accent" />
          Monthly Progress Summary
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-bg2/40 border border-border/60 rounded-xl p-4 text-center">
            <div className="text-[10px] text-text3 uppercase font-medium">Reflections Logged</div>
            <div className="text-2xl font-light text-text mt-1">{stats.total_moods}</div>
          </div>
          
          <div className="bg-bg2/40 border border-border/60 rounded-xl p-4 text-center">
            <div className="text-[10px] text-text3 uppercase font-medium">Journal Entries</div>
            <div className="text-2xl font-light text-text mt-1">{stats.total_journals}</div>
          </div>

          <div className="bg-bg2/40 border border-border/60 rounded-xl p-4 text-center">
            <div className="text-[10px] text-text3 uppercase font-medium">Routines Completed</div>
            <div className="text-2xl font-light text-text mt-1">{stats.total_rituals}</div>
          </div>

          <div className="bg-bg2/40 border border-border/60 rounded-xl p-4 text-center">
            <div className="text-[10px] text-text3 uppercase font-medium">Daily Interactions</div>
            <div className="text-2xl font-light text-text mt-1">{stats.total_clicks}</div>
          </div>
        </div>

        <div className="border-t border-border/60 pt-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-xs text-text3 font-light">
          <div>Top Visited Area: <span className="font-semibold text-text2">{stats.top_page}</span></div>
          <div className="flex items-center gap-1">
            <Heart className="w-3.5 h-3.5 text-accent fill-accent" />
            <span>Consistency builds routines. Keep reflecting daily!</span>
          </div>
        </div>
      </div>

      {/* The Personal Solstice Letter Card */}
      <div className="bg-bg2 border border-border rounded-[24px] p-8 space-y-6 relative overflow-hidden shadow-xl">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(99,102,241,0.06),transparent_60%)] pointer-events-none" />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-accent animate-pulse" />
            <h3 className="font-[family-name:var(--font-serif)] text-xl font-light text-text">The Personal Solstice</h3>
          </div>
          <span className="text-[10px] bg-accent/20 border border-accent/30 text-accent font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider">
            Premium Insight
          </span>
        </div>

        {isPremium ? (
          loadingSolstice ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="w-6 h-6 text-accent animate-spin" />
              <p className="text-xs text-text3">Synthesizing your seasonal growth letter...</p>
            </div>
          ) : (
            <div className="space-y-4 text-sm text-text2 leading-relaxed whitespace-pre-line border-t border-border/40 pt-4">
              {solsticeLetter || "Your Personal Solstice growth letter is preparing. Continue reflecting daily to enrich your seasonal analysis."}
            </div>
          )
        ) : (
          <div className="relative border-t border-border/40 pt-4">
            {/* Blurred Mock Content */}
            <div className="space-y-3 filter blur-sm select-none opacity-40">
              <h4 className="text-base font-semibold text-text">## The Season of Quiet Resilience</h4>
              <p className="text-sm">
                Over the past 30 days, your reflections show a deep alignment with quiet moments. You've successfully completed 14 evening rituals, releasing worries about tomorrow. Your mood patterns have stabilized around a self-reported level of 7.2.
              </p>
              <h4 className="text-base font-semibold text-text">## Private Victories</h4>
              <p className="text-sm">
                You've consistently prioritized letting go of control, especially during late-night journaling. This is a noticeable shift from earlier this month when rigid language dominated your check-ins.
              </p>
            </div>
            {/* Paywall Overlay */}
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-bg2/40 backdrop-blur-[2px] p-6 text-center space-y-4">
              <Lock className="w-8 h-8 text-accent animate-bounce" />
              <h4 className="text-base font-semibold text-text">Unlock Your Personal Solstice Letter</h4>
              <p className="text-xs text-text3 max-w-sm">
                MindCradle Premium synthesizes your entire month of check-ins, journal entries, and micro-habits into a seasonal narrative report.
              </p>
              <button
                onClick={() => navigate('/billing')}
                className="px-6 py-2 bg-accent hover:bg-accent2 text-white font-semibold rounded-full text-xs transition-all shadow-md smooth-hover-btn"
              >
                Upgrade to Premium
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Guided transition to Wind Down */}
      <div className="bg-bg2 border border-border rounded-[24px] p-6 text-center space-y-4 animate-fadeIn">
        <h3 className="font-medium text-text text-base">Ready to close your day?</h3>
        <p className="text-xs text-text2 max-w-md mx-auto">
          Transitions are key to consistent rest. Clear your mind, list your appreciations, and prepare for sleep with the evening routine.
        </p>
        <button
          onClick={() => navigate('/wind-down')}
          className="px-6 py-2.5 bg-gradient-to-r from-teal to-accent text-white rounded-full text-xs font-semibold hover:opacity-95 transition-all shadow-md smooth-hover-btn"
        >
          Begin Evening Wind Down →
        </button>
      </div>
    </div>
  );
}
