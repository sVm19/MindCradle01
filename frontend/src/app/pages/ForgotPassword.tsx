import { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { auth as authApi } from '@/lib/api';
import Logo from '@/app/components/Logo';
import { Mail, CheckCircle2, ArrowLeft } from 'lucide-react';
import { validateEmail } from '@/lib/validation';

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleEmailBlur = () => {
    if (email.trim() === '') {
      setEmailError('Email is required');
    } else if (!validateEmail(email)) {
      setEmailError('Invalid email address');
    } else {
      setEmailError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    handleEmailBlur();

    if (email.trim() === '' || !validateEmail(email)) {
      setError('Please enter a valid email address.');
      return;
    }

    setLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
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
          Password Reset
        </div>
        <h1 className="text-2xl font-light text-text mb-6">
          Recover Your Password
        </h1>

        {success ? (
          <div className="space-y-6 text-center py-4">
            <div className="flex justify-center text-emerald-500">
              <CheckCircle2 size={56} className="animate-bounce" />
            </div>
            <div className="space-y-2">
              <h2 className="text-lg font-medium text-text">Check your inbox</h2>
              <p className="text-sm text-text3 leading-relaxed">
                If an account exists for <strong>{email}</strong>, we have sent a secure password reset link.
              </p>
            </div>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 text-sm text-accent hover:underline mt-4"
            >
              <ArrowLeft size={16} /> Back to Sign In
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <p className="text-sm text-text3 leading-relaxed mb-2">
              Enter your email address below and we will send you a link to securely recover your account.
            </p>

            {error && (
              <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3">
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs text-text3 uppercase tracking-wider">Email Address</label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onBlur={handleEmailBlur}
                  required
                  placeholder="you@example.com"
                  className={`w-full bg-bg3 border rounded-[12px] px-4 py-3 text-sm text-text placeholder:text-text3 focus:outline-none transition-colors ${
                    emailError ? 'border-rose/50 focus:border-rose' : 'border-border focus:border-accent/40'
                  }`}
                  disabled={loading}
                />
              </div>
              {emailError && (
                <div className="text-xs text-rose mt-1 flex items-center gap-1">
                  <span>{emailError}</span>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !!emailError || email.trim() === ''}
              className="w-full py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-[12px] font-medium text-sm hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-2 cursor-pointer shadow-lg shadow-accent/10"
            >
              {loading ? 'Sending link…' : 'Send reset link →'}
            </button>

            <div className="text-center pt-2">
              <Link
                to="/login"
                className="inline-flex items-center gap-2 text-xs text-text3 hover:text-text transition-colors"
              >
                <ArrowLeft size={14} /> Back to Sign In
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
