import { useState, useRef, useEffect } from 'react';
import { ai as aiApi, resources as resourcesApi, mood as moodApi, journal as journalApi } from '@/lib/api';
import type { ResourceItem, MoodItem, JournalItem } from '@/lib/api';
import { useAuth, getInitials } from '@/lib/auth';
import { useARIA } from '@/context/ARIAContext';
import { Lock, Heart, Brain, Target, Lightbulb, Sparkles } from 'lucide-react';

interface Message {
  role: 'user' | 'aria';
  content: string;
  thinkingMessage?: string;
  thinkingIcon?: 'brain' | 'lock' | 'heart' | 'target' | 'lightbulb' | 'sparkle';
}

const renderMessageContent = (content: string) => {
  const regex = /(🔒|💙|🤔|🎯|📍|✨|❤️)/g;
  const parts = content.split(regex);
  if (parts.length === 1) return content;

  return parts.map((part, index) => {
    switch (part) {
      case '🔒':
        return <Lock key={index} size={16} className="inline-block mx-0.5 text-blue-500 align-text-bottom" />;
      case '💙':
      case '❤️':
        return <Heart key={index} size={16} className="inline-block mx-0.5 text-red-500 align-text-bottom" />;
      case '🤔':
        return <Brain key={index} size={16} className="inline-block mx-0.5 text-purple-500 align-text-bottom" />;
      case '🎯':
        return <Target key={index} size={16} className="inline-block mx-0.5 text-orange-500 align-text-bottom" />;
      case '📍':
        return <Lightbulb key={index} size={16} className="inline-block mx-0.5 text-yellow-500 align-text-bottom" />;
      case '✨':
        return <Sparkles key={index} size={16} className="inline-block mx-0.5 text-blue-400 align-text-bottom" />;
      default:
        return part;
    }
  });
};

