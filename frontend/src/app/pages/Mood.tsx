import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { sanitizeForInput } from '@/lib/sanitize';
import { Loader2, Frown, Meh, Smile, Laugh, Compass, Activity, BatteryWarning, AlertCircle, Heart, Flame, HelpCircle, Ghost, Sparkles, ThumbsDown, Lock } from 'lucide-react';
import { mood as moodApi, ai as aiApi, profile as profileApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import GuestGate from '@/app/components/GuestGate';
import { validateMood } from '@/lib/validation';

const MOOD_ICONS: Record<number, React.ReactNode> = {
  1: <Frown className="w-6 h-6 text-rose-400" />,
  2: <Meh className="w-6 h-6 text-amber-400" />,
  3: <Smile className="w-6 h-6 text-yellow-400" />,
  4: <Smile className="w-6 h-6 text-teal-400" />,
  5: <Laugh className="w-6 h-6 text-green-400" />
};
// Backend accepts 1–10; we map the 5-step UI to steps of 2
const MOOD_TO_LEVEL: Record<number, number> = { 1: 2, 2: 4, 3: 6, 4: 8, 5: 10 };

export default function Mood() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [selectedMood, setSelectedMood] = useState<number | null>(null);
  const [feelings, setFeelings] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const [notesError, setNotesError] = useState('');

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const [isPremium, setIsPremium] = useState(false);
  const [lastEnergyLevel, setLastEnergyLevel] = useState<number | null>(null);
  const [moodCount, setMoodCount] = useState(0);

  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState('');
  const [analysisData, setAnalysisData] = useState<{
    analysis: string;
    pattern: string;
    suggestion: string;
    mood_trend: string;
  } | null>(null);

  const allFeelings = [
    { label: 'Relaxed', icon: <Compass className="w-4 h-4 text-sky-400" /> },
    { label: 'Happy', icon: <Smile className="w-4 h-4 text-green-400" /> },
    { label: 'Sad', icon: <Frown className="w-4 h-4 text-blue-400" /> },
    { label: 'Stressed', icon: <Activity className="w-4 h-4 text-orange-400" /> },
    { label: 'Exhausted', icon: <BatteryWarning className="w-4 h-4 text-purple-400" /> },
    { label: 'Anxious', icon: <AlertCircle className="w-4 h-4 text-yellow-500" /> },
    { label: 'Grateful', icon: <Heart className="w-4 h-4 text-pink-400" /> },
    { label: 'Angry', icon: <Flame className="w-4 h-4 text-rose-500" /> },
    { label: 'Neutral', icon: <Meh className="w-4 h-4 text-gray-400" /> },
    { label: 'Confused', icon: <HelpCircle className="w-4 h-4 text-indigo-400" /> },
    { label: 'Scared', icon: <Ghost className="w-4 h-4 text-violet-400" /> },
    { label: 'Excited', icon: <Sparkles className="w-4 h-4 text-amber-400" /> },
    { label: 'Frustrated', icon: <ThumbsDown className="w-4 h-4 text-red-400" /> },
    { label: 'Content', icon: <Smile className="w-4 h-4 text-teal-400" /> },
  ];

  const toggleFeeling = (feelingLabel: string) => {
    setFeelings((prev) =>
      prev.includes(feelingLabel) ? prev.filter((f) => f !== feelingLabel) : [...prev, feelingLabel],
    );
  };

  const handleAnalyze = async (premiumOverride?: boolean) => {
    setAnalyzing(true);
    setAnalysisError('');
    setAnalysisData(null);
    try {
      const activePremium = premiumOverride !== undefined ? premiumOverride : isPremium;
      const range = activePremium ? '30d' : '7d';
      const historyRes = await moodApi.history(range);
      const items = historyRes.items || [];
      if (items.length === 0) {
        setAnalysisError(`No mood logs found for the last ${activePremium ? '30' : '7'} days. Try logging a check-in first.`);
        setAnalyzing(false);
        return;
      }
      
      const moodDataPayload = items.map(item => ({
        level: item.level,
        emotions: item.emotions,
        date: item.created
      }));

      const userId = user?.userId || '';
      const analysisRes = await aiApi.analyzeMood(moodDataPayload, userId);
      setAnalysisData(analysisRes);
    } catch (err) {
      setAnalysisError("Couldn't analyze mood trends, try again");
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    if (user) {
      profileApi.get()
        .then((res) => {
          const premium = !!res.is_premium;
          setIsPremium(premium);
          if (premium) {
            handleAnalyze(premium);
          }
        })
        .catch((err) => {
          console.error("Failed to load profile in Mood page:", err);
        });

      moodApi.history('7d').then((res) => {
        const items = res.items || [];
        setMoodCount(items.length);
        if (items.length > 0) {
          setLastEnergyLevel(items[0].level);
        }
      }).catch(() => {});
    }
  }, [user]);

  const handleChatWithAria = () => {
    if (!analysisData) return;
    const intervalStr = isPremium ? 'monthly' : 'weekly';
    const chatPrompt = `Let's discuss my ${intervalStr} mood analysis. ARIA noticed: "${analysisData.analysis}" and the pattern: "${analysisData.pattern}". How can I work on the suggestion: "${analysisData.suggestion}"?`;
    localStorage.setItem('mc_aria_context', chatPrompt);
    navigate('/aria');
  };

  const handleSave = async () => {
    if (selectedMood === null) {
      setError('Please select a mood level.');
      return;
    }
    const moodLevel = MOOD_TO_LEVEL[selectedMood];
    if (!validateMood(moodLevel)) {
      setError('Invalid mood level selection.');
      return;
    }
    if (notes.length > 5000) {
      setError('Notes cannot exceed 5000 characters.');
      return;
    }
    setError('');
    setSaving(true);
    try {
      await moodApi.log(moodLevel, feelings, notes);
      
      aiApi.trackInteraction({
        event_type: 'input_submit',
        page_path: '/mood',
        input_placeholder: 'mood_checkin_notes',
        input_length: notes.length,
        metadata: {
          mood_level: moodLevel,
          emotions_count: feelings.length,
        }
      }).catch((err) => console.error('Failed to log mood telemetry:', err));

      setSaved(true);

      // Automatically re-run the 30-day analytics if premium
      if (isPremium) {
        handleAnalyze();
      }
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error('Mood save failed', err);
      }
      setError(err instanceof Error ? err.message : 'Failed to save check-in');
    } finally {
      setSaving(false);
    }
  };


  if (!user) {
    return (
      <GuestGate
        title="Calm & Reflection Tracker"
        description="Acknowledge your emotional rhythm. Log your energy, save personal reflections, and let ARIA highlight consistency patterns."
        icon={<Smile className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  if (saved) {
    return (
      <div className="space-y-8 animate-fadeIn flex flex-col items-center justify-center min-h-[50vh] text-center">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-500 to-teal flex items-center justify-center text-4xl text-white">
          ✓
        </div>
        <div>
          <h1 className="text-2xl font-light text-text mb-2">Mood Check-in Saved</h1>
          <p className="text-sm text-text2 max-w-md mx-auto mb-6">You've logged your energy level. Next, let's capture your deeper thoughts in your daily reflection journal.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-center">
          <button
            onClick={() => navigate('/journal')}
            className="px-6 py-3 bg-accent text-white rounded-full font-semibold text-sm hover:bg-accent2 transition-all shadow-md smooth-hover-btn"
          >
            Continue to Journal →
          </button>
          <button
            onClick={() => {
              setSaved(false);
              setSelectedMood(null);
              setFeelings([]);
              setNotes('');
              setNotesError('');
            }}
            className="px-5 py-3 bg-bg3 border border-border text-text3 hover:text-text rounded-full font-medium text-sm hover:bg-bg4 transition-all smooth-hover-btn"
          >
            Log Another Entry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-4">CHECK IN</div>
        <h1 className="text-3xl font-light text-text mb-2">Calm & Reflection Tracker</h1>
      </div>

      {/* Success banner */}
      {error && (
        <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3">
          {error}
        </div>
      )}

      {/* Current mood */}
      <section className="space-y-4">
        <h2 className="text-base font-medium text-text">What is your energy level right now?</h2>
        <div className="flex gap-3">
          {[1, 2, 3, 4, 5].map((mood) => (
            <button
              key={mood}
              onClick={() => setSelectedMood(mood)}
              className={`w-14 h-14 rounded-full flex items-center justify-center text-2xl transition-all smooth-hover-btn ${
                selectedMood === mood
                  ? 'bg-accent/20 border-2 border-accent scale-110'
                  : 'bg-bg3 border border-border hover:bg-bg4'
              }`}
            >
              {MOOD_ICONS[mood]}
            </button>
          ))}
        </div>
      </section>

      {/* Feelings */}
      <section className="space-y-4">
        <div>
          <h2 className="text-base font-medium text-text mb-1">Which emotions describe your current state?</h2>
          <p className="text-xs text-text3">Select all that apply</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {allFeelings.map((feeling) => (
            <button
              key={feeling.label}
              onClick={() => toggleFeeling(feeling.label)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-all flex items-center gap-1.5 smooth-hover-btn ${
                feelings.includes(feeling.label)
                  ? 'bg-accent/20 border border-accent text-accent'
                  : 'bg-bg3 border border-border text-text2 hover:bg-bg4'
              }`}
            >
              {feeling.icon}
              <span>{feeling.label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Notes */}
      <section className="space-y-4">
        <h2 className="text-base font-medium text-text">Add details or thoughts</h2>
        <textarea
          value={notes}
          onChange={(e) => {
            const val = sanitizeForInput(e.target.value);
            setNotes(val);
            if (val.length > 5000) {
              setNotesError('Notes cannot exceed 5000 characters');
            } else {
              setNotesError('');
            }
          }}
          onBlur={() => {
            if (notes.length > 5000) {
              setNotesError('Notes cannot exceed 5000 characters');
            } else {
              setNotesError('');
            }
          }}
          placeholder="Write down what is occupying your thoughts right now..."
          className={`w-full bg-bg2 border rounded-[14px] px-4 py-3 text-sm text-text placeholder:text-text3 resize-none focus:outline-none min-h-32 transition-colors ${
            notesError ? 'border-rose focus:border-rose' : 'border-border focus:border-border2'
          }`}
        />
        {notesError && <span className="text-xs text-rose mt-1 block">{notesError}</span>}
        <div className="text-xs text-text3 flex justify-between flex-wrap gap-2">
          <span>{notes.length} characters · {notes.split(/\s+/).filter(Boolean).length} words</span>
          {lastEnergyLevel !== null && (
            <span className="italic text-accent">
              {lastEnergyLevel >= 7
                ? "Last time you logged high energy. How does your balance feel today?"
                : `Your last check-in was at a lower energy level (${lastEnergyLevel}/10). Take a gentle breath and note down how you're feeling now.`
              }
            </span>
          )}
        </div>
      </section>


      {/* Submit */}
      <div className="flex gap-3 pt-4">
        <button
          onClick={handleSave}
          disabled={saving || selectedMood === null || notesError !== ''}
          className="px-6 py-3 bg-accent text-white rounded-full font-semibold text-sm hover:bg-accent2 transition-all disabled:opacity-40 disabled:cursor-not-allowed smooth-hover-btn shadow-md animate-fadeIn"
        >
          {saving ? 'Saving…' : 'Save Daily Reflection'}
        </button>
        <button
          onClick={() => { setSelectedMood(null); setFeelings([]); setNotes(''); setError(''); }}
          className="px-6 py-3 bg-bg3 border border-border text-text2 rounded-full font-medium text-sm hover:bg-bg4 transition-all smooth-hover-btn"
        >
          Clear
        </button>
      </div>

      {/* AI Insight */}
      <section className="space-y-3 border-t border-border/45 pt-6">
        <div className="text-xs text-accent tracking-[0.1em] uppercase">AI COMPANION</div>
        <div className="bg-bg2 border border-border rounded-[20px] px-6 py-5 smooth-hover-card">
          <h3 className="text-base font-medium text-text mb-3">Insights by ARIA</h3>
          
          {analyzing && (
            <div className="flex flex-col items-center justify-center py-6 space-y-3">
              <Loader2 className="w-6 h-6 text-accent animate-spin" />
              <span className="text-xs text-text3">Analyzing your daily logs...</span>
            </div>
          )}

          {analysisError && !analyzing && (
            <p className="text-sm text-rose mb-4">{analysisError}</p>
          )}

          {!analysisData && !analyzing && (
            <>
              <p className="text-sm text-text2 mb-4">
                {moodCount === 0 ? (
                  <>Log your first check-in above to start mapping your calmness score trend and let ARIA highlight your rhythm.</>
                ) : (
                  <>You have checked in {moodCount} time(s) so far. Log {3 - moodCount > 0 ? 3 - moodCount : 1} more day(s) to allow ARIA to generate your first pattern analysis.</>
                )}
              </p>
              <button
                onClick={() => handleAnalyze()}
                className="px-5 py-2.5 bg-accent-glow border border-accent/25 text-accent rounded-full text-sm font-medium hover:bg-accent/20 transition-all"
              >
                Generate Calm Insights
              </button>
            </>
          )}

          {analysisData && !analyzing && (
            <div className="space-y-4 animate-fadeIn">
              <h4 className="text-sm font-medium text-accent">Here are the observations for your past {isPremium ? 'month' : 'week'}:</h4>
              <div className="space-y-3.5 pt-1">
                <div>
                  <div className="text-[10px] tracking-wider uppercase text-text3 mb-1">Recent Trends</div>
                  <p className="text-sm text-text2 leading-relaxed italic font-[family-name:var(--font-serif)]">
                    "{analysisData.analysis}"
                  </p>
                </div>
                <div className="border-t border-border/40 pt-3">
                  <div className="text-[10px] tracking-wider uppercase text-text3 mb-1">Identified Pattern</div>
                  <p className="text-sm text-text2 leading-relaxed">{analysisData.pattern}</p>
                </div>
                <div className="border-t border-border/40 pt-3">
                  <div className="text-[10px] tracking-wider uppercase text-text3 mb-1">Actionable Tip</div>
                  <p className="text-sm text-text2 leading-relaxed">{analysisData.suggestion}</p>
                </div>
                <div className="border-t border-border/40 pt-3.5 flex items-center justify-between gap-3 flex-wrap">
                  <span className="text-xs text-text3">
                    Calm Trend: <span className="font-semibold text-accent capitalize">{analysisData.mood_trend}</span>
                  </span>
                  <button
                    onClick={handleChatWithAria}
                    className="px-4 py-2 bg-gradient-to-r from-accent2 to-teal text-white rounded-full text-xs font-medium hover:opacity-90 transition-all"
                  >
                    Discuss Insights with ARIA
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
