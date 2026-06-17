import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { auth as authApi } from '@/lib/api';
import Logo from '@/app/components/Logo';
import { ShieldAlert, Check } from 'lucide-react';

export default function Signup() {
  const navigate = useNavigate();
  const { signup, setVerifyModalOpen } = useAuth();
  
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [ageChecked, setAgeChecked] = useState(false);
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const accepted = localStorage.getItem('privacy_accepted') === 'true';
    setPrivacyAccepted(accepted);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!privacyAccepted) {
      setError('You must accept the Privacy Policy and Terms of Service to sign up.');
      return;
    }

    if (!ageChecked) {
      setError('You must be 18 years or older to register.');
      return;
    }

    if (password !== passwordConfirm) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      // 1. Create user account
      await signup(name, email, password, passwordConfirm);

      // 2. Set age_verified and privacy_accepted in localStorage
      localStorage.setItem('age_verified', 'true');
      localStorage.setItem('privacy_accepted', 'true');

      // 3. Set age_verified = true in database
      try {
        await authApi.verifyAge(true);
      } catch (dbErr) {
        console.error('Failed to save age verification to database:', dbErr);
      }

      // 4. Open/show the age verification modal
      setVerifyModalOpen(true);

      // 5. Redirect to Dashboard
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const isFormValid =
    email.trim() !== '' &&
    name.trim() !== '' &&
    password.trim() !== '' &&
    passwordConfirm.trim() !== '' &&
    ageChecked &&
    privacyAccepted;

  if (!privacyAccepted) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto space-y-6 animate-fadeIn">
        <div className="w-16 h-16 rounded-2xl bg-bg2 border border-border flex items-center justify-center text-accent shadow-lg shadow-accent/5">
          <ShieldAlert size={28} />
        </div>
        <h2 className="font-[family-name:var(--font-serif)] text-2xl font-light text-text">
          Privacy Policy Acceptance Required
        </h2>
        <p className="text-sm text-text3 leading-relaxed">
          To create a secure account on MindCradle, you must first read and accept our Privacy Policy & Terms of Service.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="px-6 py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-xl font-medium text-sm hover:opacity-90 transition-all shadow-lg shadow-accent/10 cursor-pointer"
        >
          View Privacy Policy
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4 animate-fadeIn">
      <div className="w-full max-w-[420px] bg-bg2 border border-border rounded-[24px] px-8 py-8 relative shadow-2xl animate-slideIn text-left">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <Logo className="h-10 w-auto text-text" />
        </div>

        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">Get started</div>
        <h1 className="text-2xl font-light text-text mb-6">Create your account</h1>

        {error && (
          <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-[12px] px-4 py-3 mb-5">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
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
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              placeholder="••••••••"
              className="w-full bg-bg3 border border-border rounded-[12px] px-4 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-text3 uppercase tracking-wider">Confirm password</label>
            <input
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              required
              placeholder="Repeat password"
              className="w-full bg-bg3 border border-border rounded-[12px] px-4 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 transition-colors"
            />
          </div>

          {/* Age Verification Checkbox */}
          <div className="pt-2">
            <label className="flex gap-3 items-start cursor-pointer group select-none bg-bg3/40 border border-border/40 rounded-xl p-3.5 hover:border-border transition-all">
              <div className="relative mt-0.5">
                <input
                  type="checkbox"
                  checked={ageChecked}
                  onChange={(e) => setAgeChecked(e.target.checked)}
                  className="sr-only"
                />
                <div className={`w-5 h-5 rounded border transition-all flex items-center justify-center ${ageChecked ? 'bg-accent border-accent text-white' : 'border-border bg-bg3 group-hover:border-border2'}`}>
                  {ageChecked && <Check size={14} />}
                </div>
              </div>
              <span className="text-xs text-text2 leading-relaxed">
                I am 18 years or older
              </span>
            </label>
          </div>

          <button
            type="submit"
            disabled={!isFormValid || loading}
            className={`w-full py-3 rounded-[12px] font-semibold text-sm transition-all cursor-pointer mt-4 ${
              isFormValid && !loading
                ? 'bg-gradient-to-r from-accent2 to-accent text-white hover:opacity-90 shadow-lg shadow-accent/10'
                : 'bg-accent/20 text-white/30 cursor-not-allowed'
            }`}
          >
            {loading ? 'Creating account…' : 'Create account →'}
          </button>
        </form>

        <div className="mt-6 text-center text-xs text-text3">
          Already have an account?{' '}
          <Link to="/login" className="text-accent hover:underline">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
