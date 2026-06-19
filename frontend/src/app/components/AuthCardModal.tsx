import { useState, useEffect } from 'react';
import { useLocation } from 'react-router';
import { useAuth } from '@/lib/auth';
import Logo from './Logo';
import { auth as authApi } from '@/lib/api';
import { X, Eye, EyeOff } from 'lucide-react';

export default function AuthCardModal() {
  const { authModalOpen, setAuthModalOpen, setVerifyModalOpen, login, signup } = useAuth();
  const location = useLocation();
  const [isLogin, setIsLogin] = useState(true);

  useEffect(() => {
    if (authModalOpen && location.state?.isSignUp) {
      setIsLogin(false);
    }
  }, [authModalOpen, location.state]);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!authModalOpen) return null;

  const handleClose = () => {
    setError('');
    setEmail('');
    setPassword('');
    setName('');
    setPasswordConfirm('');
    setShowPassword(false);
    setShowPasswordConfirm(false);
    setAuthModalOpen(false);
  };

  const handleSwitchTab = (toLogin: boolean) => {
    setError('');
    setShowPassword(false);
    setShowPasswordConfirm(false);
    setIsLogin(toLogin);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!isLogin && password !== passwordConfirm) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await signup(name, email, password, passwordConfirm);
      }

      // Check age verification status
      const localVerified = localStorage.getItem('age_verified');
      if (localVerified === 'true' || localVerified === 'false') {
        handleClose();
        return;
      }

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
      setError(err instanceof Error ? err.message : `${isLogin ? 'Login' : 'Signup'} failed`);
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

        {/* Tab Selector */}
        <div className="flex bg-bg3/60 border border-border/40 rounded-xl p-1 mb-6">
          <button
            type="button"
            onClick={() => handleSwitchTab(true)}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
              isLogin ? 'bg-accent text-white shadow-md' : 'text-text3 hover:text-text'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => handleSwitchTab(false)}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
              !isLogin ? 'bg-accent text-white shadow-md' : 'text-text3 hover:text-text'
            }`}
          >
            Sign Up
          </button>
        </div>

        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">
          {isLogin ? 'Welcome back' : 'Get started'}
        </div>
        <h1 className="text-2xl font-light text-text mb-6">
          {isLogin ? 'Sign in' : 'Create account'}
        </h1>

        {error && (
          <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3 mb-5">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div className="space-y-1.5">
              <label className="text-xs text-text3 uppercase tracking-wider">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="Your name"
                className="w-full bg-bg3 border border-border rounded-[12px] px-4 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 transition-colors"
              />
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs text-text3 uppercase tracking-wider">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              className="w-full bg-bg3 border border-border rounded-[12px] px-4 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-text3 uppercase tracking-wider">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={isLogin ? undefined : 8}
                placeholder="••••••••"
                className="w-full bg-bg3 border border-border rounded-[12px] pl-4 pr-11 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 transition-colors"
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
          </div>

          {!isLogin && (
            <div className="space-y-1.5">
              <label className="text-xs text-text3 uppercase tracking-wider">Confirm password</label>
              <div className="relative">
                <input
                  type={showPasswordConfirm ? 'text' : 'password'}
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  required
                  placeholder="Repeat password"
                  className="w-full bg-bg3 border border-border rounded-[12px] pl-4 pr-11 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 transition-colors"
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
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-[12px] font-medium text-sm hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-2 cursor-pointer"
          >
            {loading ? (isLogin ? 'Signing in…' : 'Creating account…') : (isLogin ? 'Sign in →' : 'Create account →')}
          </button>
        </form>
      </div>
    </div>
  );
}
