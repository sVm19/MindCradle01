import { Link, useLocation } from 'react-router';
import { useEffect, useState } from 'react';
import { useAuth, getInitials } from '@/lib/auth';
import { mood as moodApi } from '@/lib/api';

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user } = useAuth();
  const [streak, setStreak] = useState(0);

  // Fetch streak from mood history — count unique dates in last 7 days
  useEffect(() => {
    moodApi.history('7d').then((res) => {
      const uniqueDates = new Set(res.items.map((item) => item.created.slice(0, 10)));
      setStreak(uniqueDates.size);
    }).catch(() => {/* silently ignore if API is unavailable */});
  }, []);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: '⊞' },
    { path: '/morning', label: 'Morning', icon: '☀' },
    { path: '/mood', label: 'Mood', icon: '◎' },
    { path: '/journal', label: 'Journal', icon: '◫' },
    { path: '/aria', label: 'ARIA', icon: '✦' },
    { path: '/wind-down', label: 'Wind Down', icon: '☽' },
  ];

  const initials = user ? getInitials(user.name || user.email) : '?';

  return (
    <>
      {/* Ambient orbs */}
      <div className="fixed w-[500px] h-[500px] rounded-full blur-[80px] bg-accent/8 -top-[150px] -right-[100px] pointer-events-none z-0" />
      <div className="fixed w-[400px] h-[400px] rounded-full blur-[80px] bg-teal/6 bottom-[100px] -left-[100px] pointer-events-none z-0" />
      <div className="fixed w-[300px] h-[300px] rounded-full blur-[80px] bg-rose/5 top-1/2 left-[40%] pointer-events-none z-0" />

      <div className="flex min-h-screen relative z-[1]">
        {/* Sidebar */}
        <nav className="w-[220px] flex-shrink-0 bg-bg2/70 border-r border-border backdrop-blur-[20px] py-7 flex flex-col fixed top-0 left-0 bottom-0">
          <div className="px-6 pb-8 border-b border-border">
            <div className="flex items-center gap-2.5 font-[family-name:var(--font-serif)] text-xl font-light text-text tracking-[0.02em]">
              <div className="w-8 h-8 rounded-[10px] bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-sm">
                🌊
              </div>
              MindCradle
            </div>
          </div>

          <div className="flex-1 px-3 py-5 flex flex-col gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[13.5px] transition-all ${
                    isActive
                      ? 'bg-accent-glow text-accent border border-accent/20'
                      : 'text-text2 hover:bg-white/5 hover:text-text'
                  }`}
                >
                  <span className={`text-base ${isActive ? 'opacity-100' : 'opacity-80'}`}>
                    {item.icon}
                  </span>
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Streak pill */}
          <div className="mx-6 mb-4 px-3.5 py-2.5 bg-amber-dim border border-amber/20 rounded-[14px] flex items-center gap-2 text-xs text-amber">
            <span>🔥</span>
            <div>
              <strong className="text-lg font-medium font-[family-name:var(--font-serif)]">{streak}</strong>
              <div className="text-[10px] opacity-80 mt-0.5">day streak</div>
            </div>
          </div>

          <div className="px-3 pt-4 border-t border-border flex flex-col gap-2">
            <Link
              to="/settings"
              className="flex items-center gap-3 px-3.5 py-2.5 text-[12.5px] text-text3 hover:bg-white/5 rounded-lg transition-all"
            >
              <span className="text-base opacity-80">⚙</span> Settings
            </Link>

            {/* User pill */}
            {user && (
              <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-lg">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-[11px] font-medium text-white flex-shrink-0">
                  {initials}
                </div>
                <div className="min-w-0">
                  <div className="text-[12px] text-text truncate">{user.name || 'You'}</div>
                  <div className="text-[10px] text-text3 truncate">{user.email}</div>
                </div>
              </div>
            )}
          </div>
        </nav>

        {/* Main content */}
        <main className="ml-[220px] flex-1 p-10 max-w-[900px]">{children}</main>
      </div>
    </>
  );
}
