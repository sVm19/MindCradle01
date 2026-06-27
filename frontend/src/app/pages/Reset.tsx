import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router';
import { auth as authApi } from '@/lib/api';
import Logo from '@/app/components/Logo';
import { Eye, EyeOff, CheckCircle2, AlertCircle } from 'lucide-react';
import { validatePassword } from '@/lib/validation';

export default function Reset() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);

  const [passwordError, setPasswordError] = useState('');
  const [passwordConfirmError, setPasswordConfirmError] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handlePasswordBlur = () => {
    const err = validatePassword(password);
    setPasswordError(err || '');
  };

  const handlePasswordConfirmBlur = () => {
    if (passwordConfirm !== password) {
      setPasswordConfirmError('Passwords do not match');
    } else {
      setPasswordConfirmError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('Invalid reset token. Please request a new link.');
      return;
    }

    handlePasswordBlur();
    handlePasswordConfirmBlur();

    const pwdErr = validatePassword(password);
    if (pwdErr || passwordConfirm !== password) {
      setError('Please correct password validation errors before continuing.');
      return;
    }

    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password. Please try again.');
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
          Recovery
        </div>
        <h1 className="text-2xl font-light text-text mb-6">
          Reset Password
        </h1>

        {!token && (
          <div className="space-y-4 text-center py-4">
            <div className="flex justify-center text-rose">
              <AlertCircle size={48} />
            </div>
            <div className="space-y-2">
              <h2 className="text-lg font-medium text-text">Invalid reset link</h2>
              <p className="text-sm text-text3 leading-relaxed">
                The password reset token is missing from your link. Please check your email or request a new reset link.
              </p>
            </div>
            <div className="pt-4">
              <Link
                to="/forgot-password"
                className="px-5 py-2.5 bg-gradient-to-r from-accent2 to-accent text-white rounded-xl font-medium text-sm hover:opacity-90 transition-all shadow-md shadow-accent/10 cursor-pointer"
              >
                Request new link
              </Link>
            </div>
          </div>
        )}

        {token && success && (
          <div className="space-y-6 text-center py-4">
            <div className="flex justify-center text-emerald-500">
              <CheckCircle2 size={56} className="animate-bounce" />
            </div>
            <div className="space-y-2">
              <h2 className="text-lg font-medium text-text">Password updated</h2>
              <p className="text-sm text-text3 leading-relaxed">
                Your password has been successfully reset. You can now log in using your new credentials.
              </p>
            </div>
            <div className="pt-4">
              <Link
                to="/login"
                className="px-6 py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-xl font-medium text-sm hover:opacity-90 transition-all shadow-lg shadow-accent/10 cursor-pointer"
              >
                Sign In Now
              </Link>
            </div>
          </div>
        )}

        {token && !success && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <p className="text-sm text-text3 leading-relaxed mb-2">
              Enter your new password below. It must be at least 8 characters long, contain an uppercase letter, a number, and a special character.
            </p>

            {error && (
              <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3">
                {error}
              </div>
            )}

            {/* Password input */}
            <div className="space-y-1.5">
              <label className="text-xs text-text3 uppercase tracking-wider">New Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={handlePasswordBlur}
                  required
                  placeholder="••••••••"
                  className={`w-full bg-bg3 border rounded-[12px] pl-4 pr-11 py-3 text-sm text-text placeholder:text-text3 focus:outline-none transition-colors ${
                    passwordError ? 'border-rose/50 focus:border-rose' : 'border-border focus:border-accent/40'
                  }`}
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-black hover:text-black/80 cursor-pointer transition-colors focus:outline-none"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {passwordError && (
                <div className="text-xs text-rose mt-1">
                  <span>{passwordError}</span>
                </div>
              )}
            </div>

            {/* Password Confirm input */}
            <div className="space-y-1.5">
              <label className="text-xs text-text3 uppercase tracking-wider">Confirm New Password</label>
              <div className="relative">
                <input
                  type={showPasswordConfirm ? 'text' : 'password'}
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  onBlur={handlePasswordConfirmBlur}
                  required
                  placeholder="Repeat new password"
                  className={`w-full bg-bg3 border rounded-[12px] pl-4 pr-11 py-3 text-sm text-text placeholder:text-text3 focus:outline-none transition-colors ${
                    passwordConfirmError ? 'border-rose/50 focus:border-rose' : 'border-border focus:border-accent/40'
                  }`}
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-black hover:text-black/80 cursor-pointer transition-colors focus:outline-none"
                  aria-label={showPasswordConfirm ? "Hide confirm password" : "Show confirm password"}
                >
                  {showPasswordConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {passwordConfirmError && (
                <div className="text-xs text-rose mt-1">
                  <span>{passwordConfirmError}</span>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !!passwordError || !!passwordConfirmError || password.trim() === ''}
              className="w-full py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-[12px] font-medium text-sm hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-2 cursor-pointer shadow-lg shadow-accent/10"
            >
              {loading ? 'Resetting password…' : 'Reset password →'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
