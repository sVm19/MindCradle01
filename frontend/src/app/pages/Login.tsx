import { useState } from 'react';
import { Link, Navigate } from 'react-router';
import Logo from '@/app/components/Logo';
import { ShieldAlert, ShieldCheck, ArrowRight } from 'lucide-react';
import { getCognitoHostedUiUrl } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function Login() {
  const { user } = useAuth();
  const [error, setError] = useState('');
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleCognitoClick = () => {
    if (!privacyAccepted) {
      setError('Please agree to the Privacy Policy and Terms of Service to continue.');
      return;
    }
    const cognitoUrl = getCognitoHostedUiUrl();
    if (!cognitoUrl) {
      setError('Cognito Hosted UI configuration missing.');
      return;
    }
    window.location.href = cognitoUrl;
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4 animate-fadeIn">
      <div className="w-full max-w-[420px] bg-bg2 border border-border rounded-[24px] px-8 py-8 relative shadow-2xl animate-slideIn text-left">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <Logo className="h-10 w-auto text-text" />
        </div>

        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">
          Secure Authentication
        </div>
        <h1 className="text-2xl font-light text-text mb-2">
          Sign In to MindCradle
        </h1>
        <p className="text-xs text-text3 mb-6 leading-relaxed">
          Sign in or create your account using AWS Cognito enterprise security. No email service setup required.
        </p>

        {error && (
          <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3 mb-5 flex items-start gap-2.5">
            <ShieldAlert className="shrink-0 mt-0.5" size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-4">
          <div className="flex items-start gap-2.5 w-full pt-1">
            <input
              type="checkbox"
              id="privacy-check-login-page"
              checked={privacyAccepted}
              onChange={(e) => setPrivacyAccepted(e.target.checked)}
              className="rounded border-border text-accent focus:ring-accent mt-0.5 cursor-pointer"
            />
            <label htmlFor="privacy-check-login-page" className="text-xs text-text3 leading-snug cursor-pointer select-none">
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

          {/* Primary Cognito Button */}
          <button
            type="button"
            onClick={handleCognitoClick}
            className="w-full flex items-center justify-center gap-2.5 rounded-[14px] bg-accent text-white px-4 py-3.5 text-sm font-semibold hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent transition-all cursor-pointer shadow-lg shadow-accent/20 group"
          >
            <ShieldCheck size={18} className="transition-transform group-hover:scale-110" />
            <span>Continue with AWS Cognito</span>
            <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
          </button>

          <div className="bg-bg3/40 border border-border rounded-xl p-3.5 text-xs text-text3 leading-relaxed text-center">
            AWS Cognito handles user verification, encryption, password recovery, and session security automatically.
          </div>
        </div>
      </div>
    </div>
  );
}
