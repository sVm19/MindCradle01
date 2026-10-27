import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { auth as authApi } from '@/lib/api';
import {
  ShieldAlert,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  Mail,
  Lock,
  User,
  ArrowRight,
  ArrowLeft,
  KeyRound,
} from 'lucide-react';

interface CognitoAuthFormProps {
  onSuccess?: () => void;
  initialTab?: 'signin' | 'signup';
  isModal?: boolean;
}

export default function CognitoAuthForm({
  onSuccess,
  initialTab = 'signin',
  isModal = false,
}: CognitoAuthFormProps) {
  const { loginWithCognitoDirect } = useAuth();

  const [tab, setTab] = useState<'signin' | 'signup'>(initialTab);
  const [showConfirm, setShowConfirm] = useState(false);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [confirmCode, setConfirmCode] = useState('');
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [countdown, setCountdown] = useState(0);

  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (countdown > 0) {
      timerRef.current = setTimeout(() => {
        setCountdown((c) => c - 1);
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [countdown]);

  const resetMessages = () => {
    setError('');
    setSuccessMsg('');
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();

    if (!email.trim() || !password) {
      setError('Please provide both email and password.');
      return;
    }

    setIsLoading(true);
    try {
      await loginWithCognitoDirect(email.trim(), password);
      onSuccess?.();
    } catch (err: any) {
      const msg = err?.message || 'Failed to sign in. Please check your credentials.';
      if (msg.includes('USER_NOT_CONFIRMED')) {
        setShowConfirm(true);
        setSuccessMsg('Your account is not yet verified. Please enter the 6-digit code sent to your email.');
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();

    if (!email.trim() || !password) {
      setError('Please provide an email and password.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (!privacyAccepted) {
      setError('Please agree to the Privacy Policy and Terms of Service to continue.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authApi.cognitoDirectSignup(email.trim(), password, name.trim() || undefined);
      if (res.requires_confirmation) {
        setShowConfirm(true);
        setCountdown(30);
        setSuccessMsg(`A 6-digit confirmation code has been sent to ${email.trim()}.`);
      } else {
        // Automatically sign in if confirmation is not required
        await loginWithCognitoDirect(email.trim(), password);
        onSuccess?.();
      }
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please check your inputs.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();

    if (!confirmCode.trim()) {
      setError('Please enter the 6-digit verification code.');
      return;
    }

    setIsLoading(true);
    try {
      await authApi.cognitoConfirmSignup(email.trim(), confirmCode.trim());

      // Attempt immediate login if password is in state
      if (password) {
        setSuccessMsg('Account verified! Signing you in...');
        try {
          await loginWithCognitoDirect(email.trim(), password);
          onSuccess?.();
          return;
        } catch {
          // If auto-login fails, fall back to sign in tab
        }
      }

      setShowConfirm(false);
      setTab('signin');
      setSuccessMsg('Account verified successfully! Please sign in with your password.');
    } catch (err: any) {
      setError(err?.message || 'Invalid or expired confirmation code.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (countdown > 0 || isResending) return;
    resetMessages();
    setIsResending(true);
    try {
      await authApi.cognitoResendCode(email.trim());
      setCountdown(30);
      setSuccessMsg(`A fresh verification code was sent to ${email.trim()}.`);
    } catch (err: any) {
      setError(err?.message || 'Failed to resend confirmation code.');
    } finally {
      setIsResending(false);
    }
  };

  // ── Confirmation Code View ───────────────────────────────────────────────
  if (showConfirm) {
    return (
      <div className="space-y-4 text-left">
        <div className="flex items-center gap-2 mb-1">
          <button
            type="button"
            onClick={() => {
              setShowConfirm(false);
              resetMessages();
            }}
            className="text-text3 hover:text-text transition-colors flex items-center gap-1 text-xs cursor-pointer"
          >
            <ArrowLeft size={14} />
            <span>Back</span>
          </button>
        </div>

        <div>
          <h2 className="text-xl font-light text-text mb-1 flex items-center gap-2">
            <KeyRound size={20} className="text-accent" />
            Verify Your Email
          </h2>
          <p className="text-xs text-text3 leading-relaxed">
            We sent a 6-digit code to <strong className="text-text font-medium">{email}</strong>. Enter it below to activate your account.
          </p>
        </div>

        {error && (
          <div className="bg-rose/10 border border-rose/30 text-rose text-xs rounded-[12px] px-3.5 py-2.5 flex items-start gap-2">
            <ShieldAlert className="shrink-0 mt-0.5" size={15} />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded-[12px] px-3.5 py-2.5 flex items-start gap-2">
            <CheckCircle2 className="shrink-0 mt-0.5" size={15} />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleConfirm} className="space-y-4">
          <div>
            <label className="block text-[11px] font-medium text-text3 uppercase tracking-wider mb-1.5">
              6-Digit Code
            </label>
            <input
              type="text"
              maxLength={6}
              value={confirmCode}
              onChange={(e) => setConfirmCode(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
              className="w-full text-center tracking-[0.35em] text-lg font-mono px-4 py-3 bg-bg3/60 border border-border rounded-[14px] text-text placeholder:text-text3/40 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
              autoFocus
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || confirmCode.length < 6}
            className="w-full flex items-center justify-center gap-2 rounded-[14px] bg-accent text-white px-4 py-3.5 text-sm font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer shadow-lg shadow-accent/20"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Verifying...</span>
              </>
            ) : (
              <>
                <span>Confirm Account</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>

          <div className="flex items-center justify-between text-xs text-text3 pt-1">
            <span>Didn&apos;t receive a code?</span>
            <button
              type="button"
              onClick={handleResendCode}
              disabled={countdown > 0 || isResending}
              className="text-accent hover:underline disabled:text-text3/50 disabled:no-underline font-medium cursor-pointer"
            >
              {countdown > 0 ? `Resend in ${countdown}s` : isResending ? 'Sending...' : 'Resend code'}
            </button>
          </div>
        </form>
      </div>
    );
  }

  // ── Tabbed Sign In / Sign Up View ─────────────────────────────────────────
  return (
    <div className="space-y-4 text-left">
      {/* Tab Switcher */}
      <div className="grid grid-cols-2 p-1 bg-bg3/70 border border-border/80 rounded-[14px]">
        <button
          type="button"
          onClick={() => {
            setTab('signin');
            resetMessages();
          }}
          className={`py-2 text-xs font-medium rounded-[10px] transition-all cursor-pointer ${
            tab === 'signin'
              ? 'bg-bg2 text-text shadow-sm'
              : 'text-text3 hover:text-text'
          }`}
        >
          Sign In
        </button>
        <button
          type="button"
          onClick={() => {
            setTab('signup');
            resetMessages();
          }}
          className={`py-2 text-xs font-medium rounded-[10px] transition-all cursor-pointer ${
            tab === 'signup'
              ? 'bg-bg2 text-text shadow-sm'
              : 'text-text3 hover:text-text'
          }`}
        >
          Create Account
        </button>
      </div>

      {error && (
        <div className="bg-rose/10 border border-rose/30 text-rose text-xs rounded-[12px] px-3.5 py-2.5 flex items-start gap-2">
          <ShieldAlert className="shrink-0 mt-0.5" size={15} />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded-[12px] px-3.5 py-2.5 flex items-start gap-2">
          <CheckCircle2 className="shrink-0 mt-0.5" size={15} />
          <span>{successMsg}</span>
        </div>
      )}

      {tab === 'signin' ? (
        /* Sign In Form */
        <form onSubmit={handleSignIn} className="space-y-3.5">
          <div>
            <label className="block text-[11px] font-medium text-text3 uppercase tracking-wider mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text3" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@domain.com"
                className="w-full pl-10 pr-3.5 py-2.5 bg-bg3/60 border border-border rounded-[14px] text-sm text-text placeholder:text-text3/50 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                autoComplete="email"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-text3 uppercase tracking-wider mb-1">
              Password
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text3" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Your password"
                className="w-full pl-10 pr-10 py-2.5 bg-bg3/60 border border-border rounded-[14px] text-sm text-text placeholder:text-text3/50 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-text3 hover:text-text transition-colors cursor-pointer"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 flex items-center justify-center gap-2 rounded-[14px] bg-accent text-white px-4 py-3 text-sm font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer shadow-lg shadow-accent/20"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Signing in...</span>
              </>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>
      ) : (
        /* Create Account Form */
        <form onSubmit={handleSignUp} className="space-y-3.5">
          <div>
            <label className="block text-[11px] font-medium text-text3 uppercase tracking-wider mb-1">
              Your Name <span className="text-text3/60 lowercase font-normal">(optional)</span>
            </label>
            <div className="relative">
              <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text3" />
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Alex Morgan"
                className="w-full pl-10 pr-3.5 py-2.5 bg-bg3/60 border border-border rounded-[14px] text-sm text-text placeholder:text-text3/50 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                autoComplete="name"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-text3 uppercase tracking-wider mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text3" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@domain.com"
                className="w-full pl-10 pr-3.5 py-2.5 bg-bg3/60 border border-border rounded-[14px] text-sm text-text placeholder:text-text3/50 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                autoComplete="email"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-text3 uppercase tracking-wider mb-1">
              Password <span className="text-text3/60 lowercase font-normal">(min 8 characters)</span>
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text3" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a strong password"
                className="w-full pl-10 pr-10 py-2.5 bg-bg3/60 border border-border rounded-[14px] text-sm text-text placeholder:text-text3/50 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-text3 hover:text-text transition-colors cursor-pointer"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="flex items-start gap-2.5 w-full pt-1">
            <input
              type="checkbox"
              id={`privacy-check-${isModal ? 'modal' : 'page'}`}
              checked={privacyAccepted}
              onChange={(e) => setPrivacyAccepted(e.target.checked)}
              className="w-4 h-4 rounded border-border text-accent focus:ring-accent shrink-0 cursor-pointer mt-0.5"
            />
            <label
              htmlFor={`privacy-check-${isModal ? 'modal' : 'page'}`}
              className="text-[11px] text-text3 leading-snug cursor-pointer select-none"
            >
              I agree to the{' '}
              <Link to="/privacy" className="text-accent hover:underline">
                Privacy Policy
              </Link>{' '}
              and{' '}
              <Link to="/terms" className="text-accent hover:underline">
                Terms of Service
              </Link>
            </label>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 flex items-center justify-center gap-2 rounded-[14px] bg-accent text-white px-4 py-3 text-sm font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer shadow-lg shadow-accent/20"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Creating account...</span>
              </>
            ) : (
              <>
                <span>Create Account</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>
      )}

      <div className="bg-bg3/30 border border-border/60 rounded-xl p-3 text-[11px] text-text3 leading-relaxed text-center">
        Secured directly with Amazon Cognito encryption and verification.
      </div>
    </div>
  );
}
