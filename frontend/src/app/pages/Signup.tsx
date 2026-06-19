import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { auth as authApi } from '@/lib/api';
import Logo from '@/app/components/Logo';
import { ShieldAlert, Check, Eye, EyeOff } from 'lucide-react';
import { validateEmail, validatePassword } from '@/lib/validation';
import { sanitizeForInput } from '@/lib/sanitize';

export default function Signup() {
  const navigate = useNavigate();
  const { signup, setVerifyModalOpen } = useAuth();
  
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);

  const [emailError, setEmailError] = useState('');
  const [nameError, setNameError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordConfirmError, setPasswordConfirmError] = useState('');
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const accepted = localStorage.getItem('privacy_accepted') === 'true';
    setPrivacyAccepted(accepted);
  }, []);

  const handleNameBlur = () => {
    if (name.trim() === '') {
      setNameError('Name is required');
    } else if (name.length > 255) {
      setNameError('Name must be 255 characters or less');
    } else {
      setNameError('');
    }
  };

  const handleEmailBlur = () => {
    if (email.trim() === '') {
      setEmailError('Email is required');
    } else if (!validateEmail(email)) {
      setEmailError('Invalid email address');
    } else {
      setEmailError('');
    }
  };

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

    // Trigger all validations on submit to be sure
    handleNameBlur();
    handleEmailBlur();
    handlePasswordBlur();
    handlePasswordConfirmBlur();

    if (
      name.trim() === '' ||
      name.length > 255 ||
      !validateEmail(email) ||
      validatePassword(password) ||
      passwordConfirm !== password
    ) {
      setError('Please fix the validation errors before signing up.');
      return;
    }

    if (!privacyAccepted) {
      setError('You must accept the Privacy Policy and Terms of Service to sign up.');
      return;
    }

    setLoading(true);
    try {
      // 1. Create user account
      await signup(name, email, password, passwordConfirm);

      // 2. Set privacy_accepted in localStorage
      localStorage.setItem('privacy_accepted', 'true');

      // 3. Open/show the age verification modal
      setVerifyModalOpen(true);

      // 4. Redirect to Dashboard
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
    privacyAccepted &&
    emailError === '' &&
    nameError === '' &&
    passwordError === '' &&
    passwordConfirmError === '';

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
              onChange={(e) => setName(sanitizeForInput(e.target.value))}
              onBlur={handleNameBlur}
              required
              placeholder="Your name"
              className="w-full bg-bg3 border border-border rounded-[12px] px-4 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 transition-colors"
            />
            {nameError && <span className="text-xs text-rose mt-1 block">{nameError}</span>}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-text3 uppercase tracking-wider">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={handleEmailBlur}
              required
              placeholder="you@example.com"
              className="w-full bg-bg3 border border-border rounded-[12px] px-4 py-3 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 transition-colors"
            />
            {emailError && <span className="text-xs text-rose mt-1 block">{emailError}</span>}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-text3 uppercase tracking-wider">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onBlur={handlePasswordBlur}
                required
                minLength={8}
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
            {passwordError && <span className="text-xs text-rose mt-1 block">{passwordError}</span>}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-text3 uppercase tracking-wider">Confirm password</label>
            <div className="relative">
              <input
                type={showPasswordConfirm ? 'text' : 'password'}
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                onBlur={handlePasswordConfirmBlur}
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
            {passwordConfirmError && <span className="text-xs text-rose mt-1 block">{passwordConfirmError}</span>}
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
