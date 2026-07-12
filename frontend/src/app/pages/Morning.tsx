import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Frown, Meh, Smile, Sun, Wind, Activity, PenTool, Footprints, Heart, Moon } from 'lucide-react';
import { sanitizeForInput } from '@/lib/sanitize';
import { rituals as ritualsApi, mood as moodApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useGrowth } from '@/context/GrowthContext';
import GuestGate from '@/app/components/GuestGate';

const MOOD_LABELS: Record<number, string> = {
  0: 'Heavy', 1: 'Unsettled', 2: 'Neutral', 3: 'Hopeful', 4: 'Bright',
};
const MOOD_ICONS: Record<number, React.ReactNode> = {
  0: <Frown className="w-7 h-7 text-rose-400" />,
  1: <Meh className="w-7 h-7 text-amber-400" />,
  2: <Smile className="w-7 h-7 text-yellow-400" />,
  3: <Smile className="w-7 h-7 text-teal-400" />,
  4: <Sun className="w-7 h-7 text-green-400" />,
};
const ACTIVITIES = [
  { id: 'breathwork', label: 'Breathwork', icon: <Wind className="w-6 h-6 text-sky-400" />, desc: '2-minute box breathing for focus' },
  { id: 'stretch', label: 'Stretch', icon: <Activity className="w-6 h-6 text-emerald-400" />, desc: 'Gentle morning stretch for energy' },
  { id: 'journal', label: 'Journal', icon: <PenTool className="w-6 h-6 text-indigo-400" />, desc: 'Quick reflection to clear your mind' },
  { id: 'walk', label: 'Walk', icon: <Footprints className="w-6 h-6 text-amber-400" />, desc: 'Short walk to build momentum' },
  { id: 'gratitude', label: 'Gratitude', icon: <Heart className="w-6 h-6 text-rose-400" />, desc: 'Note three things you appreciate' },
  { id: 'none', label: 'Skip today', icon: <Moon className="w-6 h-6 text-gray-400" />, desc: 'Rest is productive too' },
];

