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
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string, passwordConfirm: string) => Promise<void>;
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
    authApi.logout().catch(() => {});
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

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    persist(toUser(res));
  }, [persist]);

  const signup = useCallback(
    async (name: string, email: string, password: string, passwordConfirm: string) => {
      const res = await authApi.signup(name, email, password, passwordConfirm);
      persist(toUser(res));
    },
    [persist],
  );


  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        login,
        signup,
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

export const isAgeVerified = () => localStorage.getItem('age_verified') === 'true';

