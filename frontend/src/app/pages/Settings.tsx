import { useNavigate } from 'react-router';
import { useAuth, getInitials } from '@/lib/auth';

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const initials = user ? getInitials(user.name || user.email) : '?';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-4">ACCOUNT</div>
        <h1 className="text-3xl font-light text-text mb-2">Settings</h1>
      </div>

      {/* Profile Card */}
      <section className="bg-bg2 border border-border rounded-[20px] px-6 py-6">
        <div className="text-xs text-text3 uppercase tracking-wider mb-5">Profile</div>
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-xl font-medium text-white flex-shrink-0">
            {initials}
          </div>
          <div>
            <div className="text-base font-medium text-text">{user?.name || '—'}</div>
            <div className="text-sm text-text3 mt-0.5">{user?.email}</div>
          </div>
        </div>
      </section>

      {/* App Info */}
      <section className="bg-bg2 border border-border rounded-[20px] px-6 py-6 space-y-4">
        <div className="text-xs text-text3 uppercase tracking-wider mb-2">About</div>
        {[
          { label: 'App', value: 'MindCradle' },
          { label: 'Version', value: '0.1.0' },
          { label: 'Backend', value: 'FastAPI + PocketBase' },
          { label: 'AI Companion', value: 'ARIA (Gemma · OpenRouter)' },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center justify-between text-sm">
            <span className="text-text3">{label}</span>
            <span className="text-text">{value}</span>
          </div>
        ))}
      </section>

      {/* Privacy Note */}
      <section className="bg-bg3/60 border border-border rounded-[14px] px-5 py-4">
        <div className="flex gap-3">
          <div className="text-lg">🔒</div>
          <div>
            <div className="text-sm text-text mb-1">Your data is private</div>
            <div className="text-xs text-text2">
              All journal entries, mood logs, and conversations are stored securely and are only visible to you. ARIA conversations are context-aware but not shared with third parties.
            </div>
          </div>
        </div>
      </section>

      {/* Danger Zone */}
      <section className="bg-bg2 border border-rose/20 rounded-[20px] px-6 py-6">
        <div className="text-xs text-rose/70 uppercase tracking-wider mb-4">Account</div>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-text font-medium">Sign out</div>
            <div className="text-xs text-text3 mt-0.5">You'll need to sign in again to access your data.</div>
          </div>
          <button
            onClick={handleLogout}
            className="px-5 py-2.5 bg-rose/10 border border-rose/30 text-rose rounded-[10px] text-sm font-medium hover:bg-rose/20 transition-all"
          >
            Sign out
          </button>
        </div>
      </section>
    </div>
  );
}
