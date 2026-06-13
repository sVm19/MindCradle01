import { Link, useLocation } from 'react-router';
import { useEffect, useState } from 'react';
import { useAuth, getInitials } from '@/lib/auth';
import { mood as moodApi, ai as aiApi } from '@/lib/api';
import { LayoutDashboard, Sun, Smile, BookOpen, Brain, Moon, Settings, Bell, Flame } from 'lucide-react';
import Logo from './Logo';

function formatDate(d: Date): string {
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
}

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

  // Proactive check-ins (Notification Center)
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [replyText, setReplyText] = useState<{ [key: string]: string }>({});
  const [sendingReply, setSendingReply] = useState<{ [key: string]: boolean }>({});

  const handleSendReply = (checkinId: string) => {
    const text = replyText[checkinId];
    if (!text || !text.trim()) return;

    setSendingReply((prev) => ({ ...prev, [checkinId]: true }));
    aiApi.respondToProactiveCheckin(checkinId, text)
      .then((updatedCheckin) => {
        setNotifications((prev) =>
          prev.map((n) => (n.id === checkinId ? updatedCheckin : n))
        );
        setReplyText((prev) => ({ ...prev, [checkinId]: '' }));
      })
      .catch((err) => {
        console.error('Failed to respond to proactive check-in:', err);
      })
      .finally(() => {
        setSendingReply((prev) => ({ ...prev, [checkinId]: false }));
      });
  };

  useEffect(() => {
    if (user) {
      aiApi.scheduleCheckin().catch(() => {}).finally(() => {
        aiApi.listProactiveCheckins().then((list) => {
          setNotifications(list);
        }).catch(() => {});
      });
    }
  }, [user]);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <LayoutDashboard size={15} /> },
    { path: '/morning', label: 'Morning', icon: <Sun size={15} /> },
    { path: '/mood', label: 'Mood', icon: <Smile size={15} /> },
    { path: '/journal', label: 'Journal', icon: <BookOpen size={15} /> },
    { path: '/aria', label: 'ARIA', icon: <Brain size={15} /> },
    { path: '/wind-down', label: 'Wind Down', icon: <Moon size={15} /> },
  ];

  const initials = user ? getInitials(user.name || user.email) : '?';
  const greeting = new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening';

  return (
    <>
      {/* Ambient orbs */}
      <div className="fixed w-[500px] h-[500px] rounded-full blur-[80px] bg-accent/8 -top-[150px] -right-[100px] pointer-events-none z-0" />
      <div className="fixed w-[400px] h-[400px] rounded-full blur-[80px] bg-teal/6 bottom-[100px] -left-[100px] pointer-events-none z-0" />
      <div className="fixed w-[300px] h-[300px] rounded-full blur-[80px] bg-rose/5 top-1/2 left-[40%] pointer-events-none z-0" />

      <div className="flex flex-col min-h-screen relative z-[1]">
        {/* Main Top Header */}
        <header className="w-full bg-transparent relative z-20">
          <div className="flex items-center justify-between gap-4 px-6 md:px-10 py-4 max-w-[900px] w-full mx-auto">
            {/* Left: Logo */}
            <div className="flex items-center flex-shrink-0">
              <Link to="/" className="block">
                <Logo className="h-10 w-auto text-text" />
              </Link>
            </div>

            {/* Center: Date and Greeting */}
            <div className="flex-1 text-center m-0 min-w-0">
              <div className="text-[10px] text-text3 tracking-[0.1em] uppercase mb-0.5 truncate">
                {formatDate(new Date())}
              </div>
              <div className="font-[family-name:var(--font-serif)] text-xs sm:text-base md:text-lg font-light text-text italic leading-tight truncate">
                Good {greeting}, <span className="not-italic text-accent">{user?.name?.split(' ')[0] || 'there'}</span> ✦
              </div>
            </div>

            {/* Right: Notification Center & Profile Link */}
            <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0">
              {/* Notification Center */}
              <div className="relative">
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className="w-11 h-11 rounded-lg bg-bg2/50 border border-border flex items-center justify-center hover:border-border2 hover:bg-white/5 text-text2 hover:text-text transition-all relative cursor-pointer"
                  aria-label="Notifications"
                >
                  <Bell size={18} />
                  {notifications.filter((n) => !n.actual_response).length > 0 && (
                    <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-accent rounded-full border border-bg2 animate-pulse" />
                  )}
                </button>

                {showNotifications && (
                  <div className="absolute right-0 mt-2.5 w-[290px] sm:w-[360px] bg-bg2 border border-border rounded-[20px] shadow-[0_12px_40px_rgba(0,0,0,0.5)] backdrop-blur-[20px] p-5 z-50 text-left animate-fadeIn">
                    <div className="flex items-center justify-between pb-3 border-b border-border mb-3">
                      <div className="font-[family-name:var(--font-serif)] text-sm font-medium text-text">
                        ✦ Aria's Reached Out
                      </div>
                      <div className="text-[10px] text-text3 uppercase tracking-wider">
                        {notifications.filter((n) => !n.actual_response).length} pending
                      </div>
                    </div>

                    <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1">
                      {notifications.length === 0 ? (
                        <div className="text-center py-6 text-xs text-text3 italic">
                          No recent notifications.
                        </div>
                      ) : (
                        notifications.map((n) => {
                          const hasResponded = !!n.actual_response;
                          const dateLabel = new Date(n.scheduled_time).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          });

                          return (
                            <div
                              key={n.id}
                              className="bg-bg3/50 border border-border/50 rounded-xl p-3.5 space-y-2.5 hover:border-border transition-all"
                            >
                              <div className="text-[12.5px] text-text font-light leading-relaxed">
                                "{n.suggested_message}"
                              </div>
                              
                              <div className="flex items-center justify-between text-[10px] text-text3">
                                <span>{dateLabel}</span>
                                {hasResponded && (
                                  <span className="text-green flex items-center gap-1 font-medium">
                                    ✓ Responded
                                  </span>
                                )}
                              </div>

                              {!hasResponded ? (
                                <div className="space-y-2 pt-1">
                                  <textarea
                                    className="w-full bg-bg4 border border-border rounded-lg p-2 text-xs text-text placeholder-text3 focus:outline-none focus:border-accent resize-none h-14"
                                    placeholder="Write your reply..."
                                    value={replyText[n.id] || ''}
                                    onChange={(e) =>
                                      setReplyText({ ...replyText, [n.id]: e.target.value })
                                    }
                                  />
                                  <div className="flex justify-between items-center">
                                    <Link
                                      to={`/aria?checkin=${n.id}`}
                                      onClick={() => setShowNotifications(false)}
                                      className="text-[11px] text-accent hover:underline"
                                    >
                                      Chat in ARIA →
                                    </Link>
                                    <button
                                      disabled={sendingReply[n.id] || !replyText[n.id]?.trim()}
                                      onClick={() => handleSendReply(n.id)}
                                      className="bg-accent text-white px-3 py-1 rounded-md text-[11px] font-medium hover:bg-accent/80 transition-all disabled:opacity-50"
                                    >
                                      {sendingReply[n.id] ? 'Sending…' : 'Send'}
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <div className="bg-bg4/35 border border-border/30 rounded-lg p-2.5 text-xs text-text3 italic">
                                  <div className="text-[9px] uppercase tracking-wider text-text3/60 mb-1">
                                    Your response
                                  </div>
                                  "{n.actual_response}"
                                </div>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Profile Icon Link */}
              <Link
                to="/settings"
                className="w-11 h-11 rounded-lg bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-[13px] font-medium text-white cursor-pointer hover:opacity-90 transition-opacity flex-shrink-0"
                title="Settings / Profile"
              >
                {initials}
              </Link>
            </div>
          </div>
        </header>

        {/* Top Horizontal Navigation Bar */}
        <nav className="w-full bg-transparent mt-4">
          <div className="flex items-center gap-1.5 sm:gap-2 px-6 md:px-10 py-2 overflow-x-auto scrollbar-none max-w-[900px] w-full mx-auto">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] transition-all whitespace-nowrap ${
                    isActive
                      ? 'bg-accent-glow text-accent border border-accent/20'
                      : 'text-text2 hover:bg-white/5 hover:text-text'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              );
            })}

            <div className="flex items-center gap-3 ml-auto flex-shrink-0">
              {/* Streak Tracker Pill */}
              {streak > 0 && (
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-dim border border-amber/20 rounded-full text-xs text-amber font-medium">
                  <Flame size={14} className="text-amber animate-pulse" />
                  <span>{streak} day streak</span>
                </div>
              )}

              {/* Settings button */}
              <Link
                to="/settings"
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] transition-all whitespace-nowrap ${
                  location.pathname === '/settings'
                    ? 'bg-accent-glow text-accent border border-accent/20'
                    : 'text-text2 hover:bg-white/5 hover:text-text'
                }`}
              >
                <Settings size={15} />
                <span>Settings</span>
              </Link>
            </div>
          </div>
        </nav>

        {/* Main Content Area (Full width) */}
        <main className="flex-1 p-6 md:p-10 max-w-[900px] w-full mx-auto">
          {children}
        </main>
      </div>
    </>
  );
}
