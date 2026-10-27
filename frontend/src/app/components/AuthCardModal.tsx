import { FormEvent, useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router';
import { useAuth } from '@/lib/auth';
import Logo from './Logo';
import { X, ShieldAlert, Mail, Loader2, CheckCircle2, ArrowRight } from 'lucide-react';
import { auth as authApi } from '@/lib/api';
import { sanitizeForInput } from '@/lib/sanitize';

export default function AuthCardModal() {
  const navigate = useNavigate();
  const { authModalOpen, setAuthModalOpen, loginWithSessionData } = useAuth();
  
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [waiting, setWaiting] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const handleClose = () => {
    setError('');
    setSent(false);
    setWaiting(false);
    setSessionId('');
    setAuthModalOpen(false);
    sessionStorage.setItem('mc_signup_popup_shown', 'true');
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!privacyAccepted) {
      setError('Please agree to the Privacy Policy and Terms of Service to continue.');
      return;
    }
    setLoading(true);
    setError('');

    try {
      const cleanEmail = sanitizeForInput(email).trim().toLowerCase();
      const data = await authApi.requestMagicLink(cleanEmail);
      setSent(true);
      if (data.session_id) {
        setSessionId(data.session_id);
        setWaiting(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send magic sign-in link.');
    } finally {
      setLoading(false);
    }
  };

  // Poll for magic link completion across tabs/devices
  useEffect(() => {
    let intervalId: any;

    if (sent && waiting && sessionId) {
      let attempts = 0;
      const maxAttempts = 120; // 10 minutes

      intervalId = setInterval(async () => {
        attempts++;
        try {
          const checkRes = await authApi.checkSessionStatus(sessionId);
          if (checkRes.verified && checkRes.token) {
            clearInterval(intervalId);
            loginWithSessionData({
              token: checkRes.token,
              user_id: checkRes.user_id,
              name: checkRes.name || '',
              email: checkRes.email || '',
            });
            handleClose();
            navigate('/dashboard', { replace: true });
          }
        } catch {
          // Keep polling silently
        }

        if (attempts >= maxAttempts) {
          clearInterval(intervalId);
          setWaiting(false);
        }
      }, 4000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [sent, waiting, sessionId, loginWithSessionData, navigate]);

  if (!authModalOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="w-full max-w-[400px] bg-bg2 border border-border rounded-[24px] px-8 py-8 relative layer-4 animate-slideIn">
        {/* Close button */}
        <button
          type="button"
          onClick={handleClose}
          className="absolute top-5 right-5 w-10 h-10 min-w-[40px] min-h-[40px] flex items-center justify-center text-text3 hover:text-text hover:bg-bg3/60 rounded-full cursor-pointer transition-colors"
          aria-label="Close"
        >
          <X size={18} />
        </button>

        {/* Logo */}
        <div className="flex justify-center mb-5">
          <Logo className="h-10 w-auto text-text" />
        </div>

        {sent ? (
          <div className="text-center py-2 animate-fadeIn">
            <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto mb-4">
              <CheckCircle2 size={28} />
            </div>
            <h2 className="text-xl font-light text-text mb-2">Check your inbox</h2>
            <p className="text-xs text-text3 leading-relaxed mb-6">
              We sent a passwordless sign-in link to <span className="text-text font-medium">{email}</span>. Click the link in your email to instantly enter.
            </p>
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => setSent(false)}
                className="w-full py-2.5 px-4 rounded-xl bg-bg3 text-xs text-text2 hover:text-text hover:bg-bg3/80 transition-all font-medium"
              >
                Use a different email
              </button>
              <p className="text-[11px] text-text3">
                Waiting for confirmation... this window will log in automatically.
              </p>
            </div>
          </div>
        ) : (
          <div>
            <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">
              Welcome to MindCradle
            </div>
            <h1 className="text-2xl font-light text-text mb-1.5">
              Begin Your Journey
            </h1>
            <p className="text-xs text-text3 mb-5 leading-relaxed">
              Enter your email to sign in or create your personal wellness sanctuary. No passwords needed.
            </p>

            {error && (
              <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3 mb-5 flex items-start gap-2">
                <ShieldAlert className="shrink-0 mt-0.5" size={16} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="modal-email-input" className="block text-xs text-text2 font-medium mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-text3">
                    <Mail size={16} />
                  </div>
                  <input
                    type="email"
                    id="modal-email-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    autoFocus
                    className="w-full pl-10 pr-4 py-3 bg-bg3/60 border border-border rounded-[14px] text-text placeholder-text3 text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                  />
                </div>
              </div>

              <div className="flex items-start gap-2.5 w-full text-left pt-1">
                <input
                  type="checkbox"
                  id="privacy-check-modal"
                  checked={privacyAccepted}
                  onChange={(e) => setPrivacyAccepted(e.target.checked)}
                  className="w-4 h-4 rounded border-border text-accent focus:ring-accent shrink-0 cursor-pointer mt-0.5"
                />
                <label htmlFor="privacy-check-modal" className="text-[11px] text-text3 leading-snug cursor-pointer select-none">
                  I agree to the{' '}
                  <Link to="/privacy" onClick={handleClose} className="text-accent hover:underline">
                    Privacy Policy
                  </Link>{' '}
                  and{' '}
                  <Link to="/terms" onClick={handleClose} className="text-accent hover:underline">
                    Terms of Service
                  </Link>
                </label>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 rounded-[14px] bg-accent text-white px-4 py-3.5 text-sm font-semibold hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent transition-all cursor-pointer shadow-lg shadow-accent/20 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Sending link...
                  </>
                ) : (
                  <>
                    <span>Continue with Magic Link</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>

              <div className="bg-bg3/40 border border-border rounded-xl p-3 text-[11px] text-text3 leading-relaxed text-center">
                We'll email you a secure link. Accounts are created automatically on first sign-in.
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
