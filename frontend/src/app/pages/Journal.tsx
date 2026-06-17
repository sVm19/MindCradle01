import { useState } from 'react';
import { Play, Pause, Loader2, BookOpen, Music, Lock } from 'lucide-react';
import { journal as journalApi, ai as aiApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import GuestGate from '@/app/components/GuestGate';

const TODAY_PROMPT = "What felt lighter today than it did a week ago?";

export default function Journal() {
  const { user } = useAuth();
  const [journalText, setJournalText] = useState('');
  const [activeTrack, setActiveTrack] = useState<number | null>(null);

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState('');

  const [reflecting, setReflecting] = useState(false);
  const [reflectionData, setReflectionData] = useState<{
    reflection: string;
    themes: string[];
    emotional_tone: string;
  } | null>(null);
  const [reflectError, setReflectError] = useState('');

  const ambientTracks = [
    { name: 'Rain on Glass', duration: '15:30' },
    { name: 'Forest Morning', duration: '18:45' },
    { name: 'Ocean Waves', duration: '20:15' },
  ];

  const togglePlay = (index: number) => {
    setActiveTrack(activeTrack === index ? null : index);
  };

  const wordCount = journalText.split(/\s+/).filter(Boolean).length;
  const charCount = journalText.length;

  const handleSave = async () => {
    if (!journalText.trim()) return;
    setSaving(true);
    setSaveError('');
    try {
      await journalApi.save(TODAY_PROMPT, journalText);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save entry');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveWithReflection = async () => {
    if (!journalText.trim() || !reflectionData) return;
    setSaving(true);
    setSaveError('');
    try {
      const formattedReflection = `Reflection: ${reflectionData.reflection}\nKey Themes: ${reflectionData.themes.join(', ')}\nEmotional Tone: ${reflectionData.emotional_tone}`;
      await journalApi.save(TODAY_PROMPT, journalText, formattedReflection);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save entry');
    } finally {
      setSaving(false);
    }
  };

  const handleReflect = async () => {
    if (wordCount <= 10) return;
    setReflecting(true);
    setReflectError('');
    setReflectionData(null);
    try {
      const res = await aiApi.reflect(journalText, user?.userId || '');
      setReflectionData(res);
    } catch (err) {
      setReflectError("Couldn't get reflection, try again");
    } finally {
      setReflecting(false);
    }
  };
  const handleClearReflection = () => {
    setReflectionData(null);
    setReflectError('');
  };

  if (!user) {
    return (
      <GuestGate
        title="Guided Journal"
        description="Release your thoughts. Save daily entries, play calming ambient loops, and ask ARIA for insightful reflections."
        icon={<BookOpen className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-4">REFLECTION</div>
        <h1 className="text-3xl font-light text-text mb-2">Guided Journal</h1>
      </div>

      {/* Prompt */}
      <section className="bg-bg2 border border-border rounded-[20px] px-6 py-5">
        <div className="flex items-start gap-3 mb-3">
          <span className="text-lg flex items-center text-accent mt-0.5"><BookOpen size={18} /></span>
          <div>
            <div className="text-xs text-accent tracking-wider uppercase mb-1">TODAY'S PROMPT</div>
            <h2 className="text-base font-medium text-text">{TODAY_PROMPT}</h2>
          </div>
        </div>
      </section>

      {/* Ambient Music */}
      <section className="space-y-3">
        <div className="text-xs text-accent tracking-[0.1em] uppercase">AMBIENT LAYER</div>
        <div className="text-sm text-text2 mb-3">Play ambient while you write</div>

        <div className="space-y-2">
          {ambientTracks.map((track, index) => (
            <div key={index} className="bg-bg2 border border-border rounded-[14px] px-4 py-3 flex items-center gap-4">
              <button
                onClick={() => togglePlay(index)}
                className="w-10 h-10 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center text-accent hover:bg-accent/30 transition-all"
              >
                {activeTrack === index ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
              </button>

              <div className="flex-1">
                <div className="text-sm text-text mb-1">{track.name}</div>
                <div className="w-full bg-bg4 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent2 to-teal rounded-full transition-all"
                    style={{ width: activeTrack === index ? '35%' : '0%' }}
                  />
                </div>
              </div>

              <div className="text-xs text-text3 flex items-center gap-2">
                <Music size={14} className="text-text3" />
                <span>{track.duration}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Writing Area */}
      <section className="space-y-3">
        <div className="text-sm text-text2 italic">Let your thoughts flow freely...</div>
        <textarea
          value={journalText}
          onChange={(e) => setJournalText(e.target.value)}
          placeholder="Start writing..."
          className="w-full bg-bg2 border border-border rounded-[20px] px-5 py-4 text-sm text-text placeholder:text-text3 resize-none focus:outline-none focus:border-accent/30 min-h-64"
        />
        <div className="flex items-center justify-between text-xs text-text3">
          <div>{charCount} characters · {wordCount} words</div>
          {saved && <div className="text-green">✓ Entry saved</div>}
          {saveError && <div className="text-rose">{saveError}</div>}
        </div>
      </section>

      {/* AI Reflection */}
      <section className="space-y-3">
        <div className="text-xs text-accent tracking-[0.1em] uppercase">AI REFLECTION</div>
        <div className="bg-bg2 border border-border rounded-[20px] px-6 py-5">
          {reflecting && (
            <div className="flex flex-col items-center justify-center py-6 space-y-3">
              <Loader2 className="w-6 h-6 text-accent animate-spin" />
              <span className="text-xs text-text3">ARIA is analyzing your thoughts…</span>
            </div>
          )}

          {reflectError && !reflecting && (
            <p className="text-sm text-rose mb-4">{reflectError}</p>
          )}

          {!reflectionData && !reflecting && !reflectError && (
            <p className="text-sm text-text2 mb-4">
              After writing, ARIA can help you notice patterns or ask gentle questions.
            </p>
          )}

          {reflectionData && !reflecting && (
            <div className="space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-xs text-white">✦</div>
                  <span className="text-sm font-medium text-text">ARIA's Reflection</span>
                </div>
                <button
                  onClick={handleClearReflection}
                  className="text-xs text-text3 hover:text-text hover:underline transition-colors"
                >
                  Clear Reflection
                </button>
              </div>

              <div className="space-y-4 pt-2">
                <div>
                  <p className="text-sm text-text2 leading-relaxed font-[family-name:var(--font-serif)] italic">
                    "{reflectionData.reflection}"
                  </p>
                </div>

                <div className="border-t border-border/40 pt-3">
                  <div className="text-[10px] tracking-wider uppercase text-text3 mb-1.5">Key Themes</div>
                  <div className="flex flex-wrap gap-2">
                    {reflectionData.themes.map((theme, i) => (
                      <span key={i} className="px-2.5 py-1 text-xs rounded-full bg-accent-glow text-accent border border-accent/20">
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="border-t border-border/40 pt-3">
                  <div className="text-[10px] tracking-wider uppercase text-text3 mb-1">Emotional Tone</div>
                  <p className="text-sm text-text2 leading-relaxed">{reflectionData.emotional_tone}</p>
                </div>
              </div>
            </div>
          )}

          {!reflectionData && !reflecting && (
            <div className="mt-4">
              <button
                onClick={handleReflect}
                disabled={wordCount <= 10 || reflecting}
                className="px-5 py-2.5 bg-accent-glow border border-accent/25 text-accent rounded-full text-sm font-medium hover:bg-accent/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Get Reflection
              </button>
              {wordCount <= 10 && (
                <span className="text-xs text-text3 ml-3">Write at least 11 words to get reflection ({wordCount}/11)</span>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Actions */}
      <div className="flex flex-wrap gap-3 pt-4">
        {reflectionData ? (
          <button
            onClick={handleSaveWithReflection}
            disabled={saving || !journalText.trim()}
            className="px-6 py-3 bg-gradient-to-r from-accent2 to-teal text-white rounded-lg font-medium text-sm hover:opacity-90 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving…' : 'Save Entry with Reflection'}
          </button>
        ) : null}
        <button
          onClick={handleSave}
          disabled={saving || !journalText.trim()}
          className={`px-6 py-3 rounded-lg font-medium text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
            reflectionData
              ? 'bg-bg3 border border-border text-text2 hover:bg-bg4'
              : 'bg-accent text-white hover:bg-accent2'
          }`}
        >
          {saving ? 'Saving…' : reflectionData ? 'Save Entry Only' : 'Save Entry'}
        </button>
        <button
          onClick={() => {
            setJournalText('');
            setReflectionData(null);
            setSaveError('');
            setReflectError('');
          }}
          className="px-6 py-3 bg-bg3 border border-border text-text2 rounded-lg font-medium text-sm hover:bg-bg4 transition-all"
        >
          Discard
        </button>
      </div>
    </div>
  );
}
