import { Link, useLocation } from 'react-router';
import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth, getInitials, getAvatarGradient, UserSketchAvatar } from '@/lib/auth';
import { mood as moodApi, resources as resourcesApi, ai as aiApi, user as userApi } from '@/lib/api';
import { LayoutDashboard, Sun, Smile, BookOpen, Brain, Moon, Settings, Bell, AlertTriangle, X, User, Award, Sparkles, Search, Lock } from 'lucide-react';

import Logo from './Logo';
import AuthCardModal from './AuthCardModal';
import AgeVerificationModal from './AgeVerificationModal';
import PrivacyPolicyModal from './PrivacyPolicyModal';
import SemanticSearch from './SemanticSearch';
import { TelemetryProvider } from '@/context/TelemetryContext';
import SEO from './SEO';

function formatDate(d: Date): string {
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, authModalOpen, setAuthModalOpen, verifyModalOpen, setVerifyModalOpen } = useAuth();
  const [streak, setStreak] = useState(0);
  const [didCheckInToday, setDidCheckInToday] = useState(false);
  const [didCheckInYesterday, setDidCheckInYesterday] = useState(false);
  const [hasCriticalCrisis, setHasCriticalCrisis] = useState(false);
  const [showCrisisModal, setShowCrisisModal] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  const navRef = useRef<HTMLDivElement>(null);
  const scrollIntervalRef = useRef<number | null>(null);
  
  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (navRef.current) {
      if (e.deltaY !== 0) {
        e.preventDefault();
        navRef.current.scrollLeft += e.deltaY;
      }
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const container = navRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const width = rect.width;
    
    const zoneWidth = 60; // 60px zone on left/right edges

    if (scrollIntervalRef.current) {
      cancelAnimationFrame(scrollIntervalRef.current);
      scrollIntervalRef.current = null;
    }

    if (x < zoneWidth) {
      const intensity = (zoneWidth - x) / zoneWidth;
      const scrollStep = () => {
        container.scrollLeft -= intensity * 8;
        scrollIntervalRef.current = requestAnimationFrame(scrollStep);
      };
      scrollIntervalRef.current = requestAnimationFrame(scrollStep);
    } else if (x > width - zoneWidth) {
      const intensity = (x - (width - zoneWidth)) / zoneWidth;
      const scrollStep = () => {
        container.scrollLeft += intensity * 8;
        scrollIntervalRef.current = requestAnimationFrame(scrollStep);
      };
      scrollIntervalRef.current = requestAnimationFrame(scrollStep);
    }
  };

  const handleMouseLeave = () => {
    if (scrollIntervalRef.current) {
      cancelAnimationFrame(scrollIntervalRef.current);
      scrollIntervalRef.current = null;
    }
  };

  // Global ⌘K / Ctrl+K shortcut
  const handleGlobalKeyDown = useCallback((e: globalThis.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (user) setSearchOpen(open => !open);
    }
  }, [user]);

  useEffect(() => {
    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => document.removeEventListener('keydown', handleGlobalKeyDown);
  }, [handleGlobalKeyDown]);

  // Open auth modal if redirected with state
  useEffect(() => {
    if (location.state?.openAuth) {
      setAuthModalOpen(true);
      // Clear location state to prevent reopening on navigation
      window.history.replaceState({}, document.title);
    }
  }, [location, setAuthModalOpen]);

  // Fetch streak from user service
  useEffect(() => {
    if (!user) {
      setStreak(0);
      setDidCheckInToday(false);
      setDidCheckInYesterday(false);
      return;
    }
    userApi.getStreak().then((res) => {
      setStreak(res.streak);
      setDidCheckInToday(res.did_mood_checkin_today);
      setDidCheckInYesterday(res.did_mood_checkin_yesterday);
    }).catch(() => {/* silently ignore if API is unavailable */ });
  }, [user]);

  // Fetch crisis status
  useEffect(() => {
    if (user) {
      aiApi.getCrisisStatus()
        .then((res) => {
          setHasCriticalCrisis(res.has_critical_crisis);
        })
        .catch(() => { });
    } else {
      setHasCriticalCrisis(false);
    }
  }, [user, location.pathname]);

  const handleResolveCrisis = () => {
    aiApi.resolveCrisis()
      .then(() => {
        setHasCriticalCrisis(false);
        setShowCrisisModal(false);
      })
      .catch((err) => {
        if (import.meta.env.DEV) {
          console.error('Failed to resolve crisis flags:', err);
        }
      });
  };

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
        if (import.meta.env.DEV) {
          console.error('Failed to respond to proactive check-in:', err);
        }
      })
      .finally(() => {
        setSendingReply((prev) => ({ ...prev, [checkinId]: false }));
      });
  };

  useEffect(() => {
    if (user) {
      aiApi.scheduleCheckin().catch(() => { }).finally(() => {
        aiApi.listProactiveCheckins().then((list) => {
          setNotifications(list);
        }).catch(() => { });
      });
    } else {
      setNotifications([]);
    }
  }, [user]);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <LayoutDashboard size={15} /> },
    { path: '/morning', label: 'Morning Focus', icon: <Sun size={15} /> },
    { path: '/mood', label: 'Reflections', icon: <Smile size={15} /> },
    { path: '/journal', label: 'Journal', icon: <BookOpen size={15} /> },
    { path: '/aria', label: 'ARIA', icon: <Brain size={15} /> },
    { path: '/insights', label: 'AI Insights', icon: <Sparkles size={15} /> },
    { path: '/wind-down', label: 'Wind Down', icon: <Moon size={15} /> },
  ];

  const initials = user ? getInitials(user.name || user.email) : '?';
  const greeting = new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening';

  const publicPaths = ['/', '/about', '/pricing', '/privacy', '/terms', '/refund'];
  const isPublic = publicPaths.includes(location.pathname) || 
                   location.pathname.startsWith('/blog') || 
                   location.pathname.startsWith('/docs');

  return (
    <TelemetryProvider>
      <>
      {!isPublic && (
        <SEO 
          title="MindCradle"
          description="Your private wellness dashboard."
          robots="noindex, nofollow"
        />
      )}
      {/* Ambient orbs */}
      <div className="fixed w-[500px] h-[500px] rounded-full blur-[80px] bg-accent/8 -top-[150px] -right-[100px] pointer-events-none z-0" />
      <div className="fixed w-[400px] h-[400px] rounded-full blur-[80px] bg-teal/6 bottom-[100px] -left-[100px] pointer-events-none z-0" />
      <div className="fixed w-[300px] h-[300px] rounded-full blur-[80px] bg-rose/5 top-1/2 left-[40%] pointer-events-none z-0" />

      {hasCriticalCrisis && (
        <div
          onClick={() => setShowCrisisModal(true)}
          className="w-full bg-rose/20 backdrop-blur-md border-b border-rose/30 py-2.5 px-4 text-center text-rose text-xs font-semibold tracking-wider hover:bg-rose/30 transition-all cursor-pointer flex items-center justify-center gap-2 relative z-50 animate-slideDown"
        >
          <AlertTriangle size={14} className="animate-pulse text-rose" />
          <span>Distress support is available. Click here for resources.</span>
        </div>
      )}

      <div className="flex flex-col min-h-screen relative z-[1]">
        <header className="w-full bg-transparent relative z-20">
          <div className="flex flex-wrap md:flex-nowrap items-center justify-between gap-x-4 gap-y-2 px-6 md:px-10 py-4 max-w-[900px] w-full mx-auto">
            {/* Left: Logo */}
            <div className="flex items-center flex-shrink-0 order-1">
              <Link to="/" className="block" aria-label="MindCradle Home">
                <Logo className="h-10 w-auto text-text" />
              </Link>
            </div>

            {/* Center: Date and Greeting */}
            <div className="order-3 md:order-2 w-full md:w-auto md:flex-1 text-center m-0 min-w-0 mt-2 md:mt-0">
              <div className="text-[10px] text-text3 tracking-[0.1em] uppercase mb-0.5">
                {formatDate(new Date())}
              </div>
              <div className="font-[family-name:var(--font-serif)] text-xs sm:text-base md:text-lg font-light text-text italic leading-tight whitespace-normal md:truncate">
                {user ? (
                  didCheckInToday ? (
                    <>Welcome back, <span className="not-italic text-accent">{user.name?.split(' ')[0]}</span>. Today's check-in is complete.</>
                  ) : didCheckInYesterday ? (
                    <>Welcome back, <span className="not-italic text-accent">{user.name?.split(' ')[0]}</span>. Let's check in for today.</>
                  ) : streak > 0 ? (
                    <>Good {greeting}, <span className="not-italic text-accent">{user.name?.split(' ')[0]}</span>. Let's rebuild your streak.</>
                  ) : (
                    <>Good {greeting}, <span className="not-italic text-accent">{user.name?.split(' ')[0]}</span>. Let's pause to check in.</>
                  )
                ) : (
                  <>Good {greeting}, <span className="not-italic text-accent">guest</span></>
                )}
              </div>
              {streak > 0 && (
                <div className="text-xs text-amber font-medium mt-1.5 animate-fadeIn">
                  {streak === 1 ? (
                    <>1 Day Streak | Off to a great start! ✦</>
                  ) : streak >= 2 && streak < 5 ? (
                    <>{streak} Day Streak | You're building momentum! ✦</>
                  ) : (
                    <>{streak} Day Streak | Incredible rhythm, keep it up! ✦</>
                  )}
                </div>
              )}
            </div>

            {/* Right: Search + Notification Center & Profile Link */}
            <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0 order-2 md:order-3">
              {/* Global Search button (⌘K) */}
              {user && (
                <button
                  onClick={() => setSearchOpen(true)}
                  title="Search your history (⌘K)"
                  className="w-11 h-11 rounded-lg bg-bg2/50 border border-border flex items-center justify-center hover:border-accent/50 hover:bg-accent/5 text-text2 hover:text-accent transition-all cursor-pointer group relative"
                  aria-label="Search history"
                >
                  <Search size={17} />
                  <span className="absolute -bottom-7 left-1/2 -translate-x-1/2 text-[9px] text-text3 bg-bg2 border border-border px-1.5 py-0.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    ⌘K
                  </span>
                </button>
              )}
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
                        {user ? `${notifications.filter((n) => !n.actual_response).length} pending` : 'guest'}
                      </div>
                    </div>

                    <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1">
                      {!user ? (
                        <div className="text-center py-6 space-y-3">
                          <div className="text-xs text-text3 italic">Sign in to view notifications.</div>
                          <button
                            type="button"
                            onClick={() => {
                              setShowNotifications(false);
                              setAuthModalOpen(true);
                            }}
                            className="px-4 py-1.5 bg-accent hover:bg-accent/80 text-white text-[11px] font-medium rounded-md transition-all cursor-pointer mx-auto block"
                          >
                            Sign In
                          </button>
                        </div>
                      ) : notifications.length === 0 ? (
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
                                      to={localStorage.getItem('age_verified') === 'false' ? '#' : `/aria?checkin=${n.id}`}
                                      onClick={(e) => {
                                        setShowNotifications(false);
                                        if (localStorage.getItem('age_verified') === 'false') {
                                          e.preventDefault();
                                          alert("This feature is for users 18+. Please contact a crisis counselor instead.");
                                        }
                                      }}
                                      className={`text-[11px] hover:underline ${localStorage.getItem('age_verified') === 'false'
                                        ? 'text-text3 cursor-not-allowed opacity-50'
                                        : 'text-accent'
                                        }`}
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

              {/* Profile Icon Link / Button */}
              {user ? (
                <Link
                  to="/settings"
                  className="w-11 h-11 rounded-full bg-[#eef2f6] border border-[#b0b8c0] flex items-center justify-center flex-shrink-0 hover:scale-105 transition-all shadow-[0_2px_8px_rgba(0,0,0,0.1)]"
                  title="Settings / Profile"
                >
                  <span
                    className="font-extrabold font-sans text-[15px] tracking-wide select-none animate-fadeIn"
                    style={{
                      color: '#612318ff'
                    }}
                  >
                    {initials}
                  </span>
                </Link>
              ) : (
                <button
                  type="button"
                  onClick={() => setAuthModalOpen(true)}
                  className="w-11 h-11 rounded-full bg-bg2/50 border border-border flex items-center justify-center text-text2 hover:text-text hover:border-border2 hover:bg-white/5 cursor-pointer transition-all flex-shrink-0 backdrop-blur-md"
                  title="Sign In / Create Account"
                >
                  <UserSketchAvatar className="w-5 h-5 text-text2" />
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Top Horizontal Navigation Bar */}
        <nav className="w-full bg-transparent mt-4 px-6 md:px-10">
          <div 
            ref={navRef}
            onWheel={handleWheel}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="flex items-center gap-1.5 sm:gap-2 px-5 py-2.5 overflow-x-auto scrollbar-none max-w-[820px] w-full mx-auto bg-bg2/40 backdrop-blur-md border border-border/60 rounded-full shadow-[0_8px_32px_rgba(0,0,0,0.2)]"
          >
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              const isBlocked = item.path === '/aria' && localStorage.getItem('age_verified') === 'false';
              const isLockedForGuest = (item.path === '/aria' || item.path === '/insights') && !user;
              
              return (
                <Link
                  key={item.path}
                  to={isBlocked ? '#' : isLockedForGuest ? '#' : item.path}
                  onClick={(e) => {
                    if (isBlocked) {
                      e.preventDefault();
                      alert("This feature is for users 18+. Please contact a crisis counselor instead.");
                    } else if (isLockedForGuest) {
                      e.preventDefault();
                      setAuthModalOpen(true);
                    }
                  }}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] transition-all whitespace-nowrap ${isBlocked
                    ? 'opacity-40 cursor-not-allowed text-text3 hover:bg-transparent'
                    : isActive
                      ? 'bg-accent-glow text-accent border border-accent/20'
                      : 'text-text2 hover:bg-white/5 hover:text-text'
                    }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                  {isLockedForGuest && <Lock size={11} className="text-text3 shrink-0 ml-0.5" />}
                </Link>
              );
            })}

            <div className="flex items-center gap-3 ml-auto flex-shrink-0">

              {/* Pricing button */}
              <Link
                to="/pricing"
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] transition-all whitespace-nowrap ${location.pathname === '/pricing'
                  ? 'bg-accent-glow text-accent border border-accent/20'
                  : 'text-text2 hover:bg-white/5 hover:text-text'
                  }`}
              >
                <Award size={15} />
                <span>Pricing</span>
              </Link>

              {/* Settings button */}
              <Link
                to={user ? "/settings" : "#"}
                onClick={(e) => {
                  if (!user) {
                    e.preventDefault();
                    setAuthModalOpen(true);
                  }
                }}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] transition-all whitespace-nowrap ${location.pathname === '/settings'
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

        {/* Global Footer */}
        <footer className="w-full border-t border-border/40 mt-auto py-8 relative z-20">
          <div className="max-w-[900px] mx-auto px-6 md:px-10 flex flex-col items-center gap-6 text-xs text-text3">
            {/* Nick Launches Verification Badge */}
            <div className="flex justify-center transition-all duration-300 hover:scale-[1.02]">
              <a 
                href="https://nicklaunches.com/products/mindcradle/?utm_source=mindcradle.online&utm_medium=badge&utm_campaign=featured" 
                target="_blank" 
                rel="noopener"
              >
                <img 
                  src="https://nicklaunches.com/badges/featured-dark.png" 
                  alt="MindCradle on Nick Launches" 
                  width="244" 
                  height="56" 
                  className="rounded-lg shadow-md"
                />
              </a>
            </div>

            <div className="w-full flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                &copy; {new Date().getFullYear()} MindCradle. All rights reserved.
              </div>
              <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 font-mono">
                <Link to="/blog" className="hover:text-text text-accent font-semibold transition-all">Blog</Link>
                <Link to="/docs/introduction" className="hover:text-text text-accent font-semibold transition-all">Docs</Link>
                <Link to="/pricing" className="hover:text-text transition-all">Pricing</Link>
                <Link to="/privacy" className="hover:text-text transition-all">Privacy Policy</Link>
                <Link to="/refund" className="hover:text-text transition-all">Refund Policy</Link>
                <Link to="/terms" className="hover:text-text transition-all">Terms of Service</Link>
                <a href="mailto:support@mindcradle.online" className="hover:text-text transition-all">Contact Us</a>
              </div>
            </div>
          </div>
        </footer>
      </div>

      {showCrisisModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-bg2 border border-border w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-slideIn">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-bg3">
              <h2 className="text-sm font-semibold text-rose uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle size={16} /> Crisis Support & Resources
              </h2>
              <button
                type="button"
                onClick={() => setShowCrisisModal(false)}
                className="text-text3 hover:text-text text-sm transition-all"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-6 space-y-4 text-left">
              <p className="text-sm text-text leading-relaxed font-light">
                We're concerned about your safety. You don't have to face this alone. Please reach out to one of the following 24/7 resources:
              </p>

              <div className="space-y-3">
                <div className="bg-bg3 border border-border rounded-xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <div className="text-sm text-text font-medium">National Suicide Prevention Lifeline</div>
                    <div className="text-xs text-text3 mt-0.5">Call 988 or text HOME to 741741</div>
                  </div>
                  <a
                    href="tel:988"
                    className="px-4 py-2 bg-rose/10 hover:bg-rose/25 border border-rose/30 text-rose rounded-lg text-xs font-semibold transition-all whitespace-nowrap"
                  >
                    Call 988
                  </a>
                </div>

                <div className="bg-bg3 border border-border rounded-xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <div className="text-sm text-text font-medium">Crisis Text Line</div>
                    <div className="text-xs text-text3 mt-0.5">Text HOME to 741741</div>
                  </div>
                  <a
                    href="sms:741741?&body=HOME"
                    className="px-4 py-2 bg-rose/10 hover:bg-rose/25 border border-rose/30 text-rose rounded-lg text-xs font-semibold transition-all whitespace-nowrap"
                  >
                    Text HOME
                  </a>
                </div>

                <div className="bg-bg3 border border-border rounded-xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <div className="text-sm text-text font-medium">International Resources</div>
                    <div className="text-xs text-text3 mt-0.5">Global support centers outside the US</div>
                  </div>
                  <a
                    href="https://www.iasp.info/resources/Crisis_Centres"
                    target="_blank"
                    rel="noreferrer"
                    className="px-4 py-2 bg-accent/10 hover:bg-accent/25 border border-accent/30 text-accent2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap"
                  >
                    Find Center
                  </a>
                </div>
              </div>

              <div className="pt-2 text-[10px] text-text3 leading-relaxed border-t border-border">
                If you are in immediate physical danger, please call 911 or go to the nearest emergency room.
              </div>

              <div className="flex gap-3 pt-3">
                <button
                  type="button"
                  onClick={handleResolveCrisis}
                  className="flex-1 px-4 py-2.5 bg-teal text-white rounded-lg text-xs font-semibold hover:bg-teal/80 transition-all cursor-pointer"
                >
                  I am safe now / Clear this banner
                </button>
                <button
                  type="button"
                  onClick={() => setShowCrisisModal(false)}
                  className="px-4 py-2.5 bg-bg3 border border-border text-text2 hover:text-text rounded-lg text-xs font-semibold transition-all cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Auth Modals */}
      {authModalOpen && <AuthCardModal />}
      {verifyModalOpen && (
        <AgeVerificationModal
          isOpen={verifyModalOpen}
          onVerified={() => setVerifyModalOpen(false)}
          onDeclined={() => setVerifyModalOpen(false)}
        />
      )}
      <PrivacyPolicyModal />

      {/* Semantic Search overlay (⌘K / Ctrl+K) */}
      <SemanticSearch
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
      />
      </>

    </TelemetryProvider>
  );
}
