import { useState } from 'react';
import { Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import Logo from './Logo';
import { auth as authApi } from '@/lib/api';
import { X, ShieldAlert } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';

export default function AuthCardModal() {
  const { authModalOpen, setAuthModalOpen, setVerifyModalOpen, loginWithGoogle } = useAuth();
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!authModalOpen) return null;

  const handleClose = () => {
    setError('');
    setPrivacyAccepted(false);
    setAuthModalOpen(false);
  };

  const handleGoogleSuccess = async (credentialResponse: any) => {
    setError('');
    setLoading(true);
    try {
      if (!privacyAccepted) {
        throw new Error('You must accept the Privacy Policy and Terms of Service to continue.');
      }

      await loginWithGoogle(credentialResponse.credential);

      try {
        const verificationStatus = await authApi.checkAgeVerified();
        if (verificationStatus.age_verified) {
          localStorage.setItem('age_verified', 'true');
          handleClose();
        } else {
          setVerifyModalOpen(true);
          handleClose();
        }
      } catch {
        setVerifyModalOpen(true);
        handleClose();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn">
      <div className="w-full max-w-[390px] bg-bg2 border border-border rounded-[24px] px-8 py-8 relative shadow-2xl animate-slideIn">
        {/* Close button */}
        <button
          type="button"
          onClick={handleClose}
          className="absolute top-5 right-5 text-text3 hover:text-text cursor-pointer transition-colors"
          aria-label="Close"
        >
          <X size={18} />
        </button>

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
          <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3 mb-5 flex items-start gap-2">
            <ShieldAlert className="shrink-0 mt-0.5" size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-6">
          <div className="flex items-start gap-2.5 w-full text-left">
            <input
              type="checkbox"
              id="privacy-check-modal"
              checked={privacyAccepted}
              onChange={(e) => setPrivacyAccepted(e.target.checked)}
              className="rounded border-border text-accent focus:ring-accent mt-0.5 cursor-pointer"
            />
            <label htmlFor="privacy-check-modal" className="text-[11px] text-text3 leading-snug cursor-pointer">
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

          <div className="w-full flex justify-center">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError('Google authentication failed')}
              theme="outline"
              size="large"
              shape="pill"
              width="326"
            />
          </div>

          <div className="bg-bg3/40 border border-border rounded-xl p-3.5 text-[11px] text-text3 leading-relaxed text-center">
            MindCradle uses secure, passwordless authentication. Accounts are created instantly on first Google login.
          </div>
        </div>
      </div>
    </div>
  );
}