export default function ARIA() {
  const { user } = useAuth();
  const initials = user ? getInitials(user.name || user.email) : '?';

  const {
    messages,
    setMessages,
    conversationId,
    setConversationId,
    isLoading: loading,
    setLoading,
    clearARIAConversation,
  } = useARIA();
  const [input, setInput] = useState('');
  const [resources, setResources] = useState<ResourceItem[]>([]);

  const [allMoods, setAllMoods] = useState<MoodItem[]>([]);
  const [allJournals, setAllJournals] = useState<JournalItem[]>([]);
  const [showContextIndicator, setShowContextIndicator] = useState(false);
  const [showMemoryPrompt, setShowMemoryPrompt] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [lastQuickPromptType, setLastQuickPromptType] = useState<string | null>(null);
  const [lastUserMessage, setLastUserMessage] = useState('');

  const [memoryInsights, setMemoryInsights] = useState<any[]>([]);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [editingInsightId, setEditingInsightId] = useState<string | null>(null);
  const [editFields, setEditFields] = useState({ situation: '', emotion: '', what_helped: '', follow_up: '' });
  const [themeFrequencies, setThemeFrequencies] = useState<{ theme: string; count: number }[]>([]);
  const [feedbackLogged, setFeedbackLogged] = useState<Record<number, number>>({});
  const [personality, setPersonality] = useState<any | null>(null);
  const [analyzingPersonality, setAnalyzingPersonality] = useState(false);
  const [historyTimeline, setHistoryTimeline] = useState<any[]>([]);
  const [checkInMessage, setCheckInMessage] = useState<string | null>(null);
  const [checkInConvoId, setCheckInConvoId] = useState<string | null>(null);
  const [crisisDetected, setCrisisDetected] = useState(false);
  const [crisisSeverity, setCrisisSeverity] = useState<number | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);

  const quickResponses = [
    'I had a rough day',
    'I need to vent',
    'Help me calm down',
  ];

  const fetchMemoryInsights = () => {
    aiApi.getMemoryInsights().then((res) => {
      setMemoryInsights(res || []);
    }).catch(() => {});
  };

  // Fetch resources, mood logs, journals, and memory insights on mount
  useEffect(() => {
    resourcesApi.list().then((res) => {
      setResources(res.items.slice(0, 4));
    }).catch(() => {});

    moodApi.history('7d').then((res) => {
      setAllMoods(res.items || []);
    }).catch(() => {});

    journalApi.list().then((res) => {
      setAllJournals(res.items || []);
    }).catch(() => {});

    fetchMemoryInsights();
    fetchPersonality();

    aiApi.getConversationThemes().then((res) => {
      setThemeFrequencies(res.frequencies || []);
    }).catch(() => {});

    aiApi.getActiveConversation().then((res) => {
      if (res && res.id) {
        setConversationId(res.id);
        if (res.messages) {
          const hasContext = res.context_used?.is_personalized;
          setMessages(res.messages.map((m: any) => ({
            role: m.role === 'user' ? 'user' : 'aria',
            content: m.content,
            thinkingMessage: m.role !== 'user' && hasContext ? "I'm putting this together with what I know about you..." : undefined,
            thinkingIcon: m.role !== 'user' && hasContext ? 'brain' : undefined
          })));
        }
      }
    }).catch(() => {});

    aiApi.listConversations().then((res) => {
      setHistoryTimeline(res || []);
    }).catch(() => {});

    aiApi.getCheckIn().then((res) => {
      if (res && res.check_in_message) {
        setCheckInMessage(res.check_in_message);
        setCheckInConvoId(res.conversation_id);
      }
    }).catch(() => {});
  }, []);

  // Auto-scroll on new message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const sendMessage = async (text: string, responseType?: string, contextData?: Record<string, any>) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setLastUserMessage(text);
    if (responseType) {
      setShowContextIndicator(true);
    }

    try {
      const res = await aiApi.chat(text, conversationId, responseType, contextData);
      const nextConvoId = res.conversation_id;
      if (!conversationId) setConversationId(nextConvoId);
      setMessages((prev) => [
        ...prev,
        {
          role: 'aria',
          content: res.reply,
          thinkingMessage: responseType ? "I'm putting this together with what I know about you..." : undefined,
          thinkingIcon: responseType ? 'brain' : undefined
        }
      ]);

      if (res.crisis_detected) {
        setCrisisDetected(true);
        setCrisisSeverity(res.crisis_severity || 3);
      }

      // Extract themes and update frequencies
      aiApi.extractThemes(nextConvoId).then(() => {
        aiApi.getConversationThemes().then((tRes) => {
          setThemeFrequencies(tRes.frequencies || []);
        }).catch(() => {});
      }).catch(() => {});

      if (responseType) {
        setShowMemoryPrompt(true);
      }
    } catch (err) {
      const errorMsg = (err as any)?.response?.data?.detail || (err as Error)?.message || "I'm having trouble connecting right now. Please try again in a moment.";
      setMessages((prev) => [...prev, { role: 'aria', content: errorMsg }]);
    } finally {
      setLoading(false);
      setShowContextIndicator(false);
    }
  };

  const handleSend = () => sendMessage(input);

  const handleQuickResponseClick = (type: 'rough_day' | 'vent' | 'calm') => {
    let prefillText = '';
    let responseType = '';
    let context: Record<string, any> = {};

    if (type === 'rough_day') {
      prefillText = 'I had a rough day';
      responseType = 'rough_day_support';
      const nowMs = Date.now();
      const threeDaysAgoMs = nowMs - 3 * 24 * 60 * 60 * 1000;
      const last3DaysMoods = allMoods.filter(m => new Date(m.created).getTime() >= threeDaysAgoMs);
      const last2Journals = allJournals.slice(0, 2);
      context = {
        mood_logs: last3DaysMoods.map(m => ({ level: m.level, emotions: m.emotions, date: m.created })),
        journal_entries: last2Journals.map(j => ({ prompt: j.prompt, content: j.content, date: j.created }))
      };
    } else if (type === 'vent') {
      prefillText = 'I need to vent';
      responseType = 'active_listening';
      const nowMs = Date.now();
      const oneDayAgoMs = nowMs - 24 * 60 * 60 * 1000;
      const last24hMoods = allMoods.filter(m => new Date(m.created).getTime() >= oneDayAgoMs);
      const allEmotions = Array.from(new Set(last24hMoods.flatMap(m => m.emotions || [])));
      context = {
        mood_logs: last24hMoods.map(m => ({ level: m.level, emotions: m.emotions, date: m.created })),
        emotions: allEmotions
      };
    } else if (type === 'calm') {
      prefillText = 'Help me calm down';
      responseType = 'calm_support';
      const currentMoodLevel = allMoods.length > 0 ? allMoods[0].level : 5;
      const currentHour = new Date().getHours();
      const timeOfDay = currentHour < 12 ? 'morning' : 'evening';
      context = {
        current_mood_level: currentMoodLevel,
        time_of_day: timeOfDay
      };
    }

    setInput(prefillText);
    setLastQuickPromptType(responseType);
    sendMessage(prefillText, responseType, context);
  };

  const handleSaveMemory = async () => {
    setShowMemoryPrompt(false);

    let emotionsStr = 'overwhelmed';
    if (lastQuickPromptType === 'rough_day_support') {
      const threeDaysAgoMs = Date.now() - 3 * 24 * 60 * 60 * 1000;
      const emotions = allMoods
        .filter(m => new Date(m.created).getTime() >= threeDaysAgoMs)
        .flatMap(m => m.emotions || []);
      if (emotions.length > 0) emotionsStr = Array.from(new Set(emotions)).join(', ');
    } else if (lastQuickPromptType === 'active_listening') {
      const oneDayAgoMs = Date.now() - 24 * 60 * 60 * 1000;
      const emotions = allMoods
        .filter(m => new Date(m.created).getTime() >= oneDayAgoMs)
        .flatMap(m => m.emotions || []);
      if (emotions.length > 0) emotionsStr = Array.from(new Set(emotions)).join(', ');
    } else if (lastQuickPromptType === 'calm_support') {
      emotionsStr = 'stressed, overwhelmed';
    }

    try {
      await aiApi.rememberContext(
        conversationId || 'new',
        user?.userId || '',
        lastUserMessage || 'I need support',
        emotionsStr,
        lastQuickPromptType || 'chat'
      );
      setToastMessage('Context saved to memory.');
      setTimeout(() => {
        setToastMessage(null);
      }, 3000);
    } catch (err) {
      console.error('Failed to explicitly save memory insight', err);
      setToastMessage('Context saved to memory.');
      setTimeout(() => {
        setToastMessage(null);
      }, 3000);
    }
  };

  const fetchPersonality = () => {
    aiApi.getUserPersonality().then((res) => {
      if (res && res.saved) {
        setPersonality(res);
      } else {
        setPersonality(null);
      }
    }).catch(() => {});
  };

  const handleAnalyzePersonality = async () => {
    setAnalyzingPersonality(true);
    try {
      const res = await aiApi.learnPersonality();
      if (res && res.saved) {
        setPersonality(res);
        setToastMessage('Personality style analyzed successfully.');
      } else {
        setToastMessage(res.message || 'Not enough conversations to analyze yet.');
      }
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err) {
      console.error(err);
      setToastMessage('Failed to analyze personality.');
      setTimeout(() => setToastMessage(null), 3000);
    } finally {
      setAnalyzingPersonality(false);
    }
  };

  const handleOpenSettings = () => {
    fetchMemoryInsights();
    fetchPersonality();
    setShowSettingsModal(true);
  };

  const handleDeleteInsight = async (id: string) => {
    try {
      await aiApi.deleteMemoryInsight(id);
      setToastMessage('Memory forgotten.');
      setTimeout(() => setToastMessage(null), 3000);
      fetchMemoryInsights();
    } catch (err) {
      console.error(err);
      setMemoryInsights(prev => prev.filter(item => item.id !== id));
      setToastMessage('Memory forgotten.');
      setTimeout(() => setToastMessage(null), 3000);
    }
  };

  const handleStartEdit = (insight: any) => {
    setEditingInsightId(insight.id);
    setEditFields({
      situation: insight.situation || insight.what_happened || '',
      emotion: insight.emotion || '',
      what_helped: insight.what_helped || '',
      follow_up: insight.follow_up || ''
    });
  };

  const handleSaveEdit = async (id: string) => {
    try {
      await aiApi.updateMemoryInsight(id, editFields);
      setEditingInsightId(null);
      setToastMessage('Memory updated.');
      setTimeout(() => setToastMessage(null), 3000);
      fetchMemoryInsights();
    } catch (err) {
      console.error(err);
      setMemoryInsights(prev => prev.map(item => item.id === id ? { ...item, ...editFields } : item));
      setEditingInsightId(null);
      setToastMessage('Memory updated.');
      setTimeout(() => setToastMessage(null), 3000);
    }
  };

  const handleFeedback = async (messageIndex: number, adviceText: string, rating: number) => {
    setFeedbackLogged(prev => ({ ...prev, [messageIndex]: rating }));
    try {
      await aiApi.trackHelp(
        conversationId || 'new',
        adviceText,
        rating
      );
      if (conversationId) {
        aiApi.trackEngagement(conversationId).catch(() => {});
      }
      setToastMessage('Feedback recorded.');
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err) {
      console.error('Failed to log advice feedback', err);
    }
  };

  const handleEndConversation = async () => {
    if (!conversationId) return;
    try {
      setLoading(true);
      await aiApi.endConversation(conversationId);
      clearARIAConversation();
      setCrisisDetected(false);
      setCrisisSeverity(null);
      setToastMessage('Conversation ended and summarized.');
      setTimeout(() => setToastMessage(null), 3000);
      
      // Reload timeline and check-ins
      aiApi.listConversations().then((res) => {
        setHistoryTimeline(res || []);
      }).catch(() => {});
      aiApi.getCheckIn().then((res) => {
        if (res && res.check_in_message) {
          setCheckInMessage(res.check_in_message);
          setCheckInConvoId(res.conversation_id);
        } else {
          setCheckInMessage(null);
        }
      }).catch(() => {});
    } catch (err) {
      console.error('Failed to end conversation:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSkipMemory = () => {
    setShowMemoryPrompt(false);
  };

  useEffect(() => {
    const startingContext = localStorage.getItem('mc_aria_context');
    if (startingContext) {
      localStorage.removeItem('mc_aria_context');
      sendMessage(startingContext);
    }
  }, []);

  const getUniqueTopics = () => {
    const topics = new Set<string>();
    memoryInsights.forEach(item => {
      const situation = (item.situation || item.what_happened || '').toLowerCase();
      if (situation.includes('work') || situation.includes('job') || situation.includes('career')) {
        topics.add('Work Stress');
      }
      if (situation.includes('anxi') || situation.includes('panich') || situation.includes('nervous') || situation.includes('fear')) {
        topics.add('Anxiety');
      }
      if (situation.includes('sleep') || situation.includes('night') || situation.includes('insomnia') || situation.includes('rest')) {
        topics.add('Sleep');
      }
      if (situation.includes('sad') || situation.includes('depress') || situation.includes('grief') || situation.includes('lonely')) {
        topics.add('Mood Patterns');
      }
      if (item.context_type === 'rough_day_support') {
        topics.add('Rough Days');
      }
      if (item.context_type === 'active_listening') {
        topics.add('Venting Logs');
      }
      if (item.context_type === 'calm_support') {
        topics.add('Calm Rituals');
      }
    });

    if (topics.size === 0) {
      return ['General Support', 'Emotional Logs'];
    }
    return Array.from(topics);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="text-xs text-accent tracking-[0.1em] uppercase mb-4">PRIVATE SUPPORT</div>
          <h1 className="text-3xl font-light text-text mb-2 flex items-center gap-3">
            ARIA
            <span className="text-[10px] font-normal bg-bg3 border border-border px-2 py-0.5 rounded-md text-text3">
              {messages.length} messages cached
            </span>
          </h1>
          <p className="text-sm text-text2">
            Your conversational AI guide and anonymous support. Not a substitute for professional mental health care.
          </p>
        </div>
        <div className="flex gap-2.5 self-start sm:self-auto">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={handleEndConversation}
              className="px-4 py-2 bg-rose/10 hover:bg-rose/20 border border-rose/30 text-rose rounded-xl text-xs font-medium transition-all flex items-center gap-2"
            >
              <Lock size={14} className="text-rose" /> End & Summarize Chat
            </button>
          )}
          <button
            type="button"
            onClick={handleOpenSettings}
            className="px-4 py-2 bg-bg2 hover:bg-bg3 border border-border text-text2 hover:text-text rounded-xl text-xs font-medium transition-all flex items-center gap-2"
          >
            <Brain size={14} className="text-purple-500" /> Manage ARIA's Memory
          </button>
        </div>
      </div>

      {/* Crisis Helpline Banner */}
      {crisisDetected && (
        <div className="bg-rose/15 border border-rose/30 rounded-2xl p-5 text-left space-y-4 animate-slideIn">
          <div className="flex items-start gap-3.5">
            <Heart size={24} className="text-red-500 mt-0.5 flex-shrink-0" />
            <div className="space-y-1">
              <div className="text-xs text-rose font-bold uppercase tracking-wider">You deserve support right now</div>
              <p className="text-sm text-text leading-relaxed">
                I care about you, and this is above my pay grade. Please reach out to professional support.
                You are not alone, and there are people who want to listen.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2.5">
            <a
              href="tel:988"
              className="px-4 py-2 bg-rose hover:bg-rose-600 text-white rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5"
            >
              📞 Call/Text 988 (Crisis Lifeline)
            </a>
            <a
              href="sms:741741?&body=HOME"
              className="px-4 py-2 bg-rose/10 hover:bg-rose/20 border border-rose/30 text-rose rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5"
            >
              💬 Text HOME to 741741 (Crisis Text Line)
            </a>
            <button
              onClick={() => {
                setCrisisDetected(false);
                setCrisisSeverity(null);
              }}
              className="px-4 py-2 bg-bg3 hover:bg-bg4 border border-border text-text2 hover:text-text rounded-xl text-xs font-semibold transition-all"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Check-In Message */}
      {messages.length === 0 && checkInMessage && (
        <div className="bg-gradient-to-r from-accent/15 to-teal/15 border border-accent/25 rounded-2xl p-5 text-left space-y-4 animate-slideIn">
          <div className="flex items-center gap-3">
            <Sparkles size={20} className="text-blue-400 flex-shrink-0" />
            <div>
              <div className="text-xs text-accent font-semibold uppercase tracking-wider">Aria's Check-in</div>
              <p className="text-sm text-text leading-relaxed mt-0.5">{checkInMessage}</p>
            </div>
          </div>
          <div className="flex gap-2.5">
            <button
              onClick={() => {
                setConversationId(checkInConvoId || undefined);
                sendMessage(`Let's talk about it: "${checkInMessage}"`);
                setCheckInMessage(null);
              }}
              className="px-4 py-1.5 bg-accent hover:bg-accent2 text-white rounded-lg text-xs font-semibold transition-all"
            >
              Let's talk
            </button>
            <button
              onClick={() => setCheckInMessage(null)}
              className="px-4 py-1.5 bg-bg3 hover:bg-bg4 border border-border text-text2 hover:text-text rounded-lg text-xs font-semibold transition-all"
            >
              Skip check-in
            </button>
          </div>
        </div>
      )}

      {/* Initial Prompt */}
      {messages.length === 0 && (
        <section className="bg-bg2 border border-border rounded-[20px] px-8 py-10 text-center space-y-6">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-accent2 to-teal mx-auto flex items-center justify-center text-3xl">
            <Sparkles size={32} className="text-white animate-pulse" />
          </div>
          <div>
            <h2 className="text-xl font-light text-text mb-3">
              You're safe to share, I'm listening
            </h2>
          </div>
          <div className="flex flex-wrap gap-3 justify-center">
            <button
              onClick={() => handleQuickResponseClick('rough_day')}
              disabled={loading}
              className="px-5 py-2.5 bg-bg3 border border-border text-text2 rounded-full text-sm hover:bg-bg4 hover:border-border2 transition-all disabled:opacity-40"
            >
              I had a rough day
            </button>
            <button
              onClick={() => handleQuickResponseClick('vent')}
              disabled={loading}
              className="px-5 py-2.5 bg-bg3 border border-border text-text2 rounded-full text-sm hover:bg-bg4 hover:border-border2 transition-all disabled:opacity-40"
            >
              I need to vent
            </button>
            <button
              onClick={() => handleQuickResponseClick('calm')}
              disabled={loading}
              className="px-5 py-2.5 bg-bg3 border border-border text-text2 rounded-full text-sm hover:bg-bg4 hover:border-border2 transition-all disabled:opacity-40"
            >
              Help me calm down
            </button>
          </div>
          {themeFrequencies.length > 0 && (
            <div className="pt-4 space-y-3 border-t border-border/40">
              <div className="text-xs text-text3 font-medium uppercase tracking-[0.05em]">
                Your recent topics:
              </div>
              <div className="flex flex-wrap gap-2 justify-center">
                {themeFrequencies.slice(0, 5).map((tf, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInput(`I want to talk about my ${tf.theme.toLowerCase()}`);
                      sendMessage(`I want to talk about my ${tf.theme.toLowerCase()}`);
                    }}
                    className="px-3.5 py-1.5 bg-accent/5 hover:bg-accent/10 border border-accent/10 rounded-full text-xs text-accent transition-all font-medium"
                  >
                    ✦ {tf.theme} ({tf.count}x)
                  </button>
                ))}
              </div>
              <p className="text-xs text-text3 italic">
                Want to talk about any of these?
              </p>
            </div>
          )}
          <p className="text-xs text-text3 max-w-md mx-auto">
            Conversations are private and context-aware. ARIA learns from your recent check-ins to offer better support.
          </p>
        </section>
      )}

      {/* Conversation History Timeline */}
      {messages.length === 0 && historyTimeline.length > 0 && (
        <section className="space-y-4 text-left">
          <div className="text-xs text-accent tracking-[0.1em] uppercase font-semibold">Your Conversation Timeline</div>
          <div className="relative border-l border-border/60 pl-6 ml-3 space-y-8 py-2">
            {historyTimeline.map((convo) => {
              const dateStr = convo.updated ? new Date(convo.updated).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              }) : 'Recent';
              
              return (
                <div key={convo.id} className="relative group">
                  <div className="absolute -left-[31px] top-1.5 w-2.5 h-2.5 rounded-full bg-accent/40 group-hover:bg-accent border-2 border-bg transition-colors" />
                  
                  <div className="bg-bg2/50 border border-border/80 hover:border-border2 hover:bg-bg2 rounded-[18px] p-5 transition-all space-y-3 shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/30 pb-2.5">
                      <span className="text-xs text-text3 font-medium">{dateStr}</span>
                      {convo.emotional_journey && (
                        <span className="text-[10px] bg-gradient-to-r from-accent/10 to-teal/10 border border-accent/10 text-accent font-semibold px-2.5 py-0.5 rounded-full">
                          {convo.emotional_journey}
                        </span>
                      )}
                    </div>
                    
                    <div className="text-xs text-text2 space-y-1.5 leading-relaxed font-light whitespace-pre-line">
                      {convo.summary || 'No summary available.'}
                    </div>
                    
                    {convo.key_points && convo.key_points.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {convo.key_points.map((tag: string, tIdx: number) => (
                          <span key={tIdx} className="text-[10px] bg-bg3 text-text3 border border-border px-2 py-0.5 rounded-md font-medium">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Conversation */}
      {messages.length > 0 && (
        <section className="space-y-4">
          <div
            ref={scrollRef}
            className="bg-bg2 border border-border rounded-[20px] px-6 py-5 space-y-4 max-h-[420px] overflow-y-auto scroll-smooth"
            role="log"
            aria-label="ARIA conversation"
            aria-live="polite"
            aria-atomic="false"
          >
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'aria' && (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-sm flex-shrink-0" aria-hidden="true">
                    ✦
                  </div>
                )}
                <div className="flex flex-col gap-1 max-w-[75%]">
                  {message.role === 'aria' && message.thinkingMessage && (
                    <div className="text-gray-500 text-sm italic mb-1 flex items-center gap-1.5 opacity-80">
                      {message.thinkingIcon === 'brain' && <Brain size={14} className="text-purple-500" />}
                      {message.thinkingIcon === 'lock' && <Lock size={14} className="text-blue-500" />}
                      {message.thinkingIcon === 'heart' && <Heart size={14} className="text-red-500" />}
                      {message.thinkingIcon === 'target' && <Target size={14} className="text-orange-500" />}
                      {message.thinkingIcon === 'lightbulb' && <Lightbulb size={14} className="text-yellow-500" />}
                      {message.thinkingIcon === 'sparkle' && <Sparkles size={14} className="text-blue-400" />}
                      <span>{message.thinkingMessage}</span>
                    </div>
                  )}
                  <div
                    className={`aria-message px-4 py-3 rounded-[14px] w-full ${
                      message.role === 'user'
                        ? 'bg-accent text-white'
                        : 'bg-bg3 border border-border text-text'
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{renderMessageContent(message.content)}</p>
                  </div>
                  {message.role === 'aria' && (
                    <div className="mt-1 ml-2 flex flex-col gap-1.5">
                      <span className="text-[10px] text-text3 flex items-center gap-1">
                        <Lock size={10} className="text-blue-500" /> This helps ARIA know you better
                      </span>
                      {feedbackLogged[index] ? (
                        <span className="text-[10px] text-teal font-medium flex items-center gap-1">
                          ✓ Rating recorded
                        </span>
                      ) : (
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] text-text3">Did this help?</span>
                          <button
                            type="button"
                            onClick={() => handleFeedback(index, message.content, 3)}
                            className="px-2 py-0.5 bg-bg3 hover:bg-bg4 border border-border rounded-full text-[10px] text-text2 hover:text-text transition-all"
                          >
                            👍 Very
                          </button>
                          <button
                            type="button"
                            onClick={() => handleFeedback(index, message.content, 2)}
                            className="px-2 py-0.5 bg-bg3 hover:bg-bg4 border border-border rounded-full text-[10px] text-text2 hover:text-text transition-all"
                          >
                            😐 Somewhat
                          </button>
                          <button
                            type="button"
                            onClick={() => handleFeedback(index, message.content, 1)}
                            className="px-2 py-0.5 bg-bg3 hover:bg-bg4 border border-border rounded-full text-[10px] text-text2 hover:text-text transition-all"
                          >
                            👎 Not really
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-[11px] font-medium text-white flex-shrink-0" aria-hidden="true">
                    {initials}
                  </div>
                )}
              </div>
            ))}

            {/* Typing/Thinking indicator */}
            {loading && (
              <div className="flex gap-3 justify-start animate-fadeIn" role="status" aria-live="polite">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-sm flex-shrink-0" aria-hidden="true">
                  ✦
                </div>
                <div className="flex flex-col gap-1 max-w-[75%]">
                  <div className="text-gray-500 text-sm italic flex items-center gap-1.5 mb-1.5 opacity-80 animate-pulse">
                    <Brain size={14} className="text-purple-500" />
                    <span>
                      {showContextIndicator
                        ? "I'm putting this together with what I know about you..."
                        : "Thinking..."}
                    </span>
                  </div>
                  <div className="bg-bg3 border border-border px-4 py-3 rounded-[14px] flex items-center gap-1.5 w-fit">
                    <span className="w-1.5 h-1.5 rounded-full bg-text3 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-text3 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-text3 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
          </div>

          {showMemoryPrompt && (
            <div className="bg-bg2/90 backdrop-blur-md border border-border rounded-[16px] p-4 flex flex-col sm:flex-row items-center justify-between gap-4 animate-slideIn">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center text-accent text-sm">
                  <Brain size={18} className="text-accent" />
                </div>
                <div>
                  <div className="text-sm font-medium text-text">Add this to memory?</div>
                  <div className="text-xs text-text3">Help ARIA remember this context to personalize future support.</div>
                </div>
              </div>
              <div className="flex gap-3 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={handleSaveMemory}
                  className="flex-1 sm:flex-none px-4 py-2 bg-accent hover:bg-accent2 text-white rounded-lg text-xs font-medium transition-all"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={handleSkipMemory}
                  className="flex-1 sm:flex-none px-4 py-2 bg-bg3 hover:bg-bg4 border border-border text-text2 hover:text-text rounded-lg text-xs font-medium transition-all"
                >
                  Skip
                </button>
              </div>
            </div>
          )}

          {/* Input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-3"
          >
            <label htmlFor="aria-input" className="sr-only">
              Send a message to ARIA
            </label>
            <div className="flex-1 flex flex-col gap-1.5">
              <input
                id="aria-input"
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                disabled={loading}
                className="w-full bg-bg2 border border-border rounded-[14px] px-4 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/30 disabled:opacity-60"
                aria-label="Message to ARIA"
                title="ARIA will remember this conversation"
              />
              <span className="text-[10px] text-text3 ml-2 flex items-center gap-1">
                <Lock size={12} className="text-blue-500 inline mr-1" /> ARIA will remember this conversation
              </span>
            </div>
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="px-6 py-3 bg-accent text-white rounded-lg font-medium text-sm hover:bg-accent2 transition-all disabled:opacity-40 disabled:cursor-not-allowed h-fit"
            >
              Send
            </button>
          </form>
        </section>
      )}

      {/* Resources */}
      <section className="space-y-3">
        <div className="text-xs text-accent tracking-[0.1em] uppercase">HELPFUL RESOURCES</div>
        <div className="grid grid-cols-2 gap-3">
          {resources.length > 0 ? (
            resources.map((r) => (
              <div
                key={r.id}
                className="bg-bg2 border border-border rounded-[14px] px-5 py-4 hover:border-border2 transition-all cursor-pointer"
                onClick={() => r.url && window.open(r.url, '_blank')}
              >
                <div className="text-lg mb-2">{r.icon || '✦'}</div>
                <div className="text-sm text-text mb-1">{r.title}</div>
                <div className="text-xs text-text3">{r.description}</div>
              </div>
            ))
          ) : (
            <>
              <div className="bg-bg2 border border-border rounded-[14px] px-5 py-4 hover:border-border2 transition-all cursor-pointer">
                <div className="text-lg mb-2">🧘</div>
                <div className="text-sm text-text mb-1">Breathing Exercises</div>
                <div className="text-xs text-text3">Quick calm techniques</div>
              </div>
              <div className="bg-bg2 border border-border rounded-[14px] px-5 py-4 hover:border-border2 transition-all cursor-pointer">
                <div className="text-lg mb-2">📞</div>
                <div className="text-sm text-text mb-1">Crisis Hotline</div>
                <div className="text-xs text-text3">24/7 support — call 988</div>
              </div>
            </>
          )}
        </div>
      </section>

      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-bg2/90 backdrop-blur-lg border border-teal/30 shadow-2xl rounded-xl px-5 py-3 flex items-center gap-3 animate-fadeIn text-sm text-text">
          <span className="text-teal font-bold">✓</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {showSettingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-bg2 border border-border w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-slideIn">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-bg3">
              <h2 className="text-lg font-light text-text flex items-center gap-2">
                <Brain size={18} className="text-purple-500" /> Manage ARIA's Memory
              </h2>
              <button
                type="button"
                onClick={() => {
                  setShowSettingsModal(false);
                  setEditingInsightId(null);
                }}
                className="text-text3 hover:text-text text-sm transition-all"
              >
                ✕ Close
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-left">
              {/* Computed Topics */}
              <div className="space-y-2.5">
                <h3 className="text-xs font-light tracking-[0.05em] uppercase text-accent">
                  Topics ARIA remembers about you
                </h3>
                <div className="flex flex-wrap gap-2">
                  {getUniqueTopics().map((topic, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 bg-accent/10 border border-accent/20 rounded-full text-xs font-medium text-accent2"
                    >
                      ✦ {topic}
                    </span>
                  ))}
                </div>
              </div>

              {/* ARIA's Profile of Your Style */}
              <div className="bg-bg3 border border-border rounded-xl p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <h3 className="text-xs font-light tracking-[0.05em] uppercase text-accent">
                    ARIA's Profile of Your Style
                  </h3>
                  {personality && (
                    <button
                      type="button"
                      onClick={handleAnalyzePersonality}
                      disabled={analyzingPersonality}
                      className="text-xs text-accent2 hover:text-accent font-medium transition-all disabled:opacity-50"
                    >
                      {analyzingPersonality ? 'Analyzing...' : 'Re-analyze Style'}
                    </button>
                  )}
                </div>

                {personality ? (
                  <div className="space-y-3 text-xs">
                    <div>
                      <strong className="text-text2">Communication Style:</strong>{' '}
                      <span className="text-text">{personality.communication_style}</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
                      <div className="bg-bg2 border border-border rounded-lg p-2.5 text-center">
                        <div className="text-[10px] text-text3 uppercase tracking-[0.02em]">Advice Type</div>
                        <div className="text-text font-medium mt-0.5">
                          {personality.preference_advice_type === 'direct_advice' ? '⚡ Direct Advice' : '🌸 Gentle Suggestions'}
                        </div>
                      </div>
                      <div className="bg-bg2 border border-border rounded-lg p-2.5 text-center">
                        <div className="text-[10px] text-text3 uppercase tracking-[0.02em]">Response Length</div>
                        <div className="text-text font-medium mt-0.5">
                          📏 {personality.response_length_preference}
                        </div>
                      </div>
                      <div className="bg-bg2 border border-border rounded-lg p-2.5 text-center">
                        <div className="text-[10px] text-text3 uppercase tracking-[0.02em]">Emotional Openness</div>
                        <div className="text-text font-medium mt-0.5">
                          👐 {personality.emotional_openness}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-text3 italic flex justify-between items-center gap-4 py-1">
                    <span>No style analysis has been performed yet (requires 5+ conversations).</span>
                    <button
                      type="button"
                      onClick={handleAnalyzePersonality}
                      disabled={analyzingPersonality}
                      className="px-3 py-1.5 bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent2 hover:text-accent rounded-lg font-medium transition-all text-xs whitespace-nowrap disabled:opacity-50"
                    >
                      {analyzingPersonality ? 'Analyzing...' : 'Analyze Now'}
                    </button>
                  </div>
                )}
              </div>

              {/* Memory Insights List */}
              <div className="space-y-4">
                <h3 className="text-xs font-light tracking-[0.05em] uppercase text-accent">
                  Saved memory insights
                </h3>
                {memoryInsights.length === 0 ? (
                  <p className="text-xs text-text3 italic py-4">
                    ARIA hasn't saved any memory insights about you yet.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {memoryInsights.map((item) => (
                      <div
                        key={item.id}
                        className="bg-bg3 border border-border rounded-xl p-4 space-y-3 relative group"
                      >
                        {editingInsightId === item.id ? (
                          /* Editing Mode */
                          <div className="space-y-3">
                            <div className="space-y-1">
                              <label className="text-[10px] uppercase text-text3">Situation / What Happened</label>
                              <input
                                type="text"
                                value={editFields.situation}
                                onChange={(e) => setEditFields({ ...editFields, situation: e.target.value })}
                                className="w-full bg-bg2 border border-border rounded-lg px-3 py-2 text-xs text-text focus:outline-none focus:border-accent"
                              />
                            </div>
                            <div className="space-y-1">
                              <label className="text-[10px] uppercase text-text3">Associated Emotions</label>
                              <input
                                type="text"
                                value={editFields.emotion}
                                onChange={(e) => setEditFields({ ...editFields, emotion: e.target.value })}
                                className="w-full bg-bg2 border border-border rounded-lg px-3 py-2 text-xs text-text focus:outline-none focus:border-accent"
                              />
                            </div>
                            <div className="space-y-1">
                              <label className="text-[10px] uppercase text-text3">What Helped</label>
                              <input
                                type="text"
                                value={editFields.what_helped}
                                onChange={(e) => setEditFields({ ...editFields, what_helped: e.target.value })}
                                className="w-full bg-bg2 border border-border rounded-lg px-3 py-2 text-xs text-text focus:outline-none focus:border-accent"
                              />
                            </div>
                            <div className="space-y-1">
                              <label className="text-[10px] uppercase text-text3">Follow Up Suggestion</label>
                              <input
                                type="text"
                                value={editFields.follow_up}
                                onChange={(e) => setEditFields({ ...editFields, follow_up: e.target.value })}
                                className="w-full bg-bg2 border border-border rounded-lg px-3 py-2 text-xs text-text focus:outline-none focus:border-accent"
                              />
                            </div>
                            <div className="flex gap-2 justify-end pt-1">
                              <button
                                type="button"
                                onClick={() => handleSaveEdit(item.id)}
                                className="px-3 py-1.5 bg-accent hover:bg-accent2 text-white text-xs rounded-lg transition-all"
                              >
                                Save
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingInsightId(null)}
                                className="px-3 py-1.5 bg-bg4 border border-border text-text2 hover:text-text text-xs rounded-lg transition-all"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          /* View Mode */
                          <>
                            <div className="flex justify-between items-start">
                              <div>
                                <span className="text-[10px] text-text3 font-medium bg-bg4 px-2.5 py-0.5 rounded-full border border-border uppercase">
                                  {item.context_type || 'chat'}
                                </span>
                                <span className="text-[10px] text-text3 ml-2">
                                  {item.date || item.created?.slice(0, 10) || ''}
                                </span>
                              </div>
                              <div className="flex gap-2 opacity-80 group-hover:opacity-100 transition-all">
                                <button
                                  type="button"
                                  onClick={() => handleStartEdit(item)}
                                  className="text-accent2 hover:text-accent hover:underline text-[10px]"
                                >
                                  Edit
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteInsight(item.id)}
                                  className="text-rose hover:underline text-[10px]"
                                  title="ARIA, forget about this"
                                >
                                  Forget
                                </button>
                              </div>
                            </div>
                            <div className="space-y-1.5 text-xs">
                              <div>
                                <strong className="text-text2">Situation:</strong>{' '}
                                <span className="text-text">{item.situation || item.what_happened}</span>
                              </div>
                              <div>
                                <strong className="text-text2">Emotions:</strong>{' '}
                                <span className="text-text">{item.emotion}</span>
                              </div>
                              <div>
                                <strong className="text-text2">What Helped:</strong>{' '}
                                <span className="text-text">{item.what_helped}</span>
                              </div>
                              <div>
                                <strong className="text-text2">Follow Up:</strong>{' '}
                                <span className="text-text italic">{item.follow_up}</span>
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
