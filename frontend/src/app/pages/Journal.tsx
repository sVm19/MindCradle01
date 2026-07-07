import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Play, Pause, Loader2, BookOpen, Music, Lock } from 'lucide-react';
import { sanitizeForInput } from '@/lib/sanitize';
import { journal as journalApi, ai as aiApi, mood as moodApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import GuestGate from '@/app/components/GuestGate';
import { validateJournal } from '@/lib/validation';

const TODAY_PROMPT = "What felt lighter today than it did a week ago?";

export default function Journal() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [journalText, setJournalText] = useState('');
  const [journalError, setJournalError] = useState('');
  const [activeTrack, setActiveTrack] = useState<number | null>(null);

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState('');

  const [todayMood, setTodayMood] = useState<string | null>(null);
  const [yesterdayMood, setYesterdayMood] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    moodApi.history('7d').then((res) => {
      const items = res.items || [];
      const todayStr = new Date().toISOString().slice(0, 10);
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const yesterdayStr = yesterday.toISOString().slice(0, 10);

      const todayItem = items.find(item => item.created.slice(0, 10) === todayStr);
      if (todayItem) {
        setTodayMood(todayItem.emotions?.[0] || 'Neutral');
      } else {
        const yesterdayItem = items.find(item => item.created.slice(0, 10) === yesterdayStr);
        if (yesterdayItem) {
          setYesterdayMood(yesterdayItem.emotions?.[0] || 'Neutral');
        }
      }
    }).catch(() => {});
  }, [user]);

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
    if (!validateJournal(journalText)) {
      setSaveError('Journal entry must be between 1 and 5000 characters.');
      return;
    }
    setSaving(true);
    setSaveError('');
    try {
      await journalApi.save(TODAY_PROMPT, journalText);
      
      aiApi.trackInteraction({
        event_type: 'input_submit',
        page_path: '/journal',
        input_placeholder: 'journal_entry_content',
        input_length: journalText.length,
        metadata: {
          word_count: journalText.split(/\s+/).filter(Boolean).length,
          has_reflection: false,
        }
      }).catch((err) => console.error('Failed to log journal telemetry:', err));

      setSaved(true);
      setJournalError('');
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save entry');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveWithReflection = async () => {
    if (!validateJournal(journalText) || !reflectionData) {
      setSaveError('Journal entry must be between 1 and 5000 characters.');
      return;
    }
    setSaving(true);
    setSaveError('');
    try {
      const formattedReflection = `Reflection: ${reflectionData.reflection}\nKey Themes: ${reflectionData.themes.join(', ')}\nEmotional Tone: ${reflectionData.emotional_tone}`;
      await journalApi.save(TODAY_PROMPT, journalText, formattedReflection);

      aiApi.trackInteraction({
        event_type: 'input_submit',
        page_path: '/journal',
        input_placeholder: 'journal_entry_content',
        input_length: journalText.length,
        metadata: {
          word_count: journalText.split(/\s+/).filter(Boolean).length,
          has_reflection: true,
        }
      }).catch((err) => console.error('Failed to log journal telemetry:', err));

      setSaved(true);
      setJournalError('');
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save entry');
    } finally {
      setSaving(false);
    }
  };

  const handleReflect = async () => {
    if (wordCount <= 10) return;
    if (journalText.length > 5000) {
      setReflectError('Journal entry cannot exceed 5000 characters.');
      return;
    }
    setReflecting(true);
    setReflectError('');
    setReflectionData(null);
    try {
      const res = await aiApi.reflect(journalText, user?.userId || '');
      setReflectionData(res);
      if (res && res.linguistic_shift) {
        localStorage.setItem('mc_linguistic_shift', res.linguistic_shift);
      }
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
        title="Guided Reflection Journal"
        description="Clear your thoughts. Write daily reflections with relaxing ambient sounds, and receive immediate insights from ARIA."
        icon={<BookOpen className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  if (saved) {
    return (
      <div className="space-y-8 animate-fadeIn flex flex-col items-center justify-center min-h-[50vh] text-center">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500 to-accent flex items-center justify-center text-4xl text-white">
          ✍
        </div>
        <div>
          <h1 className="text-2xl font-light text-text mb-2">Journal Entry Saved</h1>
          <p className="text-sm text-text2 max-w-md mx-auto mb-6">Your daily reflection is safely locked. Now, let's explore deeper patterns with your AI companion, ARIA.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-center">
          <button
            onClick={() => navigate('/aria')}
            className="px-6 py-3 bg-accent text-white rounded-full font-semibold text-sm hover:bg-accent2 transition-all shadow-md smooth-hover-btn"
          >
            Chat with ARIA →
          </button>
          <button
            onClick={() => {
              setSaved(false);
              setJournalText('');
              setReflectionData(null);
              setSaveError('');
              setReflectError('');
              setJournalError('');
            }}
            className="px-5 py-3 bg-bg3 border border-border text-text3 hover:text-text rounded-full font-medium text-sm hover:bg-bg4 transition-all smooth-hover-btn"
          >
            Write Another Entry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-4">REFLECTION</div>
        <h1 className="text-3xl font-light text-text mb-2">Reflection Journal</h1>
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
        <div className="text-xs text-accent tracking-[0.1em] uppercase">Ambient Soundscape</div>
        <div className="text-sm text-text2 mb-3">Select a calming soundscape to help you focus while writing</div>

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
        <div className="text-sm text-text2 italic">Write your thoughts below...</div>
        <textarea
          value={journalText}
          onChange={(e) => {
            const val = sanitizeForInput(e.target.value);
            setJournalText(val);
            if (val.length > 5000) {
              setJournalError('Journal entry cannot exceed 5000 characters');
            } else {
              setJournalError('');
            }
          }}
          onBlur={() => {
            if (journalText.length > 5000) {
              setJournalError('Journal entry cannot exceed 5000 characters');
            } else if (journalText.trim().length === 0) {
              setJournalError('Journal entry cannot be empty');
            } else {
              setJournalError('');
            }
          }}
          placeholder={
            todayMood 
              ? `You logged feeling '${todayMood}' today. Elaborate on what is contributing to that feeling, or reflect on your day here...` 
              : yesterdayMood 
                ? `Yesterday you logged feeling '${yesterdayMood}'. Write down your reflections for today...` 
                : "Write down anything on your mind. Aim for at least 11 words to get ARIA's reflection insights..."
          }
          className={`w-full bg-bg2 border rounded-[20px] px-5 py-4 text-sm text-text placeholder:text-text3 resize-none focus:outline-none min-h-64 transition-colors ${
            journalError ? 'border-rose focus:border-rose' : 'border-border focus:border-accent/30'
          }`}
        />
        {journalError && <span className="text-xs text-rose mt-1 block">{journalError}</span>}
        <div className="flex items-center justify-between text-xs text-text3">
          <div>{charCount} characters · {wordCount} words</div>
          {saved && <div className="text-green">✓ Entry saved</div>}
          {saveError && <div className="text-rose">{saveError}</div>}
        </div>
      </section>

      {/* Actions */}
      <div className="flex flex-wrap gap-3 pt-4">
        {reflectionData ? (
          <button
            onClick={handleSaveWithReflection}
            disabled={saving || !journalText.trim() || journalError !== ''}
            className="px-6 py-3 bg-gradient-to-r from-accent2 to-teal text-white rounded-full font-semibold text-sm hover:opacity-90 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
          >
            {saving ? 'Saving…' : 'Save Entry & AI Insights'}
          </button>
        ) : null}
        <button
          onClick={handleSave}
          disabled={saving || !journalText.trim() || journalError !== ''}
          className={`px-6 py-3 rounded-full font-semibold text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
            reflectionData
              ? 'bg-bg3 border border-border text-text2 hover:bg-bg4'
              : 'bg-accent text-white hover:bg-accent2 shadow-md'
          }`}
        >
          {saving ? 'Saving…' : reflectionData ? 'Save Reflection Only' : 'Save Entry'}
        </button>
        <button
          onClick={() => {
            setJournalText('');
            setReflectionData(null);
            setSaveError('');
            setReflectError('');
            setJournalError('');
          }}
          className="px-6 py-3 bg-bg3 border border-border text-text2 rounded-full font-medium text-sm hover:bg-bg4 transition-all"
        >
          Discard
        </button>
      </div>

      {/* AI Reflection */}
      <section className="space-y-3 border-t border-border/45 pt-6">
        <div className="text-xs text-accent tracking-[0.1em] uppercase">Reflections by ARIA</div>
        <div className="bg-bg2 border border-border rounded-[20px] px-6 py-5">
          {reflecting && (
            <div className="flex flex-col items-center justify-center py-6 space-y-3">
              <Loader2 className="w-6 h-6 text-accent animate-spin" />
              <span className="text-xs text-text3">ARIA is synthesizing your reflection…</span>
            </div>
          )}

          {reflectError && !reflecting && (
            <p className="text-sm text-rose mb-4">{reflectError}</p>
          )}

          {!reflectionData && !reflecting && !reflectError && (
            <p className="text-sm text-text2 mb-4">
              {wordCount === 0 ? (
                <>Start writing above. Once you reach 11 words, ARIA will analyze your entry's key themes and emotional tone.</>
              ) : (
                <>You've written {wordCount} words. Write {11 - wordCount > 0 ? 11 - wordCount : 0} more words to unlock AI reflection themes.</>
              )}
            </p>
          )}

          {reflectionData && !reflecting && (
            <div className="space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-xs text-white">✦</div>
                  <span className="text-sm font-medium text-text">ARIA's Insights</span>
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
                disabled={wordCount <= 10 || reflecting || journalError !== ''}
                className="px-5 py-2.5 bg-accent-glow border border-accent/25 text-accent rounded-full text-sm font-medium hover:bg-accent/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Generate AI Insights
              </button>
              {wordCount <= 10 && (
                <span className="text-xs text-text3 ml-3">Write at least 11 words to get reflection ({wordCount}/11)</span>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
