import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Check, Moon, Leaf, HandHelping, Lightbulb, Book, Sparkles, CloudRain, Wind } from 'lucide-react';
import { sanitizeForInput } from '@/lib/sanitize';
import { rituals as ritualsApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import GuestGate from '@/app/components/GuestGate';
import { audioManager } from '@/lib/audioManager';

const soundscapes = [
  { id: 'quiet-library', title: 'The Quiet Library', icon: <Book className="w-5 h-5 text-teal-400" />, url: 'https://nnwuthynlxrbvuxmpjgu.supabase.co/storage/v1/object/public/Soundspaces/library.mp3' },
  { id: 'moonlit-garden', title: 'Moonlit Garden', icon: <Sparkles className="w-5 h-5 text-teal-400" />, url: 'https://nnwuthynlxrbvuxmpjgu.supabase.co/storage/v1/object/public/Soundspaces/garden.mp3' },
  { id: 'rainy-window', title: 'Rainy Window', icon: <CloudRain className="w-5 h-5 text-teal-400" />, url: 'https://nnwuthynlxrbvuxmpjgu.supabase.co/storage/v1/object/public/Soundspaces/rain.mp3' },
];

export default function WindDown() {
  const { user } = useAuth();
  const navigate = useNavigate();
  // Checklist
  const [release, setRelease] = useState('');
  const [gratitudes, setGratitudes] = useState(['', '', '']);
  const [audioChoice, setAudioChoice] = useState('');

  // Subscribe to global audioManager
  useEffect(() => {
    return audioManager.subscribe((state) => {
      if (state.isPlaying && state.trackId && state.trackId.startsWith('winddown-')) {
        setAudioChoice(state.trackId.replace('winddown-', ''));
      } else {
        setAudioChoice('');
      }
    });
  }, []);

  const handleAudioChoice = (id: string) => {
    if (!id) {
      audioManager.stop();
      return;
    }
    const trackId = `winddown-${id}`;
    if (audioManager.isPlaying(trackId)) {
      audioManager.stop();
    } else {
      const selected = soundscapes.find(s => s.id === id);
      if (selected && selected.url) {
        audioManager.play(trackId, selected.url);
      }
    }
  };

  // Breathing states
  const [breathingCompleted, setBreathingCompleted] = useState(false);
  const [isBreathingActive, setIsBreathingActive] = useState(false);
  const [breathPhase, setBreathPhase] = useState<'idle' | 'inhale' | 'hold' | 'exhale'>('idle');
  const [breathSeconds, setBreathSeconds] = useState(0);
  const [breathCycle, setBreathCycle] = useState(1);

  // Derived
  const leaveChecked = release.trim().length > 0;
  const gratitudesChecked = gratitudes.every((g) => g.trim().length > 0);
  const breathingChecked = breathingCompleted;
  const audioChecked = audioChoice !== '';
  const allChecked = leaveChecked && gratitudesChecked && breathingChecked && audioChecked;

  const [step, setStep] = useState<'checklist' | 'detail' | 'done'>('checklist');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [suggestedPrompt, setSuggestedPrompt] = useState('Write down one thought or concern you wish to let go of tonight.');

  useEffect(() => {
    if (!user) return;
    ritualsApi.getWindDownPrompt()
      .then((res) => {
        if (res.prompt) {
          setSuggestedPrompt(res.prompt);
        }
      })
      .catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!isBreathingActive) return;

    let timer: any;
    
    timer = setInterval(() => {
      setBreathSeconds((prev) => {
        if (prev <= 1) {
          if (breathPhase === 'idle') {
            setBreathPhase('inhale');
            return 4;
          } else if (breathPhase === 'inhale') {
            setBreathPhase('hold');
            return 7;
          } else if (breathPhase === 'hold') {
            setBreathPhase('exhale');
            return 8;
          } else if (breathPhase === 'exhale') {
            if (breathCycle >= 4) {
              setIsBreathingActive(false);
              setBreathingCompleted(true);
              setBreathPhase('idle');
              return 0;
            } else {
              setBreathCycle((c) => c + 1);
              setBreathPhase('inhale');
              return 4;
            }
          }
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isBreathingActive, breathPhase, breathCycle]);

  const startBreathing = () => {
    setBreathingCompleted(false);
    setIsBreathingActive(true);
    setBreathPhase('inhale');
    setBreathSeconds(4);
    setBreathCycle(1);
  };

  // Breathing styles mapping
  let transitionStyle = 'all 1s ease-in-out';
  let scaleClass = 'scale-100';
  let bgGradient = 'from-bg3 to-bg3 border border-border';
  let glowClass = 'shadow-none';

  if (breathPhase === 'inhale') {
    transitionStyle = 'transform 4s ease-out, background-color 1s ease-out, shadow 1s ease-out';
    scaleClass = 'scale-125';
    bgGradient = 'from-teal/40 via-teal/30 to-accent/20';
    glowClass = 'shadow-[0_0_40px_rgba(45,212,191,0.45)]';
  } else if (breathPhase === 'hold') {
    transitionStyle = 'transform 7s linear, background-color 1s ease-in-out, shadow 1s ease-in-out';
    scaleClass = 'scale-125';
    bgGradient = 'from-accent/40 via-accent/30 to-indigo-500/20';
    glowClass = 'shadow-[0_0_50px_rgba(108,92,231,0.5)]';
  } else if (breathPhase === 'exhale') {
    transitionStyle = 'transform 8s ease-in-out, background-color 1s ease-in-out, shadow 1s ease-in-out';
    scaleClass = 'scale-85';
    bgGradient = 'from-indigo-500/20 via-teal/15 to-bg3';
    glowClass = 'shadow-[0_0_20px_rgba(99,102,241,0.25)]';
  }

  const updateGratitude = (index: number, val: string) => {
    const sanitizedVal = sanitizeForInput(val);
    setGratitudes((prev) => prev.map((g, i) => (i === index ? sanitizedVal : g)));
  };

  const handleBegin = async () => {
    if (!allChecked) return;
    setSaving(true);
    setError('');
    try {
      if (user) {
        await ritualsApi.saveWindDown({
          releaseItem: release,
          gratitudes: gratitudes.filter(Boolean),
          audioChoice,
          timer: '4m',
        });
      }
      localStorage.setItem('winddown_completed_at', new Date().toISOString());
      setStep('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save wind-down ritual');
    } finally {
      setSaving(false);
    }
  };

  if (step === 'done') {
    return (
      <div className="space-y-8 animate-fadeIn flex flex-col items-center justify-center min-h-[50vh] text-center">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-teal to-accent flex items-center justify-center text-4xl">
          <Moon className="text-4xl text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-light text-text mb-2">Evening Reflection Completed</h1>
          <p className="text-sm text-text2 max-w-md mx-auto mb-6">You've cleared your mind and set a calm tone for the night. Sleep well. <Moon className="inline-block align-text-bottom" /></p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-center">
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-3 bg-accent text-white rounded-full font-semibold text-sm hover:bg-accent2 transition-all shadow-md smooth-hover-btn"
          >
            Back to Dashboard →
          </button>
          <button
            onClick={() => { setStep('checklist'); setRelease(''); setGratitudes(['', '', '']); setAudioChoice(''); setBreathingCompleted(false); }}
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
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5 text-[10px] tracking-[0.12em] uppercase text-teal mb-6">
          <Moon size={14} className="text-teal" />
          EVENING ROUTINE
        </div>
        <h1 className="text-3xl font-light text-text mb-2">Evening Wind Down</h1>
        <p className="text-sm text-text2">Release the day's tasks and prepare your mind for restful sleep.</p>
      </div>

      {error && (
        <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3">
          {error}
        </div>
      )}

      {/* Leave something behind */}
      <section className="space-y-3">
        <div className={`border rounded-[14px] px-5 py-4 transition-all ${leaveChecked ? 'bg-bg2/40 border-green/30' : 'bg-bg2 border-border'}`}>
          <div className="flex items-center gap-4 mb-3">
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${leaveChecked ? 'bg-green border-green' : 'border-border'}`}>
              {leaveChecked && <Check className="w-4 h-4 text-white" />}
            </div>
            <div className="flex-1">
              <div className="text-sm text-text font-medium">Clear Your Mind</div>
              <div className="text-xs text-text3">
                {leaveChecked ? (
                  <span className="text-green font-medium">Left behind: "{release}"</span>
                ) : (
                  <span>{suggestedPrompt}</span>
                )}
              </div>
            </div>
            <div className="text-lg"><Leaf /></div>
          </div>
          <input
            type="text"
            value={release}
            onChange={(e) => setRelease(sanitizeForInput(e.target.value))}
            placeholder="e.g., An unfinished task, a minor frustration, or tomorrow's to-do list…"
            className="w-full bg-bg3 border border-border rounded-[10px] px-3.5 py-2.5 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/30 transition-colors"
          />
        </div>

        {/* Three gratitudes */}
        <div className={`border rounded-[14px] px-5 py-4 transition-all ${gratitudesChecked ? 'bg-bg2/40 border-green/30' : 'bg-bg2 border-border'}`}>
          <div className="flex items-center gap-4 mb-3">
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${gratitudesChecked ? 'bg-green border-green' : 'border-border'}`}>
              {gratitudesChecked && <Check className="w-4 h-4 text-white" />}
            </div>
            <div className="flex-1">
              <div className="text-sm text-text font-medium">Reflect on Gratitude</div>
              <div className="text-xs text-text3">
                {gratitudesChecked ? (
                  <span className="text-green font-medium">Today's Appreciations: "{gratitudes.filter(Boolean).join(', ')}"</span>
                ) : (
                  <span>Identify three simple moments or things you appreciated today.</span>
                )}
              </div>
            </div>
            <div className="text-lg"><HandHelping /></div>
          </div>
          <div className="space-y-2">
            {gratitudes.map((g, i) => (
              <input
                key={i}
                type="text"
                value={g}
                onChange={(e) => updateGratitude(i, e.target.value)}
                placeholder={`Gratitude ${i + 1}…`}
                className="w-full bg-bg3 border border-border rounded-[10px] px-3.5 py-2.5 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/30 transition-colors"
              />
            ))}
          </div>
        </div>

        {/* Breathing Ritual */}
        <div className={`border rounded-[14px] px-5 py-4 transition-all ${breathingChecked ? 'bg-bg2/40 border-green/30' : 'bg-bg2 border-border'}`}>
          <div className="flex items-center gap-4 mb-3">
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${breathingChecked ? 'bg-green border-green' : 'border-border'}`}>
              {breathingChecked && <Check className="w-4 h-4 text-white" />}
            </div>
            <div className="flex-1">
              <div className="text-sm text-text font-medium">Breathe & Release</div>
              <div className="text-xs text-text3">
                {breathingChecked ? (
                  <span className="text-green font-medium">Completed 4 cycles of 4-7-8 breathing.</span>
                ) : (
                  <span>Perform a 4-7-8 breathing exercise to calm your nervous system.</span>
                )}
              </div>
            </div>
            <div className="text-lg text-teal"><Wind /></div>
          </div>
          
          {isBreathingActive ? (
            <div className="flex flex-col items-center justify-center py-6 bg-bg3/40 rounded-[12px] border border-border/50 backdrop-blur-sm animate-fadeIn">
              <div
                style={{ transition: transitionStyle }}
                className={`w-40 h-40 rounded-full bg-gradient-to-br ${bgGradient} ${scaleClass} ${glowClass} flex flex-col items-center justify-center relative`}
              >
                <div className="absolute inset-0 rounded-full border border-teal/20 animate-ping opacity-10 pointer-events-none" />
                
                <span className="text-[10px] uppercase tracking-[0.2em] text-text2 font-semibold mb-1">
                  {breathPhase}
                </span>
                <span className="text-4xl font-light text-text">
                  {breathSeconds}
                </span>
                <span className="text-[9px] text-text3 mt-1.5">
                  Cycle {breathCycle} of 4
                </span>
              </div>
              <button
                onClick={() => {
                  setIsBreathingActive(false);
                  setBreathPhase('idle');
                }}
                className="mt-6 px-4 py-1.5 bg-rose/10 hover:bg-rose/20 text-rose border border-rose/20 rounded-full text-xs font-semibold tracking-wide transition-all smooth-hover-btn"
              >
                Stop Exercise
              </button>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row gap-3 pt-1">
              <button
                onClick={startBreathing}
                className="px-5 py-2.5 bg-teal/15 hover:bg-teal/25 text-teal border border-teal/25 rounded-full text-xs font-semibold tracking-wide transition-all smooth-hover-btn"
              >
                {breathingChecked ? 'Restart Breathing Exercise' : 'Start 4-7-8 Breathing (1.5 min)'}
              </button>
              {!breathingChecked && (
                <button
                  onClick={() => setBreathingCompleted(true)}
                  className="px-5 py-2.5 bg-bg3 hover:bg-bg4 text-text2 border border-border rounded-full text-xs font-medium transition-all smooth-hover-btn"
                >
                  Mark Completed Offline
                </button>
              )}
            </div>
          )}
        </div>

        {/* Sleep story */}
        <div className={`border rounded-[14px] px-5 py-4 transition-all ${audioChecked ? 'bg-bg2/40 border-green/30' : 'bg-bg2 border-border'}`}>
          <div className="flex items-center gap-4 mb-3">
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${audioChecked ? 'bg-green border-green' : 'border-border'}`}>
              {audioChecked && <Check className="w-4 h-4 text-white" />}
            </div>
            <div className="flex-1">
              <div className="text-sm text-text font-medium">Select a Soundscape</div>
              <div className="text-xs text-text3">
                {audioChecked ? (
                  <span className="text-green font-medium">Selected Soundscape: "{audioChoice}"</span>
                ) : (
                  <span>Choose a calming background audio to help you rest.</span>
                )}
              </div>
            </div>
            <div className="text-lg text-teal"><Moon size={18} /></div>
          </div>
          <div className="space-y-2">
            {soundscapes.map((story) => (
              <button
                key={story.id}
                onClick={() => handleAudioChoice(audioChoice === story.id ? '' : story.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-[10px] text-left transition-all ${
                  audioChoice === story.id
                    ? 'bg-teal/10 border border-teal/30'
                    : 'bg-bg3 border border-transparent hover:border-border'
                }`}
              >
                <span className="text-xl">{story.icon}</span>
                <span className="text-sm text-text">{story.title}</span>
                {audioChoice === story.id && (
                  <span className="ml-auto text-xs text-teal flex items-center gap-1.5 font-medium animate-pulse">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal animate-ping" />
                    Playing (Click to Stop)
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Progress */}
        <div className="text-xs text-text3 text-center pt-2">
          {[leaveChecked, gratitudesChecked, breathingChecked, audioChecked].filter(Boolean).length} of 4 sections completed
        </div>
      </section>

      {/* Begin button */}
      <section className={`border rounded-[20px] px-6 py-6 text-center space-y-4 transition-all ${allChecked ? 'bg-bg2 border-accent/40 shadow-[0_0_20px_rgba(108,92,231,0.08)]' : 'bg-bg2 border-border'}`}>
        <button
          onClick={handleBegin}
          disabled={!allChecked || saving}
          className={`px-8 py-3 rounded-full font-semibold text-sm transition-all flex items-center gap-2 mx-auto shadow-md ${
            allChecked
              ? 'bg-gradient-to-r from-teal to-accent text-white hover:opacity-95 cursor-pointer scale-105 shadow-[0_0_15px_rgba(108,92,231,0.2)]'
              : 'bg-bg3 border border-border text-text3 disabled:opacity-50 disabled:cursor-not-allowed'
          }`}
        >
          {saving ? 'Saving…' : 'Save Reflections & Complete →'}
        </button>
        <p className="text-xs text-text3">
          {allChecked ? 'Beautiful work. All 4 evening steps are complete. Ready to log your reflections?' : 'Complete all sections above to save your routine.'}
        </p>
      </section>

      {/* Tips */}
      <section className="bg-bg3/50 border border-border rounded-[14px] px-5 py-4">
        <div className="flex gap-3">
          <div className="text-lg"><Lightbulb /></div>
          <div>
            <div className="text-sm text-text mb-1">Evening Tip</div>
            <div className="text-xs text-text2">
              Dim your screen and set aside devices 30 minutes before resting to build a consistent sleep rhythm.
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
