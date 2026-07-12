import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { Loader2, ShieldAlert } from 'lucide-react';
import { useAuth } from '@/lib/auth';

export default function MagicLinkCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { loginWithMagicToken, setVerifyModalOpen } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function completeLogin() {
      const token = searchParams.get('token');
      if (!token) {
        setError('This login link is missing its token.');
        return;
      }

      try {
        await loginWithMagicToken(token);
        if (!cancelled) {
          setVerifyModalOpen(true);
          navigate('/dashboard', { replace: true });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'This login link is invalid or expired.');
        }
      }
    }

    completeLogin();
    return () => {
      cancelled = true;
    };
  }, [loginWithMagicToken, navigate, searchParams, setVerifyModalOpen]);

  if (error) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center p-4 animate-fadeIn">
        <div className="w-full max-w-[420px] bg-bg2 border border-border rounded-[24px] px-8 py-8 shadow-2xl text-center">
          <div className="mx-auto mb-4 h-11 w-11 rounded-[14px] bg-rose/10 border border-rose/30 flex items-center justify-center">
            <ShieldAlert className="text-rose" size={20} />
          </div>
          <h1 className="text-xl font-light text-text mb-2">Login link failed</h1>
          <p className="text-sm text-text3 mb-6">{error}</p>
          <Link to="/auth/magic-link" className="text-sm text-accent hover:underline">
            Request a new link
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center bg-bg text-text">
      <Loader2 className="h-8 w-8 animate-spin text-accent mb-4" />
      <p className="text-sm font-medium tracking-wide text-text2">Completing sign in...</p>
    </div>
  );
}
