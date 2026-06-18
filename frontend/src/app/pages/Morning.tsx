import { useState } from 'react';
import { Frown, Meh, Smile, Sun, Wind, Activity, PenTool, Footprints, Heart, Moon } from 'lucide-react';
import { sanitizeForInput } from '@/lib/sanitize';
import { rituals as ritualsApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
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
  { id: 'breathwork', label: 'Breathwork', icon: <Wind className="w-6 h-6 text-sky-400" />, desc: '2 min box breathing' },
  { id: 'stretch', label: 'Stretch', icon: <Activity className="w-6 h-6 text-emerald-400" />, desc: 'Gentle morning stretch' },
  { id: 'journal', label: 'Journal', icon: <PenTool className="w-6 h-6 text-indigo-400" />, desc: 'Quick brain dump' },
  { id: 'walk', label: 'Walk', icon: <Footprints className="w-6 h-6 text-amber-400" />, desc: 'Short outdoor walk' },
  { id: 'gratitude', label: 'Gratitude', icon: <Heart className="w-6 h-6 text-rose-400" />, desc: 'Name 3 things' },
  { id: 'none', label: 'Skip today', icon: <Moon className="w-6 h-6 text-gray-400" />, desc: 'Rest is valid too' },
];

export default function Morning() {
  const { user } = useAuth();
  const [step, setStep] = useState(1);
  const [forecast, setForecast] = useState<number | null>(null);
  const [intention, setIntention] = useState('');
  const [activity, setActivity] = useState('');

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const handleComplete = async () => {
    if (!forecast && forecast !== 0) return;
    setSaving(true);
    setError('');
    try {
      await ritualsApi.saveMorning({
        forecast: MOOD_LABELS[forecast],
        intention: intention || 'Show up gently',
        activityType: activity || 'none',
        completedAt: new Date().toISOString(),
      });
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save ritual');
    } finally {
      setSaving(false);
    }
  };

  if (!user) {
    return (
      <GuestGate
        title="Morning Ritual"
        description="Start your day with intention. Align your mind, set a gentle focus, and choose a grounding exercise."
        icon={<Sun className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  if (saved) {
    return (
      <div className="space-y-8 animate-fadeIn flex flex-col items-center justify-center min-h-[50vh] text-center">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-4xl">
          ✦
        </div>
        <div>
          <h1 className="text-2xl font-light text-text mb-2">Morning ritual complete</h1>
          <p className="text-sm text-text2">You've set the tone for the day. Go be wonderful.</p>
        </div>
        <button
          onClick={() => { setSaved(false); setStep(1); setForecast(null); setIntention(''); setActivity(''); }}
          className="px-5 py-2.5 bg-bg3 border border-border text-text2 rounded-full text-sm hover:bg-bg4 transition-all"
        >
          Start over
        </button>
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
          <h1 className="text-[32px] font-light text-text">How do you anticipate today feeling?</h1>
          <p className="text-[15px] text-text2">Pick the tone of the day you are stepping into.</p>

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
              className="px-6 py-3 bg-accent text-white rounded-lg font-medium text-sm hover:bg-accent2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Continue →
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Intention */}
      {step === 2 && (
        <div className="space-y-6">
          <h1 className="text-[32px] font-light text-text">Set your intention.</h1>
          <p className="text-[15px] text-text2">What's one thing you want to be present for today?</p>

          <textarea
            value={intention}
            onChange={(e) => setIntention(sanitizeForInput(e.target.value))}
            placeholder="e.g. 'Be patient with myself' or 'Finish the report calmly'"
            className="w-full bg-bg2 border border-border rounded-[20px] px-5 py-4 text-sm text-text placeholder:text-text3 resize-none focus:outline-none focus:border-accent/30 min-h-28"
          />

          <div className="pt-2 flex gap-3">
            <button
              onClick={() => setStep(1)}
              className="px-5 py-3 bg-bg3 border border-border text-text2 rounded-lg font-medium text-sm hover:bg-bg4 transition-all"
            >
              ← Back
            </button>
            <button
              onClick={() => setStep(3)}
              className="px-6 py-3 bg-accent text-white rounded-lg font-medium text-sm hover:bg-accent2 transition-all"
            >
              Continue →
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Activity */}
      {step === 3 && (
        <div className="space-y-6">
          <h1 className="text-[32px] font-light text-text">Choose your morning anchor.</h1>
          <p className="text-[15px] text-text2">One small action to ground you before the day begins.</p>

          <div className="grid grid-cols-2 gap-3 pt-2">
            {ACTIVITIES.map((act) => (
              <button
                key={act.id}
                onClick={() => setActivity(act.id)}
                className={`bg-bg2 border rounded-[16px] px-5 py-4 flex items-center gap-3 text-left transition-all ${
                  activity === act.id
                    ? 'border-accent bg-accent/10'
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

          <div className="pt-2 flex gap-3">
            <button
              onClick={() => setStep(2)}
              className="px-5 py-3 bg-bg3 border border-border text-text2 rounded-lg font-medium text-sm hover:bg-bg4 transition-all"
            >
              ← Back
            </button>
            <button
              onClick={handleComplete}
              disabled={!activity || saving}
              className="px-6 py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-lg font-medium text-sm hover:opacity-90 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving…' : 'Complete Ritual ✦'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
