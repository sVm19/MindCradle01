import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '@/lib/auth';
import { profile as profileApi } from '@/lib/api';
import GuestGate from '@/app/components/GuestGate';
import { 
  ArrowLeft, Sparkles, Eye, Shield, Lock, 
  Settings as SettingsIcon, AppWindow, Calendar, 
  Compass, Heart, CheckCircle2, Award, Flame, Sun,
  Plus, Search, HelpCircle, ArrowRight, Layers, Activity, Wind, Zap
} from 'lucide-react';

declare global {
  interface Window {
    AndroidWidgetBridge?: {
      pinWidget: (widgetId: string) => void;
    };
  }
}

export default function WidgetGallery() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [modalWidget, setModalWidget] = useState<any | null>(null);

  // Widget settings
  const [personalizedEnabled, setPersonalizedEnabled] = useState(true);
  const [memoriesEnabled, setMemoriesEnabled] = useState(true);
  const [ariaPersonalizedEnabled, setAriaPersonalizedEnabled] = useState(true);
  const [sensitiveEnabled, setSensitiveEnabled] = useState(false);

  // Platform guide tab state
  const [selectedPlatform, setSelectedPlatform] = useState<'ios' | 'android'>('ios');

  // Detect platform on load
  useEffect(() => {
    const ua = navigator.userAgent.toLowerCase();
    if (ua.includes('iphone') || ua.includes('ipad') || ua.includes('ipod') || ua.includes('macintosh')) {
      setSelectedPlatform('ios');
    } else if (ua.includes('android')) {
      setSelectedPlatform('android');
    }
  }, []);

  // Fetch settings from profile
  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    profileApi.get()
      .then((res) => {
        setPersonalizedEnabled(res.widget_personalized_enabled ?? true);
        setMemoriesEnabled(res.widget_memories_enabled ?? true);
        setAriaPersonalizedEnabled(res.widget_aria_personalized_enabled ?? true);
        setSensitiveEnabled(res.widget_sensitive_enabled ?? false);
      })
      .catch((err) => {
        console.error('Failed to load widget profile settings:', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [user]);

  const handleAddToHomeScreen = (widget: any) => {
    // 1. Check if running inside Android native shell with bridge enabled
    if (window.AndroidWidgetBridge) {
      try {
        window.AndroidWidgetBridge.pinWidget(widget.id);
        return;
      } catch (err) {
        console.error('Android programmatic widget pinning failed:', err);
      }
    }
    // 2. Else (iOS or standard web browsers), show the overlay modal dialog
    setModalWidget(widget);
  };

  if (!user) {
    return (
      <GuestGate
        title="MindCradle Widget System"
        description="Configure privacy parameters and preview beautiful home-screen widgets."
        icon={<SettingsIcon className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  // Dynamic preview text blocks based on privacy settings loaded from profile
  const ariaText = personalizedEnabled && ariaPersonalizedEnabled && !sensitiveEnabled
    ? "Before your day gets busy, what's one thing you'd like to make space for today?"
    : "How are you feeling today? Tap to check in.";

  const insightText = personalizedEnabled && !sensitiveEnabled
    ? "Keep journaling. MindCradle will begin discovering patterns as your history grows."
    : "Your morning rituals correlate with a 35% higher calmness index.";

  const memoryText = personalizedEnabled && memoriesEnabled && !sensitiveEnabled
    ? "Keep reflecting. MindCradle will preserve your meaningful moments here as your history grows."
    : "Three months ago, you wrote about wanting more uninterrupted time.";

  const solsticeText = "You don't need to solve everything today. Some things become clearer when you give them space.";

  const widgets = [
    {
      id: 'aria',
      name: 'ARIA Assistant',
      description: 'Draw focus suggestions and daily reflections from ARIA.',
      preview: (
        <div className="w-full flex flex-col justify-between h-full text-left" style={{ color: '#fff' }}>
          <div className="flex gap-3 justify-between items-start">
            <div className="space-y-0.5">
              <span style={{ fontSize: '10px', color: '#888', fontWeight: 'bold' }}>ARIA</span>
              <p style={{ fontSize: '11px', lineHeight: '1.4', color: '#eee' }}>
                "{ariaText}"
              </p>
            </div>
            {/* Companion purple planet illustration */}
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-purple-800 to-indigo-500 shadow-[0_0_12px_rgba(139,92,246,0.3)] flex-shrink-0 flex items-center justify-center relative">
              <div className="absolute inset-0.5 rounded-full bg-[#0f0a1c] flex items-center justify-center">
                <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-400 flex items-center justify-center gap-1 shadow-[inset_0_1.5px_3px_rgba(255,255,255,0.2)]">
                  <div className="w-0.5 h-1 rounded-full bg-white opacity-85" />
                  <div className="w-0.5 h-1 rounded-full bg-white opacity-85" />
                </div>
              </div>
            </div>
          </div>
          <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-2" style={{ fontSize: '9px', color: '#666' }}>
            <span>mindcradle://aria</span>
            <span style={{ color: '#feba7b', fontWeight: 'semibold' }}>Talk</span>
          </div>
        </div>
      )
    },
    {
      id: 'journal',
      name: 'Quick Journal',
      description: 'Compose journals instantly with daily reflective prompts.',
      preview: (
        <div className="w-full flex flex-col justify-between h-full text-left" style={{ color: '#fff' }}>
          <div className="flex justify-between items-start gap-3">
            <div className="space-y-0.5">
              <span style={{ fontSize: '10px', color: '#888', fontWeight: 'bold' }}>DAILY JOURNAL</span>
              <p style={{ fontSize: '12px', color: '#fff', fontWeight: 'light' }}>What's on your mind today?</p>
            </div>
            {/* Notebook icon */}
            <div className="w-10 h-9 rounded border border-teal-500/20 bg-teal-500/5 relative flex items-center justify-center flex-shrink-0">
              <div className="absolute left-0.5 top-0 bottom-0 w-0.5 bg-teal-500/25" />
              <div className="w-4 h-0.5 bg-white/20 my-0.5 rounded" />
            </div>
          </div>
          <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-2" style={{ fontSize: '9px', color: '#666' }}>
            <span>mindcradle://journal/new</span>
            <span style={{ color: '#feba7b', fontWeight: 'semibold' }}>Write</span>
          </div>
        </div>
      )
    },
    {
      id: 'insight',
      name: 'Daily Insight',
      description: 'Highlight core wellness correlations and balance insights.',
      preview: (
        <div className="w-full flex flex-col justify-between h-full text-left" style={{ color: '#fff' }}>
          <div className="flex justify-between items-start gap-3">
            <div className="space-y-0.5">
              <span style={{ fontSize: '10px', color: '#888', fontWeight: 'bold' }}>TODAY'S INSIGHT</span>
              <p style={{ fontSize: '11px', lineHeight: '1.4', color: '#eee' }}>
                {insightText}
              </p>
            </div>
            {/* Sunset icon */}
            <div className="w-10 h-9 rounded border border-amber-500/20 bg-amber-500/5 relative overflow-hidden flex items-end justify-center flex-shrink-0">
              <div className="w-4 h-4 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)] translate-y-1.5" />
            </div>
          </div>
          <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-2" style={{ fontSize: '9px', color: '#666' }}>
            <span>mindcradle://insight</span>
            <span style={{ color: '#feba7b', fontWeight: 'semibold' }}>Explore</span>
          </div>
        </div>
      )
    },
    {
      id: 'memory',
      name: 'Memory Recall',
      description: 'Display reflection moments from your history card.',
      preview: (
        <div className="w-full flex flex-col justify-between h-full text-left" style={{ color: '#fff' }}>
          <div className="flex justify-between items-start gap-3">
            <div className="space-y-0.5">
              <span style={{ fontSize: '10px', color: '#888', fontWeight: 'bold' }}>FROM YOUR MEMORY</span>
              <p style={{ fontSize: '11px', lineHeight: '1.4', color: '#eee' }}>
                "{memoryText}"
              </p>
            </div>
            {/* Tree icon */}
            <div className="w-10 h-9 rounded border border-purple-500/20 bg-purple-500/5 relative overflow-hidden flex items-center justify-center flex-shrink-0">
              <div className="w-4 h-4 rounded-full bg-gradient-to-tr from-purple-800 to-indigo-600 shadow-[0_0_8px_rgba(168,85,247,0.4)]" />
            </div>
          </div>
          <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-2" style={{ fontSize: '9px', color: '#666' }}>
            <span>mindcradle://memory</span>
            <span style={{ color: '#feba7b', fontWeight: 'semibold' }}>View</span>
          </div>
        </div>
      )
    },
    {
      id: 'question',
      name: 'Daily Question',
      description: 'Gentle daily queries prompting self-discovery.',
      preview: (
        <div className="w-full flex flex-col justify-between h-full text-left" style={{ color: '#fff' }}>
          <div className="flex justify-between items-start gap-3">
            <div className="space-y-0.5">
              <span style={{ fontSize: '10px', color: '#888', fontWeight: 'bold' }}>TODAY'S QUESTION</span>
              <p style={{ fontSize: '11px', color: '#eee', fontWeight: 'medium' }}>
                What deserves less of your attention today?
              </p>
            </div>
            {/* Moon icon */}
            <div className="w-10 h-9 rounded border border-sky-500/20 bg-slate-900 relative overflow-hidden flex items-center justify-center flex-shrink-0">
              <div className="w-3.5 h-3.5 rounded-full border-t-2 border-r-2 border-sky-200 rotate-45 transform translate-x-0.5 -translate-y-0.5" />
            </div>
          </div>
          <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-2" style={{ fontSize: '9px', color: '#666' }}>
            <span>mindcradle://journal/reflection</span>
            <span style={{ color: '#feba7b', fontWeight: 'semibold' }}>Reflect</span>
          </div>
        </div>
      )
    },
    {
      id: 'mood',
      name: 'Mood Check-in',
      description: 'Quick emotional outlook buttons mapping directly to log flows.',
      preview: (
        <div className="w-full flex flex-col justify-between h-full text-left" style={{ color: '#fff' }}>
          <div>
            <span style={{ fontSize: '10px', color: '#888', fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>HOW ARE YOU FEELING?</span>
            <div className="grid grid-cols-5 gap-1.5 text-center">
              {['Great', 'Good', 'Okay', 'Low', 'Hard'].map((label, idx) => {
                const icons = [
                  <Activity size={10} className="text-teal" />,
                  <Heart size={10} className="text-teal" />,
                  <Compass size={10} className="text-text2" />,
                  <Wind size={10} className="text-rose" />,
                  <Shield size={10} className="text-rose" />
                ];
                return (
                  <div key={idx} className="flex flex-col items-center gap-1 bg-white/5 p-1 rounded">
                    {icons[idx]}
                    <span style={{ fontSize: '7px', color: '#888' }}>{label}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="text-[8px] text-center text-text3 mt-1.5">
            Tapping opens mood check-in flow
          </div>
        </div>
      )
    },
    {
      id: 'habit',
      name: 'Habit Pulse',
      description: 'Track ongoing daily goals and morning/night routines.',
      preview: (
        <div className="w-full flex flex-col justify-between h-full text-left" style={{ color: '#fff' }}>
          <div className="flex justify-between items-start">
            <div className="space-y-0.5 text-[9px] text-text3 flex-grow">
              <span style={{ fontSize: '9px', color: '#888', fontWeight: 'bold', display: 'block', marginBottom: '2px' }}>TODAY'S ROUTINES</span>
              <div className="flex justify-between items-center w-20">
                <span>Journal</span>
                <span className="text-[#2dd4bf] font-bold">✓</span>
              </div>
              <div className="flex justify-between items-center w-20">
                <span>Reflection</span>
                <span className="text-[#2dd4bf] font-bold">✓</span>
              </div>
            </div>
            {/* Ring progress */}
            <div className="w-8 h-8 rounded-full border-4 border-white/5 border-t-[#2dd4bf] border-r-[#2dd4bf] rotate-45 flex-shrink-0" />
          </div>
          <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-2" style={{ fontSize: '8px', color: '#666' }}>
            <span>2 / 3 complete</span>
            <span style={{ color: '#feba7b' }}>Open</span>
          </div>
        </div>
      )
    },
    {
      id: 'streak',
      name: 'Streak Counter',
      description: 'View active engagement streak metrics on the home screen.',
      preview: (
        <div className="w-full flex flex-col justify-between h-full text-left" style={{ color: '#fff' }}>
          <div className="flex items-center gap-2">
            <Flame size={20} className="text-amber-500 fill-amber-500 animate-pulse" />
            <div>
              <span style={{ fontSize: '14px', fontWeight: 'bold', display: 'block', lineHeight: '1' }}>7 DAYS</span>
              <span style={{ fontSize: '7px', color: '#888', textTransform: 'uppercase' }}>Engagement Streak</span>
            </div>
          </div>
          <p style={{ fontSize: '10px', color: '#ccc', marginTop: '6px' }}>
            You've checked in 7 days in a row!
          </p>
        </div>
      )
    },
    {
      id: 'solstice',
      name: 'Solstice Digest',
      description: 'Premium insights, weekly patterns, and summaries.',
      preview: (
        <div className="w-full flex flex-col justify-between h-full text-left" style={{ color: '#fff' }}>
          <div className="flex justify-between gap-2 items-center">
            <div className="space-y-0.5">
              <span style={{ fontSize: '9px', color: '#888', fontWeight: 'bold' }}>A NOTE FOR YOU</span>
              <p style={{ fontSize: '10px', color: '#eee', lineHeight: '1.3' }}>
                "{solsticeText}"
              </p>
            </div>
            {/* Sunrise illustration */}
            <div className="w-12 h-8 rounded bg-gradient-to-tr from-[#2d1b50] to-[#120d24] relative overflow-hidden flex items-end justify-center flex-shrink-0">
              <div className="w-6 h-6 rounded-full bg-yellow-400 shadow-[0_0_8px_rgba(234,179,8,0.5)] translate-y-3" />
            </div>
          </div>
          <div className="flex justify-between items-center border-t border-white/5 pt-1.5 mt-2" style={{ fontSize: '9px', color: '#666' }}>
            <span>mindcradle://solstice</span>
            <span style={{ color: '#feba7b', fontWeight: 'semibold' }}>Open</span>
          </div>
        </div>
      )
    }
  ];

  return (
    <div style={{ color: '#fff', paddingBottom: '4rem', lineHeight: '1.6' }}>
      
      {/* Back button above header */}
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '1rem 2rem 0' }}>
        <button
          onClick={() => navigate('/settings')}
          style={{
            background: 'none',
            border: 'none',
            color: '#aaa',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '14px',
            fontWeight: '500'
          }}
          className="hover:text-white transition-all"
        >
          <ArrowLeft size={16} /> Back to Settings
        </button>
      </div>

      {/* NEW HEADER - Styled with App Accent Color (CIE Gold #feba7b) */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(254, 180, 123, 0.18) 0%, rgba(15, 10, 28, 0) 100%)',
        padding: '2rem',
        textAlign: 'center',
        marginBottom: '2rem',
        borderRadius: '24px',
        border: '1px solid rgba(254, 180, 123, 0.08)',
        maxWidth: '1360px',
        margin: '1rem auto 2rem'
      }}>
        <h1 style={{ fontSize: '40px', marginBottom: '0.5rem', fontWeight: '300', fontFamily: 'var(--font-serif)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          Bring 
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" style={{ height: '34px', width: '34px', transform: 'translateY(-2px)' }}>
              <g stroke="#feba7b" strokeWidth="5.5" fill="none" strokeLinejoin="round" strokeLinecap="round">
                <path d="M 23,37 L 23,17 L 63,17 L 63,57 L 43,57 L 43,37 Z" />
                <rect x="17" y="43" width="20" height="20" rx="2" />
              </g>
            </svg>
            <span style={{ fontWeight: '400', letterSpacing: '-0.02em' }}>MindCradle</span>
          </span> 
          Home
        </h1>
        <p style={{ fontSize: '18px', color: '#ddd', marginBottom: '1.5rem' }}>
          Choose your widgets. Stay connected.
        </p>

        {/* Feature Highlights Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1.5rem',
          maxWidth: '1200px',
          margin: '2rem auto 0',
          textAlign: 'left'
        }}>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.04)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#feba7b', fontSize: '13px', fontWeight: '600', marginBottom: '0.5rem' }}>
              <Shield size={14} /> Privacy-First Content
            </div>
            <p style={{ fontSize: '11px', color: '#bbb', lineHeight: '1.5' }}>
              Your reflections are encrypted. Sensitive info (such as memory highlights or custom messages) is hidden by default in lock-screen contexts, in full compliance with your settings.
            </p>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.04)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#feba7b', fontSize: '13px', fontWeight: '600', marginBottom: '0.5rem' }}>
              <Zap size={14} /> Battery & Resource Friendly
            </div>
            <p style={{ fontSize: '11px', color: '#bbb', lineHeight: '1.5' }}>
              Widgets utilize native iOS/Android Timeline providers. They update dynamically inside scheduled background slots to conserve cellular data and battery life.
            </p>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.04)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#feba7b', fontSize: '13px', fontWeight: '600', marginBottom: '0.5rem' }}>
              <Compass size={14} /> Direct Navigation Shortcuts
            </div>
            <p style={{ fontSize: '11px', color: '#bbb', lineHeight: '1.5' }}>
              Tapping elements uses registered mobile deep-link schemas (`mindcradle://`) to bypass intermediate loading screens and jump straight to ARIA or the journal builder.
            </p>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.04)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#feba7b', fontSize: '13px', fontWeight: '600', marginBottom: '0.5rem' }}>
              <Award size={14} /> Offline Resilience
            </div>
            <p style={{ fontSize: '11px', color: '#bbb', lineHeight: '1.5' }}>
              Widget data is cached on-device. Previews, streaks, and check-ins continue to display your last-synced metrics offline, keeping you in touch without requiring constant connectivity.
            </p>
          </div>
        </div>
      </div>

      {/* GRID LAYOUT */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '2rem',
        padding: '2rem',
        maxWidth: '1400px',
        margin: '0 auto'
      }}>
        
        {/* Render each Widget Card using App Theme styles */}
        {widgets.map((widget) => (
          <div 
            key={widget.id}
            style={{
              background: 'linear-gradient(135deg, #1c1635 0%, #0f0a1c 100%)',
              border: '1px solid rgba(254, 180, 123, 0.12)',
              borderRadius: '16px',
              padding: '1.5rem',
              transition: 'all 0.3s',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'between',
              minHeight: '320px'
            }}
            className="hover:shadow-[0_4px_20px_rgba(254,180,123,0.12)] hover:border-[#feba7b]/40 transition-all duration-300"
          >
            {/* Icon + Title */}
            <div style={{ marginBottom: '1rem', textAlign: 'left' }}>
              <h3 style={{ fontSize: '18px', marginBottom: '0.5rem', fontWeight: '500' }}>
                {widget.name}
              </h3>
              <p style={{ fontSize: '14px', color: '#aaa', minHeight: '40px', lineHeight: '1.4' }}>
                {widget.description}
              </p>
            </div>

            {/* Preview Box */}
            <div style={{
              background: '#0f0a1c',
              borderRadius: '12px',
              padding: '1rem',
              marginBottom: '1.5rem',
              minHeight: '120px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#666',
              flexGrow: 1
            }}>
              {widget.preview}
            </div>

            {/* Button */}
            <button 
              onClick={() => handleAddToHomeScreen(widget)}
              style={{
                width: '100%',
                background: '#feba7b',
                color: '#0c0714',
                border: 'none',
                padding: '10px 16px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: '600',
                transition: 'background 0.2s'
              }}
              className="hover:bg-[#fdb066] transition-all"
            >
              Add to Home Screen
            </button>
          </div>
        ))}

      </div>

      {/* SETUP GUIDE (Moved to bottom) */}
      <section 
        id="setup-guide-section"
        style={{
          background: '#1c1635',
          padding: '2rem',
          borderRadius: '16px',
          marginTop: '4rem',
          maxWidth: '800px',
          margin: '4rem auto 0',
          textAlign: 'left',
          border: '1px solid rgba(254, 180, 123, 0.12)'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(254, 180, 123, 0.08)', paddingBottom: '0.75rem' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '500', fontFamily: 'var(--font-serif)' }}>How to Add Widgets</h2>
          
          <div className="flex bg-[#0f0a1c] p-0.5 rounded-lg border border-white/5">
            <button
              onClick={() => setSelectedPlatform('ios')}
              className={`text-[10px] px-3 py-1 rounded font-bold transition-all ${selectedPlatform === 'ios' ? 'bg-[#feba7b] text-[#0c0714] shadow-md' : 'text-text3'}`}
            >
              iOS
            </button>
            <button
              onClick={() => setSelectedPlatform('android')}
              className={`text-[10px] px-3 py-1 rounded font-bold transition-all ${selectedPlatform === 'android' ? 'bg-[#feba7b] text-[#0c0714] shadow-md' : 'text-text3'}`}
            >
              Android
            </button>
          </div>
        </div>

        {selectedPlatform === 'ios' ? (
          <ol style={{ lineHeight: '2', listStyleType: 'decimal', paddingLeft: '1.5rem', fontSize: '14px', color: '#ddd' }}>
            <li>Hold empty area on home screen until apps jiggle.</li>
            <li>Tap <strong style={{ color: '#fff' }}>+ button</strong> (top-left).</li>
            <li>Search <strong style={{ color: '#fff' }}>"MindCradle"</strong>.</li>
            <li>Select widget + size preference.</li>
            <li>Tap <strong style={{ color: '#feba7b' }}>"Add Widget"</strong>.</li>
          </ol>
        ) : (
          <ol style={{ lineHeight: '2', listStyleType: 'decimal', paddingLeft: '1.5rem', fontSize: '14px', color: '#ddd' }}>
            <li>Touch and hold an empty space on your Android home screen.</li>
            <li>Tap <strong style={{ color: '#fff' }}>Widgets</strong> in the pop-up menu.</li>
            <li>Scroll and expand the <strong style={{ color: '#fff' }}>MindCradle</strong> row.</li>
            <li>Touch, hold, and drag the widget to place it.</li>
            <li>Adjust the bounding corners to resize.</li>
          </ol>
        )}
      </section>

      {/* Target Popup Instructions Modal */}
      {modalWidget && (
        <div 
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '1rem'
          }}
          onClick={() => setModalWidget(null)}
        >
          <div 
            style={{
              background: '#1c1635',
              border: '1px solid rgba(254, 180, 123, 0.2)',
              borderRadius: '20px',
              padding: '2rem',
              maxWidth: '480px',
              width: '100%',
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
              position: 'relative',
              textAlign: 'left'
            }}
            onClick={(e) => e.stopPropagation()}
            className="animate-scaleIn"
          >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(254, 180, 123, 0.08)', paddingBottom: '0.75rem' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#feba7b', fontFamily: 'var(--font-serif)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={16} /> Add {modalWidget.name}
              </h3>
              <button 
                onClick={() => setModalWidget(null)}
                style={{ background: 'none', border: 'none', color: '#888', fontSize: '20px', cursor: 'pointer', lineHeight: '1' }}
                className="hover:text-white"
              >
                &times;
              </button>
            </div>

            {/* Platform Instructions */}
            <p style={{ fontSize: '13px', color: '#ccc', marginBottom: '1.25rem', lineHeight: '1.5' }}>
              To place the <strong style={{ color: '#fff' }}>{modalWidget.name}</strong> on your home screen, please follow the platform-specific instructions below:
            </p>

            <div style={{ background: '#0f0a1c', padding: '1.25rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.03)' }}>
              <h4 style={{ fontSize: '12px', fontWeight: 'bold', color: '#fff', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                iOS Steps:
              </h4>
              <ol style={{ fontSize: '12px', color: '#bbb', paddingLeft: '1.25rem', listStyleType: 'decimal', lineHeight: '1.8' }}>
                <li>Hold down an empty spot on your Home Screen.</li>
                <li>Tap the <strong style={{ color: '#feba7b' }}>+ icon</strong> in the top corner.</li>
                <li>Find <strong style={{ color: '#fff' }}>MindCradle</strong> & select {modalWidget.name}.</li>
                <li>Pick your size and tap <strong style={{ color: '#feba7b' }}>Add Widget</strong>.</li>
              </ol>

              <h4 style={{ fontSize: '12px', fontWeight: 'bold', color: '#fff', marginTop: '1.25rem', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Android Steps:
              </h4>
              <ol style={{ fontSize: '12px', color: '#bbb', paddingLeft: '1.25rem', listStyleType: 'decimal', lineHeight: '1.8' }}>
                <li>Long press an empty slot on your launcher.</li>
                <li>Select <strong style={{ color: '#fff' }}>Widgets</strong> and locate MindCradle.</li>
                <li>Drag the widget receiver to place it.</li>
              </ol>
            </div>

            {/* Dismiss Button */}
            <button
              onClick={() => setModalWidget(null)}
              style={{
                width: '100%',
                background: '#feba7b',
                color: '#0c0714',
                border: 'none',
                padding: '10px 16px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: '600',
                marginTop: '1.5rem',
                textAlign: 'center'
              }}
              className="hover:bg-[#fdb066] transition-all"
            >
              Got it
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
