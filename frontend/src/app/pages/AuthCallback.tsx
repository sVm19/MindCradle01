import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { AlertCircle, ArrowLeft } from 'lucide-react';

export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { loginWithCognito } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const handledRef = useRef(false);

  useEffect(() => {
    if (handledRef.current) return;

    const code = searchParams.get('code');
    const authError = searchParams.get('error_description') || searchParams.get('error');

    if (authError) {
      handledRef.current = true;
      setError(decodeURIComponent(authError));
      return;
    }

    if (code) {
      handledRef.current = true;
      const redirectUri = `${window.location.origin}/auth/callback`;

      loginWithCognito(code, redirectUri)
        .then(() => {
          navigate('/dashboard', { replace: true });
        })
        .catch((err) => {
          console.error('Cognito sign-in callback failed:', err);
          setError(err instanceof Error ? err.message : 'Failed to complete Cognito sign in');
        });
    } else {
      // No code in query parameters, redirect to home
      handledRef.current = true;
      navigate('/', { replace: true });
    }
  }, [loginWithCognito, navigate, searchParams]);

  if (error) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center p-4 animate-fadeIn">
        <div className="w-full max-w-[420px] bg-bg2 border border-border rounded-[24px] px-8 py-8 shadow-2xl text-left">
          <div className="w-12 h-12 rounded-full bg-rose/10 border border-rose/30 flex items-center justify-center text-rose mb-4">
            <AlertCircle size={24} />
          </div>
          <h2 className="text-xl font-medium text-text mb-2">Authentication Failed</h2>
          <p className="text-sm text-text3 mb-6 leading-relaxed">
            {error}
          </p>
          <Link
            to="/login"
            className="w-full flex items-center justify-center gap-2 rounded-[14px] bg-accent text-white px-4 py-3 text-sm font-semibold hover:opacity-90 transition-all shadow-lg shadow-accent/20"
          >
            <ArrowLeft size={16} />
            Back to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center bg-bg text-text p-4">
      <div className="w-10 h-10 rounded-full border-3 border-accent border-t-transparent animate-spin mb-4" />
      <h3 className="text-base font-medium tracking-wide text-text mb-1">
        Authenticating with AWS Cognito
      </h3>
      <p className="text-xs text-text3 tracking-wide">
        Securely validating session and syncing your account...
      </p>
    </div>
  );
}
