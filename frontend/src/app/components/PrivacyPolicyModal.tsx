import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { auth as authApi } from '@/lib/api';
import Logo from './Logo';

export default function PrivacyPolicyModal() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [scrollPercent, setScrollPercent] = useState(0);
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Disable auto-opening privacy policy modal on first visit
    setIsOpen(false);
  }, []);

  const handleScroll = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const scrollableHeight = container.scrollHeight - container.clientHeight;
    if (scrollableHeight <= 0) {
      setScrollPercent(100);
      setHasScrolledToBottom(true);
      return;
    }

    const scrolledAmount = container.scrollTop;
    const percentage = (scrolledAmount / scrollableHeight) * 100;
    setScrollPercent(percentage);

    if (percentage >= 95) {
      setHasScrolledToBottom(true);
    }
  };

  // Trigger scroll check on mount or when content changes to handle container sizing
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        handleScroll();
      }, 100);
    }
  }, [isOpen]);

  const handleCheckClick = (e: React.MouseEvent) => {
    if (!hasScrolledToBottom) {
      e.preventDefault();
      setError('Please read through the entire privacy policy first');
    }
  };

  const handleSubmit = async () => {
    if (scrollPercent < 95 && !hasScrolledToBottom) {
      setError('Please read through the entire privacy policy first');
      return;
    }
    if (!agreed) {
      setError('Please check the box to agree to the Privacy Policy');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // 1. Save to database (anonymous POST)
      await authApi.acceptPrivacy(true);

      // 2. Save to localStorage
      localStorage.setItem('privacy_accepted', 'true');
      localStorage.setItem(
        'privacy_accepted_data',
        JSON.stringify({ privacy_accepted: true, accepted_at: new Date().toISOString() })
      );

      // 3. Close modal
      setIsOpen(false);

      // 4. Redirect to Login page (Google OAuth signup is handled here)
      navigate('/login');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save agreement');
    } finally {
      setLoading(false);
    }
  };

  const handleAttemptClose = () => {
    setError('Please read through the entire privacy policy first');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-bg/95 backdrop-blur-md p-4 animate-fadeIn">
      {/* Background click interceptor — doesn't allow closing */}
      <div className="absolute inset-0" onClick={handleAttemptClose} />

      <div className="w-full max-w-2xl bg-bg2 border border-border rounded-[24px] p-6 md:p-8 relative shadow-2xl animate-slideIn flex flex-col max-h-[90vh] z-10 text-left">
        {/* Logo */}
        <div className="flex justify-start mb-4">
          <Logo className="h-8 w-auto text-text" />
        </div>

        <h1 className="text-xl md:text-2xl font-light text-text mb-4 font-[family-name:var(--font-serif)]">
          Privacy Policy & Terms
        </h1>

        {error && (
          <div className="bg-rose/10 border border-rose/30 text-rose text-xs rounded-[12px] px-4 py-3 mb-4 flex-shrink-0 animate-fadeIn">
            {error}
          </div>
        )}

        {/* Scrollable text area */}
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto pr-3 mb-6 h-[400px] border border-border/50 rounded-xl bg-bg3/20 p-4 text-xs md:text-[13px] text-text3 leading-relaxed space-y-4 select-text"
          style={{ scrollbarWidth: 'thin' }}
        >
          <p className="font-semibold text-text">Effective Date: June 17, 2026</p>
          
          <p>
            Welcome to MindCradle. Your trust is our most valuable asset. We are dedicated to providing a safe, secure, and supportive environment for your daily routines. This Privacy Policy details how we handle, protect, and process your data. Please read this document in its entirety to understand how we store and handle your personal logs, reflection entries, and conversation details with ARIA, our built-in AI companion.
          </p>

          <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
            1. Data Collection & Privacy First Approach
          </h2>
          <p>
            MindCradle is built on a privacy-first foundation. We gather minimal personal information required to run the core features of the dashboard. The information we collect includes:
          </p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>
              <strong>Account Credentials:</strong> Your email address, password, and chosen profile name are collected during user registration. These are securely processed and verified via Supabase authentication.
            </li>
            <li>
              <strong>Daily Check-in Data:</strong> Numerical ratings of your state of calm (from 1 to 10), selected emotion categories, and custom narrative notes representing your state at check-in.
            </li>
            <li>
              <strong>Routine Entries:</strong> Intentions, activity choices, completion timestamps, and reflection entries recorded during your morning and wind-down routines.
            </li>
            <li>
              <strong>Journal Reflections:</strong> Text content you draft inside the digital journal tool, which is processed to generate personalized AI-driven reflections.
            </li>
            <li>
              <strong>ARIA Chat Logs:</strong> Chat logs of all text exchanges with our AI companion, ARIA, to enable context retention, conversational memory, and consistency analysis.
            </li>
          </ul>

          <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
            2. How We Use Your Data
          </h2>
          <p>
            Your information is processed strictly to provide the tracking functionality and features. We do not sell or trade your data. The data is used to:
          </p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>Synthesize calm indices and routine progress graphs on your dashboard.</li>
            <li>Maintain historical memory for ARIA to provide contextual, warm, and daily insights.</li>
            <li>Detect acute distress levels to proactively deliver helpful resources.</li>
            <li>Perform internal A/B experiments to evaluate feature engagement, response speeds, and UI layouts to continuously refine the experience.</li>
          </ul>

          <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
            3. Data Storage, Security, & GDPR Compliance
          </h2>
          <p>
            All connection states and transaction details are encrypted using Transport Layer Security (TLS) in transit, and databases are encrypted at rest.
          </p>
          <p>
            If you are situated in the European Union (EU) or European Economic Area (EEA), you benefit from standard rights under the General Data Protection Regulation (GDPR). These rights include:
          </p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong>Right of Erasure:</strong> The capability to completely purge your account and delete all associated journals, mood records, and chat history permanently.</li>
            <li><strong>Right to Restrict Processing:</strong> The ability to adjust notifications, disable background processing trackers, or disconnect push notification tokens.</li>
            <li><strong>Right to Access & Portability:</strong> The ability to request a complete export of all historical reflections linked to your identity.</li>
          </ul>

          <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
            4. AI Integrations & Prompt Privacy
          </h2>
          <p>
            To power the reflective capabilities of ARIA, we utilize advanced language models.
          </p>
          <p>
            Before sending your messages or journal contents to these external AI models, all direct personally identifiable information (PII) is stripped out. AI providers do not use your conversations to train their public models, and all interactions are subject to strict data retention policies.
          </p>

          <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
            5. Distress Support & Safety Handover Policies
          </h2>
          <p>
            ARIA is a conversational companion designed for positive self-awareness and daily reflection. ARIA is not a medical device, a replacement for professional clinical care, or an emergency responder.
          </p>
          <p>
            If you log severe or acute distress, our system will automatically show a support banner pointing to 24/7 hotlines (e.g. 988 Lifeline, Crisis Text Line). Furthermore, if you specify an emergency contact in settings, we may log a safety handover record to assist in notifying your designated supporter.
          </p>

          <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
            6. Consent and Agreement
          </h2>
          <p>
            By scrolling to the bottom of this text, checking the consent checkbox, and clicking "I Agree & Continue", you confirm that:
          </p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>You are at least 18 years of age (or have explicit parental consent).</li>
            <li>You understand that ARIA is an AI companion and does not provide professional medical diagnoses.</li>
            <li>You agree to our data collection, processing, and crisis management policies described above.</li>
          </ul>
        </div>

        {/* Scroll Progress indicator & Checkbox / Button */}
        <div className="space-y-4 flex-shrink-0 bg-bg3/20 border border-border/30 rounded-xl p-4">
          <div className="flex justify-between items-center text-[11px] text-text3">
            <span>Read Progress:</span>
            <span className="font-semibold text-accent">{Math.min(100, Math.round(scrollPercent))}%</span>
          </div>
          <div className="h-1 bg-bg4 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent transition-all duration-150"
              style={{ width: `${Math.min(100, scrollPercent)}%` }}
            />
          </div>

          <div className="flex flex-col gap-3 pt-1">
            <label
              className={`flex items-start gap-2.5 text-xs transition-opacity cursor-pointer ${
                hasScrolledToBottom ? 'opacity-100' : 'opacity-40'
              }`}
              onClick={handleCheckClick}
            >
              <input
                type="checkbox"
                disabled={!hasScrolledToBottom}
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="mt-0.5 rounded border-border bg-bg3 text-accent focus:ring-accent focus:ring-offset-bg cursor-pointer disabled:cursor-not-allowed"
              />
              <span className="text-text2 leading-normal">
                I have read and agree to the Privacy Policy & Terms of Service
              </span>
            </label>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
              <span className="text-[11px] text-text3">
                {hasScrolledToBottom ? (
                  <span className="text-green font-medium">✓ You've read to the end! Check the box to continue.</span>
                ) : (
                  <span>Keep scrolling to enable agreement...</span>
                )}
              </span>

              <button
                type="button"
                disabled={loading}
                onClick={handleSubmit}
                className={`w-full sm:w-auto px-6 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                  hasScrolledToBottom && agreed
                    ? 'bg-accent text-white hover:opacity-90'
                    : 'bg-accent/20 text-white/40'
                }`}
              >
                {loading ? 'Saving...' : 'I Agree & Continue'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
