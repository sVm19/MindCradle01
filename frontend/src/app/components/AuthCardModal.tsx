import { useState } from 'react';
import { Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import Logo from './Logo';
import { X, ShieldAlert, ShieldCheck, ArrowRight } from 'lucide-react';
import { getCognitoHostedUiUrl } from '@/lib/api';

export default function AuthCardModal() {
  const { authModalOpen, setAuthModalOpen } = useAuth();
  const [error, setError] = useState('');
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const handleClose = () => {
    setError('');
    setAuthModalOpen(false);
    sessionStorage.setItem('mc_signup_popup_shown', 'true');
  };

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
    handleClose();
    window.location.href = cognitoUrl;
  };

  if (!authModalOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="w-full max-w-[400px] bg-bg2 border border-border rounded-[24px] px-8 py-8 relative layer-4 animate-slideIn text-left">
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

        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">
          Secure Authentication
        </div>
        <h1 className="text-2xl font-light text-text mb-1.5">
          Join MindCradle
        </h1>
        <p className="text-xs text-text3 mb-5 leading-relaxed">
          Sign in or create your account using AWS Cognito enterprise security. No setup or manual verification required.
        </p>

        {error && (
          <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3 mb-5 flex items-start gap-2">
            <ShieldAlert className="shrink-0 mt-0.5" size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-4">
          <div className="flex items-start gap-2.5 w-full pt-1">
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

          <div className="bg-bg3/40 border border-border rounded-xl p-3 text-[11px] text-text3 leading-relaxed text-center">
            AWS Cognito handles user verification, encryption, and password recovery automatically.
          </div>
        </div>
      </div>
    </div>
  );
}
