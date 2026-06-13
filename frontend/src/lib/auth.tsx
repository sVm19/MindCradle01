import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { auth as authApi, setTokenExpiredCallback } from '@/lib/api';
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
}

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = 'mc_token';
const STORAGE_REFRESH_KEY = 'mc_refresh_token';
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

  // Rehydrate from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_USER_KEY);
      const token = localStorage.getItem(STORAGE_KEY);
      if (stored && token) {
        const parsed = JSON.parse(stored) as User;
        setUser(parsed);
      }
    } catch {
      // Corrupted data — clear it
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(STORAGE_REFRESH_KEY);
      localStorage.removeItem(STORAGE_USER_KEY);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_REFRESH_KEY);
    localStorage.removeItem(STORAGE_USER_KEY);
    setUser(null);
  }, []);

  // Register the global token-expired callback so the API layer
  // can force a logout when refresh fails
  useEffect(() => {
    setTokenExpiredCallback(() => {
      logout();
    });
  }, [logout]);

  const persist = useCallback((u: User, refreshToken: string) => {
    localStorage.setItem(STORAGE_KEY, u.token);
    localStorage.setItem(STORAGE_REFRESH_KEY, refreshToken);
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(u));
    setUser(u);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    persist(toUser(res), res.refresh_token);
  }, [persist]);

  const signup = useCallback(
    async (name: string, email: string, password: string, passwordConfirm: string) => {
      const res = await authApi.signup(name, email, password, passwordConfirm);
      persist(toUser(res), res.refresh_token);
    },
    [persist],
  );

  return (
    <AuthContext.Provider value={{ user, isLoading, login, signup, logout }}>
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
