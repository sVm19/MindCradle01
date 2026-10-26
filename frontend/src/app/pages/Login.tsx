import { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import Logo from '@/app/components/Logo';
import { ShieldAlert, Mail, ShieldCheck } from 'lucide-react';
import { getCognitoHostedUiUrl } from '@/lib/api';

export default function Login() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const handleCognitoClick = () => {
    if (!privacyAccepted) {
      setError('You must accept the Privacy Policy and Terms of Service to continue.');
      return;
    }
    const cognitoUrl = getCognitoHostedUiUrl();
    if (!cognitoUrl) {
      setError('AWS Cognito Hosted UI is not configured yet. Please configure VITE_COGNITO_DOMAIN and VITE_COGNITO_CLIENT_ID.');
      return;
    }
    setError('');
    window.location.href = cognitoUrl;
  };

  const handleMagicLinkClick = () => {
    if (!privacyAccepted) {
      setError('You must accept the Privacy Policy and Terms of Service to continue.');
      return;
    }
    setError('');
    navigate('/auth/magic-link');
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

        <div className="space-y-5">
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

          {/* AWS Cognito Button */}
          <button
            type="button"
            onClick={handleCognitoClick}
            className="w-full flex items-center justify-center gap-2.5 rounded-[14px] bg-bg3 border border-border text-text px-4 py-3.5 text-sm font-semibold hover:bg-bg3/80 hover:border-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent transition-all cursor-pointer shadow-sm group"
          >
            <ShieldCheck className="w-4 h-4 text-accent transition-transform group-hover:scale-110" />
            Continue with AWS Cognito
          </button>

          {/* Divider */}
          <div className="relative flex items-center justify-center py-1">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative bg-bg2 px-3 text-[11px] uppercase tracking-wider text-text3 font-medium">
              or
            </div>
          </div>

          {/* Email Magic Link Button */}
          <button
            type="button"
            onClick={handleMagicLinkClick}
            className="w-full flex items-center justify-center gap-2 rounded-[14px] bg-accent text-white px-4 py-3.5 text-sm font-semibold hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent transition-all cursor-pointer shadow-lg shadow-accent/20"
          >
            <Mail size={16} />
            Sign in with email link
          </button>

          <div className="bg-bg3/40 border border-border rounded-xl p-4 text-xs text-text3 leading-relaxed text-center">
            MindCradle uses enterprise-grade security. Accounts are created and synchronized automatically on first sign-in.
          </div>
        </div>
      </div>
    </div>
  );
}
