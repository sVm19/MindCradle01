import { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { GoogleLogin } from '@react-oauth/google';
import Logo from '@/app/components/Logo';
import { ShieldAlert } from 'lucide-react';
import { auth as authApi } from '@/lib/api';

export default function Login() {
  const navigate = useNavigate();
  const { loginWithGoogle, setVerifyModalOpen } = useAuth();

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

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

          <div className="w-full flex justify-center py-2">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError('Google Sign-In failed')}
              theme="outline"
              size="large"
              shape="pill"
              width="356"
            />
          </div>

          <div className="bg-bg3/40 border border-border rounded-xl p-4 text-xs text-text3 leading-relaxed text-center">
            MindCradle uses secure, passwordless authentication. If you don't have an account, logging in with Google will automatically create one.
          </div>
        </div>
      </div>
    </div>
  );
}
