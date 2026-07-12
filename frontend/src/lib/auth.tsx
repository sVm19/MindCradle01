import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { auth as authApi, setTokenExpiredCallback, setAccessToken } from '@/lib/api';
import type { AuthResponse } from '@/lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface User {
  token: string;
  userId: string;
  name: string;
  email: string;
}

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  loginWithGoogle: (token: string) => Promise<void>;
  loginWithGoogleCode: (code: string) => Promise<void>;
  loginWithMagicToken: (token: string) => Promise<void>;
  logout: () => void;
  authModalOpen: boolean;
  setAuthModalOpen: (open: boolean) => void;
  verifyModalOpen: boolean;
  setVerifyModalOpen: (open: boolean) => void;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_USER_KEY = 'mc_user';

function toUser(res: AuthResponse): User {
  return {
    token: res.token,
    userId: res.user_id,
    name: res.name,
    email: res.email,
  };
}

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [verifyModalOpen, setVerifyModalOpen] = useState(false);

  // Restore session on mount using the HTTP-only refresh cookie
  useEffect(() => {
    async function restoreSession() {
      try {
        const res = await authApi.refresh();
        setAccessToken(res.token);
        const u = toUser(res);
        localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(u));
        setUser(u);
      } catch {
        // Clear session if restore fails
        setAccessToken(null);
        localStorage.removeItem(STORAGE_USER_KEY);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    restoreSession();
  }, []);

  const logout = useCallback(() => {
    setAccessToken(null);
    localStorage.removeItem(STORAGE_USER_KEY);
    setUser(null);
    authApi.logout().catch(() => { });
  }, []);

  // Register the global token-expired callback so the API layer
  // can force a logout when refresh fails
  useEffect(() => {
    setTokenExpiredCallback(() => {
      logout();
    });
  }, [logout]);

  const persist = useCallback((u: User) => {
    setAccessToken(u.token);
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(u));
    setUser(u);

    // Sync privacy acceptance to database now that we have a user token
    const localAccepted = localStorage.getItem('privacy_accepted') === 'true';
    if (localAccepted) {
      authApi.acceptPrivacy(true, true).catch((err) => {
        if (import.meta.env.DEV) {
          console.error('Failed to sync privacy acceptance to database:', err);
        }
      });
    }
  }, []);


  const loginWithGoogle = useCallback(async (token: string) => {
    const res = await authApi.loginWithGoogle(token);
    persist(toUser(res));
  }, [persist]);

  const loginWithGoogleCode = useCallback(async (code: string) => {
    const res = await authApi.loginWithGoogleCode(code);
    persist(toUser(res));
  }, [persist]);

  const loginWithMagicToken = useCallback(async (token: string) => {
    const res = await authApi.loginWithMagicToken(token);
    persist(toUser(res));
  }, [persist]);


  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        loginWithGoogle,
        loginWithGoogleCode,
        loginWithMagicToken,
        logout,
        authModalOpen,
        setAuthModalOpen,
        verifyModalOpen,
        setVerifyModalOpen,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

/** Returns initials for the avatar (up to 2 chars). */
export function getInitials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');
}

/** Returns a modern colorful gradient based on name/email string. */
export function getAvatarGradient(name: string): string {
  const sum = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const gradients = [
    'from-[#ff007f] via-[#7f00ff] to-[#00f0ff]', // Neon Pink-Purple-Cyan
    'from-[#ff5e62] to-[#ff9966]', // Salmon-Orange
    'from-[#11998e] to-[#38ef7d]', // Emerald-Mint
    'from-[#130cb7] to-[#52e5e7]', // Electric Blue
    'from-[#fc4a1a] to-[#f7b733]', // Fire Sunrise
    'from-[#ee0979] to-[#ff6a00]', // Pink Sunset
    'from-[#8a2387] via-[#e94057] to-[#f27121]', // Crimson-Orange
    'from-[#f857a6] to-[#ff5858]', // Hot Pink
    'from-[#654ea3] to-[#eaafc8]', // Orchid
  ];
  return gradients[sum % gradients.length];
}

export const isAgeVerified = () => localStorage.getItem('age_verified') === 'true';

/** A stylized modern sketch of a human face/silhouette for avatars. */
export function UserSketchAvatar({ className = "w-6 h-6 text-white" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="8.5" r="4.5" />
      <path d="M4.5 20c0-3.3 2.7-6 6-6h3c3.3 0 6 2.7 6 6" />
    </svg>
  );
}


