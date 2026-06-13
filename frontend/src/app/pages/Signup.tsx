import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useAuth } from '@/lib/auth';

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== passwordConfirm) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await signup(name, email, password, passwordConfirm);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign up failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg relative overflow-hidden">
      {/* Ambient orbs */}
      <div className="fixed w-[500px] h-[500px] rounded-full blur-[80px] bg-accent/8 -top-[150px] -right-[100px] pointer-events-none" />
      <div className="fixed w-[400px] h-[400px] rounded-full blur-[80px] bg-teal/6 bottom-[100px] -left-[100px] pointer-events-none" />

      <div className="w-full max-w-[380px] mx-auto px-6 relative z-10 animate-fadeIn">
        {/* Logo */}
        <div className="flex items-center gap-2.5 font-[family-name:var(--font-serif)] text-xl font-light text-text tracking-[0.02em] mb-10 justify-center">
          <div className="w-9 h-9 rounded-[10px] bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-base">
            🌊
          </div>
          MindCradle
        </div>

        <div className="bg-bg2 border border-border rounded-[24px] px-8 py-8">
          <div className="text-xs text-accent tracking-[0.1em] uppercase mb-2">Get started</div>
          <h1 className="text-2xl font-light text-text mb-6">Create account</h1>

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
                placeholder="Min. 8 characters"
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

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-[12px] font-medium text-sm hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {loading ? 'Creating account…' : 'Create account →'}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-text3 mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-accent hover:text-accent2 transition-colors">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
