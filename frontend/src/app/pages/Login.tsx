import { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { useGoogleLogin } from '@react-oauth/google';
import Logo from '@/app/components/Logo';
import { ShieldAlert, Loader2, Mail } from 'lucide-react';
import { auth as authApi } from '@/lib/api';

/* Inline Google "G" logo SVG — matches brand guidelines */
function GoogleIcon({ className = '' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <defs>
        <linearGradient id="mindcradle-google-gradient-login" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#f0eeff" />
          <stop offset="0.45" stopColor="#b76cff" />
          <stop offset="0.72" stopColor="#f093a0" />
          <stop offset="1" stopColor="#5c133a" />
        </linearGradient>
      </defs>
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="url(#mindcradle-google-gradient-login)"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="url(#mindcradle-google-gradient-login)"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 001 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z" fill="url(#mindcradle-google-gradient-login)"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="url(#mindcradle-google-gradient-login)"/>
    </svg>
  );
}

export default function Login() {
  const navigate = useNavigate();
  const { loginWithGoogleCode, setVerifyModalOpen } = useAuth();

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const googleLogin = useGoogleLogin({
    flow: 'auth-code',
    onSuccess: async (codeResponse) => {
      setError('');
      setLoading(true);
      try {
        if (!privacyAccepted) {
          throw new Error('You must accept the Privacy Policy and Terms of Service to continue.');
        }

        await loginWithGoogleCode(codeResponse.code);

        try {
          const verificationStatus = await authApi.checkAgeVerified();
          if (verificationStatus.age_verified) {
            localStorage.setItem('age_verified', 'true');
          } else {
            setVerifyModalOpen(true);
          }
        } catch {
          setVerifyModalOpen(true);
        }

        navigate('/', { replace: true });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Google authentication failed.');
      } finally {
        setLoading(false);
      }
    },
    onError: () => {
      setError('Google Sign-In was cancelled or failed.');
    },
  });

  const handleClick = () => {
    if (!privacyAccepted) {
      setError('You must accept the Privacy Policy and Terms of Service to continue.');
      return;
    }
    setError('');
    googleLogin();
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4 animate-fadeIn">
      <div className="w-full max-w-[420px] bg-bg2 border border-border rounded-[24px] px-8 py-8 relative shadow-2xl animate-slideIn text-left">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <Logo className="h-10 w-auto text-text" />
        </div>

        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">
          Secure Login & Registration
        </div>
        <h1 className="text-2xl font-light text-text mb-6">
          Sign in to MindCradle
        </h1>

        {error && (
          <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3 mb-5 flex items-start gap-2.5">
            <ShieldAlert className="shrink-0 mt-0.5" size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-6">
          <div className="flex items-start gap-3 w-full">
            <input
              type="checkbox"
              id="privacy-check-login-page"
              checked={privacyAccepted}
              onChange={(e) => setPrivacyAccepted(e.target.checked)}
              className="rounded border-border text-accent focus:ring-accent mt-1 cursor-pointer"
            />
            <label htmlFor="privacy-check-login-page" className="text-xs text-text3 leading-snug cursor-pointer">
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
            type="button"
            onClick={handleClick}
            disabled={loading}
            aria-label="Sign up or sign in with Google"
            title="Sign up or sign in with Google"
            className="mx-auto flex h-12 w-12 items-center justify-center rounded-[14px]
                       bg-bg3 border border-border2 shadow-[0_0_0_1px_rgba(255,255,255,0.04),0_12px_28px_rgba(0,0,0,0.28)]
                       hover:bg-bg4 hover:border-white/25 hover:shadow-[0_0_24px_var(--accent-glow),0_14px_32px_rgba(0,0,0,0.34)]
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-[#12071d]
                       active:scale-95
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200 cursor-pointer"
          >
            {loading ? (
              <Loader2 size={20} className="animate-spin text-text2" />
            ) : (
              <GoogleIcon className="h-7 w-7 drop-shadow-[0_2px_8px_rgba(255,255,255,0.18)]" />
            )}
            <span className="sr-only">{loading ? 'Signing in with Google' : 'Sign up or sign in with Google'}</span>
          </button>

          <p className="text-center text-xs text-rose font-medium">
            google OAuth is currently unavilable
          </p>

          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-[10px] uppercase tracking-[0.12em] text-text3">or</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <button
            type="button"
            onClick={() => navigate('/auth/magic-link')}
            className="w-full flex items-center justify-center gap-2 rounded-[14px] bg-bg3 border border-border2 px-4 py-3 text-sm font-medium text-text hover:bg-bg4 hover:border-white/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent transition-all cursor-pointer"
          >
            <Mail size={16} />
            Sign in with email link
          </button>

          <div className="bg-bg3/40 border border-border rounded-xl p-4 text-xs text-text3 leading-relaxed text-center">
            MindCradle uses secure, passwordless authentication. New accounts are created automatically the first time you sign in.
          </div>
        </div>
      </div>
    </div>
  );
}
