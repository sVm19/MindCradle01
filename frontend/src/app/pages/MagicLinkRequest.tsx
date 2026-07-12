import { FormEvent, useState } from 'react';
import { Link } from 'react-router';
import { Mail, Loader2, ShieldAlert, CheckCircle2 } from 'lucide-react';
import Logo from '@/app/components/Logo';
import { auth as authApi } from '@/lib/api';
import { sanitizeForInput } from '@/lib/sanitize';

export default function MagicLinkRequest() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      await authApi.requestMagicLink(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send login link.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4 animate-fadeIn">
      <div className="w-full max-w-[420px] bg-bg2 border border-border rounded-[24px] px-8 py-8 shadow-2xl animate-slideIn text-left">
        <div className="flex justify-center mb-6">
          <Logo className="h-10 w-auto text-text" />
        </div>

        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">
          Passwordless Access
        </div>
        <h1 className="text-2xl font-light text-text mb-3">
          Sign in with email
        </h1>
        <p className="text-sm text-text3 leading-relaxed mb-6">
          Enter your email and MindCradle will send a secure sign-in link.
        </p>

        {error && (
          <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3 mb-5 flex items-start gap-2.5">
            <ShieldAlert className="shrink-0 mt-0.5" size={16} />
            <span>{error}</span>
          </div>
        )}

        {sent ? (
          <div className="space-y-5">
            <div className="bg-green-dim border border-green/30 text-text rounded-[14px] px-4 py-4 flex gap-3">
              <CheckCircle2 className="text-green shrink-0 mt-0.5" size={18} />
              <div>
                <div className="text-sm font-medium">Check your email</div>
                <p className="text-xs text-text3 mt-1 leading-relaxed">
                  We sent a login link to {email}. It expires in 15 minutes.
                </p>
              </div>
            </div>
            <Link to="/login" className="block text-center text-xs text-accent hover:underline">
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <label className="block">
              <span className="text-xs text-text2 font-medium">Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(sanitizeForInput(event.target.value))}
                required
                autoComplete="email"
                placeholder="you@example.com"
                className="mt-2 w-full bg-bg3 border border-border rounded-[14px] px-4 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 transition-colors"
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-[14px] bg-bg3 border border-border2 px-4 py-3 text-sm font-medium text-text hover:bg-bg4 hover:border-white/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Mail size={16} />}
              {loading ? 'Sending link...' : 'Send magic link'}
            </button>

            <Link to="/login" className="block text-center text-xs text-text3 hover:text-text transition-colors">
              Use another sign-in method
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