export default function Morning() {
  const { user } = useAuth();
  const { variantOf, trackEvent } = useGrowth();
  const layoutVariant = variantOf('morning_habit_layout', 'control');
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [forecast, setForecast] = useState<number | null>(null);
  const [intention, setIntention] = useState('');
  const [activity, setActivity] = useState('');
  const [suggestedPrompt, setSuggestedPrompt] = useState('');

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const [streak, setStreak] = useState(0);
  const [lastIntention] = useState(() => localStorage.getItem('last_morning_intention') || '');
  const [lastActivity] = useState(() => localStorage.getItem('last_morning_activity') || '');

  useEffect(() => {
    if (!user) return;
    moodApi.history('7d').then((res) => {
      const uniqueDates = new Set(res.items.map((item) => item.created.slice(0, 10)));
      setStreak(uniqueDates.size);
    }).catch(() => {});

    ritualsApi.getMorningPrompt()
      .then((res) => {
        if (res.prompt) {
          setSuggestedPrompt(res.prompt);
        }
      })
      .catch(() => {});
  }, [user]);

  const handleComplete = async () => {
    if (!forecast && forecast !== 0) return;
    setSaving(true);
    setError('');
    try {
      if (user) {
        await ritualsApi.saveMorning({
          forecast: MOOD_LABELS[forecast],
          intention: intention || 'Show up gently',
          activityType: activity || 'none',
          completedAt: new Date().toISOString(),
        });
        trackEvent('morning_ritual_completed', { activity_id: activity, layout_variant: layoutVariant });
      }
      localStorage.setItem('last_morning_intention', intention || 'Show up gently');
      localStorage.setItem('last_morning_activity', activity || 'none');
      localStorage.setItem('morning_completed_at', new Date().toISOString());
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save ritual');
    } finally {
      setSaving(false);
    }
  };

  if (saved) {
    return (
      <div className="space-y-8 animate-fadeIn flex flex-col items-center justify-center min-h-[50vh] text-center">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-4xl text-white">
          ✦
        </div>
        <div>
          <h1 className="text-2xl font-light text-text mb-2">Morning Routine Completed</h1>
          <p className="text-sm text-text2 max-w-md mx-auto mb-6">You've established your rhythm for today. Ready to check in on your emotional outlook next?</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-center">
          <button
            onClick={() => navigate('/mood')}
            className="px-6 py-3 bg-accent text-white rounded-full font-semibold text-sm hover:bg-accent2 transition-all shadow-md smooth-hover-btn"
          >
            Check In Your Mood →
          </button>
          <button
            onClick={() => { setSaved(false); setStep(1); setForecast(null); setIntention(''); setActivity(''); }}
            className="px-5 py-3 bg-bg3 border border-border text-text3 hover:text-text rounded-full font-medium text-sm hover:bg-bg4 transition-all smooth-hover-btn"
          >
            Reset Routine
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Progress */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5 text-[10px] tracking-[0.12em] uppercase text-accent">
          <Sun className="w-4 h-4 text-accent animate-pulse" />
          STEP {step} OF 3
        </div>
        <div className="flex gap-1.5 ml-2">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-1 rounded-full transition-all ${s <= step ? 'w-6 bg-accent' : 'w-3 bg-bg4'}`}
            />
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3">
          {error}
        </div>
      )}

      {/* Step 1: Forecast */}
      {step === 1 && (
        <div className="space-y-6">
          <h1 className="text-[32px] font-light text-text">
            {lastIntention ? (
              <>Yesterday your focus was <span className="text-accent italic">"{lastIntention}"</span>. How is today looking?</>
            ) : streak > 0 ? (
              <>Streak active: {streak} days. Let's forecast today's focus.</>
            ) : (
              <>Let's set today's rhythm. How is your energy looking?</>
            )}
          </h1>
          <p className="text-[15px] text-text2">Select the feeling that will guide your actions today.</p>

          <div className="flex gap-4 items-center pt-6">
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="flex flex-col items-center gap-3">
                <button
                  onClick={() => setForecast(i)}
                  className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
                    forecast === i
                      ? 'bg-accent/20 border-2 border-accent scale-110'
                      : 'bg-bg3 border border-border hover:bg-bg4 hover:border-border2'
                  }`}
                >
                  {MOOD_ICONS[i]}
                </button>
                <span className="text-xs text-text3">{MOOD_LABELS[i]}</span>
              </div>
            ))}
          </div>

          <div className="pt-8">
            <button
              onClick={() => setStep(2)}
              disabled={forecast === null}
              className="px-6 py-3 bg-accent text-white rounded-full font-medium text-sm hover:bg-accent2 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
            >
              Continue to Focus →
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Intention */}
      {step === 2 && (
        <div className="space-y-6">
          <h1 className="text-[32px] font-light text-text">Set Your Daily Focus</h1>
          <p className="text-[15px] text-text2">Write down a single focus to anchor your day.</p>

          {suggestedPrompt && (
            <div className="bg-accent/10 border border-accent/20 rounded-[14px] p-4 text-xs text-text flex items-center justify-between gap-4">
              <div>
                <span className="font-semibold text-accent2 block mb-0.5">ARIA's Suggested Anchor Focus:</span>
                <span className="italic">"{suggestedPrompt}"</span>
              </div>
              <button
                type="button"
                onClick={() => setIntention(suggestedPrompt)}
                className="shrink-0 bg-accent hover:bg-accent2 text-bg text-[10px] font-semibold px-2.5 py-1.5 rounded-lg transition-all cursor-pointer"
              >
                Use Suggestion
              </button>
            </div>
          )}

          <textarea
            value={intention}
            onChange={(e) => setIntention(sanitizeForInput(e.target.value))}
            placeholder={lastIntention ? `Your last focus was: "${lastIntention}". What is today's anchor?` : 'e.g., "Bring patience to my interactions" or "Complete my tasks with calm focus"'}
            className="w-full bg-bg2 border border-border rounded-[20px] px-5 py-4 text-sm text-text placeholder:text-text3 resize-none focus:outline-none focus:border-accent/30 min-h-28"
          />

          <div className="pt-2 flex gap-3 items-center">
            <button
              onClick={() => setStep(1)}
              className="px-5 py-3 text-text3 hover:text-text rounded-full font-medium text-sm transition-all"
            >
              ← Back
            </button>
            <button
              onClick={() => setStep(3)}
              className="px-6 py-3 bg-accent text-white rounded-full font-medium text-sm hover:bg-accent2 transition-all shadow-md"
            >
              Continue to Anchor →
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Activity */}
      {step === 3 && (
        <div className="space-y-6">
          <h1 className="text-[32px] font-light text-text">
            {lastActivity && lastActivity !== 'none' ? (
              <>Select Your Morning Habit (Yesterday: {ACTIVITIES.find(a => a.id === lastActivity)?.label || lastActivity})</>
            ) : (
              <>Select Your Morning Habit</>
            )}
          </h1>
          <p className="text-[15px] text-text2">Pick a 2-minute routine to build immediate momentum and calm.</p>

          {layoutVariant === 'creative' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              {ACTIVITIES.map((act) => (
                <button
                  key={act.id}
                  onClick={() => {
                    setActivity(act.id);
                    trackEvent('morning_habit_click', { activity_id: act.id, layout_variant: 'creative' });
                  }}
                  className={`relative overflow-hidden group rounded-[22px] p-5 flex items-start gap-4 transition-all duration-300 text-left border ${
                    activity === act.id
                      ? 'border-accent bg-accent/10 shadow-[0_8px_30px_rgb(108,92,231,0.08)] scale-[1.03]'
                      : 'border-border/60 bg-bg2/40 hover:border-accent2/30 hover:bg-bg3/60'
                  }`}
                >
                  <div className="absolute inset-0 bg-gradient-to-tr from-accent2/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                  
                  <div className={`p-3 rounded-xl transition-transform duration-300 group-hover:scale-110 ${
                    activity === act.id ? 'bg-accent/20 text-accent2' : 'bg-bg/80 text-text2'
                  }`}>
                    {act.icon}
                  </div>
                  <div className="space-y-1">
                    <div className="text-sm font-semibold text-text group-hover:text-accent2 transition-colors duration-200">
                      {act.label}
                    </div>
                    <div className="text-xs text-text3 leading-relaxed">
                      {act.desc}
                    </div>
                  </div>
                  {act.id === 'breathwork' && (
                    <span className="absolute top-3 right-3 bg-teal/15 text-teal text-[9px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider scale-90">
                      Recommended
                    </span>
                  )}
                </button>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 pt-2">
              {ACTIVITIES.map((act) => (
                <button
                  key={act.id}
                  onClick={() => {
                    setActivity(act.id);
                    trackEvent('morning_habit_click', { activity_id: act.id, layout_variant: 'control' });
                  }}
                  className={`bg-bg2 border rounded-[16px] px-5 py-4 flex items-center gap-3 text-left transition-all ${
                    activity === act.id
                      ? 'border-accent bg-accent/10 shadow-[0_0_15px_rgba(108,92,231,0.08)] scale-[1.02]'
                      : 'border-border hover:border-border2 hover:bg-bg3'
                  }`}
                >
                  <span className="text-2xl">{act.icon}</span>
                  <div>
                    <div className="text-sm text-text font-medium">{act.label}</div>
                    <div className="text-xs text-text3">{act.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          )}

          <div className="pt-2 flex gap-3 items-center">
            <button
              onClick={() => setStep(2)}
              className="px-5 py-3 text-text3 hover:text-text rounded-full font-medium text-sm transition-all"
            >
              ← Back
            </button>
            <button
              onClick={handleComplete}
              disabled={!activity || saving}
              className="px-6 py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-full font-semibold text-sm hover:opacity-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
            >
              {saving ? 'Saving…' : 'Save Routine & Finish ✦'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
