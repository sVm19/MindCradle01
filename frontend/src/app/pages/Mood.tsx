import { useState } from 'react';
import { useNavigate } from 'react-router';
import { Loader2 } from 'lucide-react';
import { mood as moodApi, ai as aiApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';

const MOOD_EMOJIS: Record<number, string> = { 1: '😟', 2: '😐', 3: '🙂', 4: '😊', 5: '😁' };
// Backend accepts 1–10; we map the 5-step UI to steps of 2
const MOOD_TO_LEVEL: Record<number, number> = { 1: 2, 2: 4, 3: 6, 4: 8, 5: 10 };

export default function Mood() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [selectedMood, setSelectedMood] = useState<number | null>(null);
  const [feelings, setFeelings] = useState<string[]>([]);
  const [notes, setNotes] = useState('');

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState('');
  const [analysisData, setAnalysisData] = useState<{
    analysis: string;
    pattern: string;
    suggestion: string;
    mood_trend: string;
  } | null>(null);

  const allFeelings = [
    '😌 Relaxed', '😊 Happy', '😢 Sad', '😰 Stressed', '🥱 Exhausted',
    '😔 Anxious', '🤗 Grateful', '😡 Angry', '😐 Neutral', '🤔 Confused',
    '😨 Scared', '🤩 Excited', '😞 Frustrated', '🙂 Content',
  ];

  const toggleFeeling = (feeling: string) => {
    setFeelings((prev) =>
      prev.includes(feeling) ? prev.filter((f) => f !== feeling) : [...prev, feeling],
    );
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalysisError('');
    setAnalysisData(null);
    try {
      const historyRes = await moodApi.history('7d');
      const items = historyRes.items || [];
      if (items.length === 0) {
        setAnalysisError("No mood logs found for the last 7 days. Try logging a check-in first.");
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

  const handleChatWithAria = () => {
    if (!analysisData) return;
    const chatPrompt = `Let's discuss my weekly mood analysis. ARIA noticed: "${analysisData.analysis}" and the pattern: "${analysisData.pattern}". How can I work on the suggestion: "${analysisData.suggestion}"?`;
    localStorage.setItem('mc_aria_context', chatPrompt);
    navigate('/aria');
  };

  const handleSave = async () => {
    if (selectedMood === null) {
      setError('Please select a mood level.');
      return;
    }
    setError('');
    setSaving(true);
    try {
      await moodApi.log(MOOD_TO_LEVEL[selectedMood], feelings, notes);
      setSaved(true);
      // Reset after 2s
      setTimeout(() => {
        setSaved(false);
        setSelectedMood(null);
        setFeelings([]);
        setNotes('');
      }, 2000);
    } catch (err) {
      console.error('Mood save failed', err);
      setError(err instanceof Error ? err.message : 'Failed to save check-in');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-4">CHECK IN</div>
        <h1 className="text-3xl font-light text-text mb-2">Mood Tracker</h1>
      </div>

      {/* Success banner */}
      {saved && (
        <div className="bg-green/10 border border-green/30 text-green text-sm rounded-[12px] px-4 py-3">
          ✓ Check-in saved successfully!
        </div>
      )}
      {error && (
        <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3">
          {error}
        </div>
      )}

      {/* Current mood */}
      <section className="space-y-4">
        <h2 className="text-base font-medium text-text">How are you feeling right now?</h2>
        <div className="flex gap-3">
          {[1, 2, 3, 4, 5].map((mood) => (
            <button
              key={mood}
              onClick={() => setSelectedMood(mood)}
              className={`w-14 h-14 rounded-full flex items-center justify-center text-2xl transition-all ${
                selectedMood === mood
                  ? 'bg-accent/20 border-2 border-accent scale-110'
                  : 'bg-bg3 border border-border hover:bg-bg4'
              }`}
            >
              {MOOD_EMOJIS[mood]}
            </button>
          ))}
        </div>
      </section>

      {/* Feelings */}
      <section className="space-y-4">
        <div>
          <h2 className="text-base font-medium text-text mb-1">What are you feeling?</h2>
          <p className="text-xs text-text3">Select all that apply</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {allFeelings.map((feeling) => (
            <button
              key={feeling}
              onClick={() => toggleFeeling(feeling)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                feelings.includes(feeling)
                  ? 'bg-accent/20 border border-accent text-accent'
                  : 'bg-bg3 border border-border text-text2 hover:bg-bg4'
              }`}
            >
              {feeling}
            </button>
          ))}
        </div>
      </section>

      {/* Notes */}
      <section className="space-y-4">
        <h2 className="text-base font-medium text-text">Any notes?</h2>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="What's going on your mind..."
          className="w-full bg-bg2 border border-border rounded-[14px] px-4 py-3 text-sm text-text placeholder:text-text3 resize-none focus:outline-none focus:border-border2 min-h-32"
        />
        <div className="text-xs text-text3">
          {notes.length} characters · {notes.split(/\s+/).filter(Boolean).length} words
        </div>
      </section>

      {/* AI Insight */}
      <section className="space-y-3">
        <div className="text-xs text-accent tracking-[0.1em] uppercase">AI COMPANION</div>
        <div className="bg-bg2 border border-border rounded-[20px] px-6 py-5">
          <h3 className="text-base font-medium text-text mb-3">AI Insight</h3>
          
          {analyzing && (
            <div className="flex flex-col items-center justify-center py-6 space-y-3">
              <Loader2 className="w-6 h-6 text-accent animate-spin" />
              <span className="text-xs text-text3">Analyzing your mood patterns...</span>
            </div>
          )}

          {analysisError && !analyzing && (
            <p className="text-sm text-rose mb-4">{analysisError}</p>
          )}

          {!analysisData && !analyzing && (
            <>
              <p className="text-sm text-text2 mb-4">
                After logging, ARIA can help you notice patterns in how you feel across the week.
              </p>
              <button
                onClick={handleAnalyze}
                className="px-5 py-2.5 bg-accent-glow border border-accent/25 text-accent rounded-full text-sm font-medium hover:bg-accent/20 transition-all"
              >
                Analyze Trends
              </button>
            </>
          )}

          {analysisData && !analyzing && (
            <div className="space-y-4 animate-fadeIn">
              <h4 className="text-sm font-medium text-accent">Here's what I noticed about your week...</h4>
              <div className="space-y-3.5 pt-1">
                <div>
                  <div className="text-[10px] tracking-wider uppercase text-text3 mb-1">Weekly Observation</div>
                  <p className="text-sm text-text2 leading-relaxed italic font-[family-name:var(--font-serif)]">
                    "{analysisData.analysis}"
                  </p>
                </div>
                <div className="border-t border-border/40 pt-3">
                  <div className="text-[10px] tracking-wider uppercase text-text3 mb-1">Key Pattern</div>
                  <p className="text-sm text-text2 leading-relaxed">{analysisData.pattern}</p>
                </div>
                <div className="border-t border-border/40 pt-3">
                  <div className="text-[10px] tracking-wider uppercase text-text3 mb-1">Gentle Suggestion</div>
                  <p className="text-sm text-text2 leading-relaxed">{analysisData.suggestion}</p>
                </div>
                <div className="border-t border-border/40 pt-3.5 flex items-center justify-between gap-3 flex-wrap">
                  <span className="text-xs text-text3">
                    Mood Trend: <span className="font-semibold text-accent capitalize">{analysisData.mood_trend}</span>
                  </span>
                  <button
                    onClick={handleChatWithAria}
                    className="px-4 py-2 bg-gradient-to-r from-accent2 to-teal text-white rounded-full text-xs font-medium hover:opacity-90 transition-all"
                  >
                    Chat with ARIA about this
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Submit */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving || selectedMood === null}
          className="px-6 py-3 bg-accent text-white rounded-lg font-medium text-sm hover:bg-accent2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving…' : 'Save Check-In'}
        </button>
        <button
          onClick={() => { setSelectedMood(null); setFeelings([]); setNotes(''); setError(''); }}
          className="px-6 py-3 bg-bg3 border border-border text-text2 rounded-lg font-medium text-sm hover:bg-bg4 transition-all"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
