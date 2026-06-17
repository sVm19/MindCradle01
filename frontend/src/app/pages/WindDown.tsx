import { useState } from 'react';
import { Check, Moon, Leaf, HandHelping, Lightbulb, Book, Sparkles, CloudRain } from 'lucide-react';
import { rituals as ritualsApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import GuestGate from '@/app/components/GuestGate';

export default function WindDown() {
  const { user } = useAuth();
  // Checklist
  const [release, setRelease] = useState('');
  const [gratitudes, setGratitudes] = useState(['', '', '']);
  const [audioChoice, setAudioChoice] = useState('');

  // Derived
  const leaveChecked = release.trim().length > 0;
  const gratitudesChecked = gratitudes.every((g) => g.trim().length > 0);
  const audioChecked = audioChoice !== '';
  const allChecked = leaveChecked && gratitudesChecked && audioChecked;

  const [step, setStep] = useState<'checklist' | 'detail' | 'done'>('checklist');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const updateGratitude = (index: number, val: string) => {
    setGratitudes((prev) => prev.map((g, i) => (i === index ? val : g)));
  };

  const handleBegin = async () => {
    if (!allChecked) return;
    setSaving(true);
    setError('');
    try {
      await ritualsApi.saveWindDown({
        releaseItem: release,
        gratitudes: gratitudes.filter(Boolean),
        audioChoice,
        timer: '3m',
      });
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
          <Moon className="text-4xl" />
        </div>
        <div>
          <h1 className="text-2xl font-light text-text mb-2">Wind-down complete</h1>
          <p className="text-sm text-text2">You've put the day down gently. Sleep well. <Moon className="inline-block align-text-bottom" /></p>
        </div>
        <button
          onClick={() => { setStep('checklist'); setRelease(''); setGratitudes(['', '', '']); setAudioChoice(''); }}
          className="px-5 py-2.5 bg-bg3 border border-border text-text2 rounded-full text-sm hover:bg-bg4 transition-all"
        >
          Start over
        </button>
      </div>
    );
  }

  if (!user) {
    return (
      <GuestGate
        title="Evening Wind Down"
        description="Close the day gently. Reflect on your gratitudes, release what no longer serves you, and listen to calming soundscapes."
        icon={<Moon className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5 text-[10px] tracking-[0.12em] uppercase text-teal mb-6">
          <Moon size={14} className="text-teal" />
          EVENING RITUAL
        </div>
        <h1 className="text-3xl font-light text-text mb-2">Wind Down</h1>
        <p className="text-sm text-text2">The day is ending. Let's put it down gently.</p>
      </div>

      {error && (
        <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3">
          {error}
        </div>
      )}

      {/* Leave something behind */}
      <section className="space-y-3">
        <div className="bg-bg2 border border-border rounded-[14px] px-5 py-4">
          <div className="flex items-center gap-4 mb-3">
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${leaveChecked ? 'bg-green border-green' : 'border-border'}`}>
              {leaveChecked && <Check className="w-4 h-4 text-white" />}
            </div>
            <div className="flex-1">
              <div className="text-sm text-text font-medium">Leave something behind</div>
              <div className="text-xs text-text3">What will you consciously release tonight?</div>
            </div>
            <div className="text-lg"><Leaf /></div>
          </div>
          <input
            type="text"
            value={release}
            onChange={(e) => setRelease(e.target.value)}
            placeholder="e.g. The argument from this morning…"
            className="w-full bg-bg3 border border-border rounded-[10px] px-3.5 py-2.5 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/30 transition-colors"
          />
        </div>

        {/* Three gratitudes */}
        <div className="bg-bg2 border border-border rounded-[14px] px-5 py-4">
          <div className="flex items-center gap-4 mb-3">
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${gratitudesChecked ? 'bg-green border-green' : 'border-border'}`}>
              {gratitudesChecked && <Check className="w-4 h-4 text-white" />}
            </div>
            <div className="flex-1">
              <div className="text-sm text-text font-medium">Three gratitudes</div>
              <div className="text-xs text-text3">Name three things you're thankful for today</div>
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

        {/* Sleep story */}
        <div className="bg-bg2 border border-border rounded-[14px] px-5 py-4">
          <div className="flex items-center gap-4 mb-3">
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${audioChecked ? 'bg-green border-green' : 'border-border'}`}>
              {audioChecked && <Check className="w-4 h-4 text-white" />}
            </div>
            <div className="flex-1">
              <div className="text-sm text-text font-medium">Drift into sleep</div>
              <div className="text-xs text-text3">Choose your sleep companion</div>
            </div>
            <div className="text-lg text-teal"><Moon size={18} /></div>
          </div>
          <div className="space-y-2">
            {[
              { id: 'quiet-library', title: 'The Quiet Library', icon: <Book className="w-5 h-5 text-teal-400" /> },
              { id: 'moonlit-garden', title: 'Moonlit Garden', icon: <Sparkles className="w-5 h-5 text-teal-400" /> },
              { id: 'rainy-window', title: 'Rainy Window', icon: <CloudRain className="w-5 h-5 text-teal-400" /> },
            ].map((story) => (
              <button
                key={story.id}
                onClick={() => setAudioChoice(story.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-[10px] text-left transition-all ${
                  audioChoice === story.id
                    ? 'bg-teal/10 border border-teal/30'
                    : 'bg-bg3 border border-transparent hover:border-border'
                }`}
              >
                <span className="text-xl">{story.icon}</span>
                <span className="text-sm text-text">{story.title}</span>
                {audioChoice === story.id && <span className="ml-auto text-xs text-teal">▶ Selected</span>}
              </button>
            ))}
          </div>
        </div>

        {/* Progress */}
        <div className="text-xs text-text3 text-center pt-2">
          {[leaveChecked, gratitudesChecked, audioChecked].filter(Boolean).length} / 3 completed
        </div>
      </section>

      {/* Begin button */}
      <section className="bg-bg2 border border-border rounded-[20px] px-6 py-6 text-center space-y-4">
        <button
          onClick={handleBegin}
          disabled={!allChecked || saving}
          className="px-8 py-3 bg-gradient-to-r from-teal to-accent text-white rounded-lg font-medium text-sm hover:opacity-90 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 mx-auto"
        >
          {saving ? 'Saving…' : 'Begin Wind Down →'}
        </button>
        <p className="text-xs text-text3">Fill all three sections to complete your ritual</p>
      </section>

      {/* Tips */}
      <section className="bg-bg3/50 border border-border rounded-[14px] px-5 py-4">
        <div className="flex gap-3">
          <div className="text-lg"><Lightbulb /></div>
          <div>
            <div className="text-sm text-text mb-1">Wind Down Tip</div>
            <div className="text-xs text-text2">
              Consider dimming your screen brightness and putting away devices 30 minutes before bed for better sleep quality.
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
