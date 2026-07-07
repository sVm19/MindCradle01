/**
 * MindCradle API Client
 * Central fetch wrapper with auto-auth headers, typed methods,
 * and automatic JWT refresh on 401.
 *
 * Routing:
 *   Development — Vite proxy rewrites /api → http://localhost:8000
 *   Production  — Vercel rewrites /api → https://mindcradle01-959765770210.europe-west1.run.app
 *                 (configured in vercel.json) OR same-origin if collocated.
 *
 * All requests use relative /api paths so no VITE_API_URL is needed
 * in client-side code — the proxy/rewrite handles it transparently.
 */

import { getCsrfToken } from './csrf';

const BASE = '/api';

// ─── Token helpers ────────────────────────────────────────────────────────────

let _accessToken: string | null = null;

export function getAccessToken(): string | null {
  return _accessToken;
}

export function setAccessToken(token: string | null) {
  _accessToken = token;
}

function getToken(): string | null {
  return _accessToken;
}

function clearTokens() {
  _accessToken = null;
  localStorage.removeItem('mc_user');
}

// Global callback — set by AuthProvider to handle forced logout
let _onTokenExpired: (() => void) | null = null;

export function setTokenExpiredCallback(cb: () => void) {
  _onTokenExpired = cb;
}

// ─── Token refresh ────────────────────────────────────────────────────────────

let _refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  // Deduplicate concurrent refreshes
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });

      if (!res.ok) return false;

      const data = await res.json();
      setAccessToken(data.token);

      // Also update the stored user object with the new token
      const stored = localStorage.getItem('mc_user');
      if (stored) {
        try {
          const user = JSON.parse(stored);
          user.token = data.token;
          user.name = data.name;
          user.email = data.email;
          user.userId = data.user_id;
          localStorage.setItem('mc_user', JSON.stringify(user));
        } catch { /* ignore */ }
      } else {
        // Create user object if missing
        const user = {
          token: data.token,
          userId: data.user_id,
          name: data.name,
          email: data.email,
        };
        localStorage.setItem('mc_user', JSON.stringify(user));
      }
      return true;
    } catch {
      return false;
    }
  })();

  const result = await _refreshPromise;
  _refreshPromise = null;
  return result;
}

// ─── Core request function ────────────────────────────────────────────────────

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  requiresAuth = true,
  _isRetry = false,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (requiresAuth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method.toUpperCase())) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers['X-CSRF-Token'] = csrf;
    }
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'include',
  });

  // Handle 401 — attempt token refresh, then retry once
  if (res.status === 401 && requiresAuth && !_isRetry) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      return request<T>(method, path, body, requiresAuth, true);
    }
    // Refresh failed — force logout
    clearTokens();
    _onTokenExpired?.();
    throw new Error('Session expired. Please log in again.');
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const text = await res.text();
      try {
        const err = JSON.parse(text);
        detail = err.detail || err.message || err.error || detail;
      } catch {
        if (text) {
          detail = `${detail}: ${text}`;
        }
      }
    } catch {
      /* ignore */
    }

    // Catch JWT-expired messages in error body too
    if (detail.includes('JWT expired') || detail.includes('PGRST303')) {
      if (!_isRetry) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
          return request<T>(method, path, body, requiresAuth, true);
        }
      }
      clearTokens();
      _onTokenExpired?.();
      throw new Error('Session expired. Please log in again.');
    }

    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}


// ─── Types ────────────────────────────────────────────────────────────────────

export interface AuthResponse {
  token: string;
  refresh_token: string;
  user_id: string;
  name: string;
  email: string;
}

export interface MoodItem {
  id: string;
  level: number;
  emotions: string[];
  note: string;
  created: string;
}

export interface MoodHistoryResponse {
  items: MoodItem[];
  total: number;
}

export interface JournalItem {
  id: string;
  prompt: string;
  content: string;
  ai_reflection?: string;
  created: string;
}

export interface JournalListResponse {
  items: JournalItem[];
  total: number;
}

export interface CrisisResource {
  name: string;
  phone?: string;
  text?: string;
  website: string;
}

export interface AIChatResponse {
  reply: string;
  conversation_id: string;
  crisis_detected?: boolean;
  crisis_severity?: number;
  severity?: 'CRITICAL' | 'HIGH';
  message?: string;
  type?: string;
  reason?: string;
  resources?: CrisisResource[];
  encourage?: string;
  contact_emergency?: string;
}

export interface JournalReflectionResponse {
  reflection: string;
  themes: string[];
  emotional_tone: string;
}

export interface MoodAnalysisResponse {
  analysis: string;
  pattern: string;
  suggestion: string;
  mood_trend: string;
}


export interface ResourceItem {
  id: string;
  title: string;
  description: string;
  icon: string;
  color_class: string;
  category: string;
  order: number;
  url?: string;
}

export interface ResourcesResponse {
  items: ResourceItem[];
  total: number;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const auth = {
  login: (email: string, password: string) =>
    request<AuthResponse>('POST', '/auth/login', { email, password }, false),

  signup: (name: string, email: string, password: string, passwordConfirm: string) =>
    request<AuthResponse>(
      'POST',
      '/auth/signup',
      { name, email, password, passwordConfirm },
      false,
    ),

  refresh: () =>
    request<AuthResponse>('POST', '/auth/refresh', undefined, false),

  logout: () =>
    request<{ success: boolean }>('POST', '/auth/logout', undefined, false),



  checkAgeVerified: () =>
    request<{ age_verified: boolean; verified_at: string | null }>('GET', '/auth/check-age-verified'),

  verifyAge: (verified: boolean) =>
    request<{ success: boolean; verified: boolean }>('POST', '/auth/verify-age', {
      age_verified: verified,
    }),

  acceptPrivacy: (accepted: boolean, requiresAuth = false) =>
    request<{ success: boolean; accepted: boolean; warning?: string }>('POST', '/auth/privacy-accepted', {
      privacy_accepted: accepted,
    }, requiresAuth),

  checkPrivacy: () =>
    request<{ privacy_accepted: boolean; accepted_at: string | null }>('GET', '/auth/check-privacy'),

  getPrivacyPolicy: () =>
    request<{ text: string }>('GET', '/auth/privacy-policy', undefined, false),

  withdrawConsent: (password: string) =>
    request<{ success: boolean; message: string }>('DELETE', '/auth/withdraw-consent', {
      password,
    }),

  forgotPassword: (email: string) =>
    request<{ message: string }>('POST', '/auth/forgot-password', { email }, false),

  resetPassword: (token: string, newPassword: string) =>
    request<{ message: string }>('POST', '/auth/reset-password', { token, newPassword }, false),
};

// ─── Mood ─────────────────────────────────────────────────────────────────────

export const mood = {
  log: (level: number, emotions: string[], note: string) =>
    request<{ id: string; saved: boolean }>('POST', '/mood', { level, emotions, note }),

  history: (range: '7d' | '30d' | '90d' | 'all' = '7d') =>
    request<MoodHistoryResponse>('GET', `/mood?range=${range}`),
};

// ─── Journal ──────────────────────────────────────────────────────────────────

export const journal = {
  save: (prompt: string, content: string, aiReflection?: string) =>
    request<{ id: string; saved: boolean }>('POST', '/journal', {
      prompt,
      content,
      ai_reflection: aiReflection,
    }),

  list: () => request<JournalListResponse>('GET', '/journal'),
};

// ─── Rituals ──────────────────────────────────────────────────────────────────

export const rituals = {
  saveMorning: (data: {
    forecast: string;
    intention: string;
    activityType: string;
    completedAt: string;
  }) => request<{ id: string; saved: boolean }>('POST', '/rituals/morning', data),

  saveWindDown: (data: {
    releaseItem: string;
    gratitudes: string[];
    audioChoice: string;
    timer: string;
  }) => request<{ id: string; saved: boolean }>('POST', '/rituals/winddown', data),

  getStats: () =>
    request<{ completed: number; total: number }>('GET', '/rituals/stats'),
};

// ─── AI ───────────────────────────────────────────────────────────────────────

export const ai = {
  verifyAge: (verified: boolean) =>
    request<{ status: string; age_verified: boolean }>('POST', '/aria/verify-age', {
      age_verified: verified,
    }),

  chat: (
    message: string,
    conversationId?: string,
    responseType?: string,
    contextData?: Record<string, any>
  ) =>
    request<AIChatResponse>('POST', '/ai/chat', {
      message,
      conversation_id: conversationId ?? null,
      response_type: responseType ?? null,
      context_data: contextData ?? null,
    }),

  reflect: (journalContent: string, userId: string) =>
    request<JournalReflectionResponse>('POST', '/ai/journal-reflection', {
      journal_content: journalContent,
      user_id: userId,
    }),

  analyzeMood: (moodData: { level: number; emotions: string[]; date: string }[], userId: string) =>
    request<MoodAnalysisResponse>('POST', '/ai/mood-analysis', {
      mood_data: moodData,
      user_id: userId,
    }),

  rememberContext: (
    conversationId: string,
    userId: string,
    keyInsight: string,
    emotion: string,
    contextType: string
  ) =>
    request<{ id: string; saved: boolean }>('POST', '/ai/remember-context', {
      conversation_id: conversationId,
      user_id: userId,
      key_insight: keyInsight,
      emotion: emotion,
      context_type: contextType,
    }),

  getMemoryInsights: () =>
    request<any[]>('GET', '/ai/memory-insights'),

  updateMemoryInsight: (id: string, data: { situation?: string; emotion?: string; what_helped?: string; follow_up?: string }) =>
    request<{ saved: boolean }>('PUT', `/ai/memory-insights/${id}`, data),

  deleteMemoryInsight: (id: string) =>
    request<{ deleted: boolean }>('DELETE', `/ai/memory-insights/${id}`),

  extractThemes: (conversationId: string) =>
    request<any>('POST', '/ai/extract-themes', { conversation_id: conversationId }),

  getConversationThemes: () =>
    request<{ themes: any[]; frequencies: { theme: string; count: number }[] }>('GET', '/ai/conversation-themes'),

  trackHelp: (conversationId: string, adviceGiven: string, helpRating: number, followUpMood?: number) =>
    request<{ id: string; saved: boolean }>('POST', '/ai/track-help', {
      conversation_id: conversationId,
      advice_given: adviceGiven,
      help_rating: helpRating,
      follow_up_mood: followUpMood ?? null,
    }),

  learnPersonality: () =>
    request<any>('POST', '/ai/learn-personality'),

  getUserPersonality: () =>
    request<any>('GET', '/ai/user-personality'),

  selectResponseType: (message: string, conversationId?: string) =>
    request<{ response_type: string; reason: string }>('POST', '/ai/select-response-type', { message, conversation_id: conversationId }),

  listConversations: () =>
    request<any[]>('GET', '/ai/conversations'),

  getActiveConversation: () =>
    request<any>('GET', '/ai/conversations/active'),

  endConversation: (conversationId: string) =>
    request<any>('POST', `/ai/conversations/${conversationId}/end`),

  getCheckIn: () =>
    request<any>('GET', '/ai/check-in'),

  scheduleCheckin: () =>
    request<any>('POST', '/ai/schedule-checkin'),

  listProactiveCheckins: () =>
    request<any[]>('GET', '/ai/proactive-checkins'),

  respondToProactiveCheckin: (checkinId: string, actualResponse: string, effectiveness?: number) =>
    request<any>('POST', `/ai/proactive-checkins/${checkinId}/respond`, {
      actual_response: actualResponse,
      effectiveness,
    }),

  getRecoveryPatterns: () =>
    request<{ history: any[]; stats: any }>('GET', '/ai/recovery-patterns'),

  trackEngagement: (conversationId: string) =>
    request<any>('POST', '/ai/track-engagement', { conversation_id: conversationId }),

  getEngagementStats: () =>
    request<{
      avg_response_time: number;
      return_rate_24h: number;
      convo_type_engagement: any[];
      personalized_vs_generic: Record<string, any>;
      ab_tests: any[];
    }>('GET', '/ai/engagement-stats'),

  detectCrisis: (conversationId: string, message: string) =>
    request<{ severity_level: number; red_flags_detected: string[]; action_taken?: string }>('POST', '/ai/detect-crisis', {
      conversation_id: conversationId,
      message,
    }),

  getCrisisStatus: () =>
    request<{ has_critical_crisis: boolean }>('GET', '/aria/crisis-status'),

  resolveCrisis: () =>
    request<{ status: string; resolved_count: number }>('POST', '/aria/crisis-resolve'),

  trackInteraction: (data: {
    event_type: string;
    element_id?: string;
    element_name?: string;
    page_path: string;
    input_placeholder?: string;
    input_length?: number;
    metadata?: Record<string, any>;
  }) => request<{ success: boolean; id?: string }>('POST', '/ai/track-interaction', data),

  get30DayInsights: () => request<{
    success: boolean;
    data: {
      calmness_score: number;
      consistency_index: number;
      interaction_focus: string;
      insights: string[];
    };
    stats: {
      total_moods: number;
      avg_mood: number;
      total_journals: number;
      total_rituals: number;
      total_clicks: number;
      total_navigations: number;
      top_page: string;
    };
  }>('GET', '/ai/30day-insights'),

  getSolsticeLetter: () => request<{ letter: string }>('GET', '/ai/solstice-letter'),
  getDailyDiscovery: () => request<any>('GET', '/ai/daily-discovery'),
  getDailyDiscoveryHistory: () => request<any[]>('GET', '/ai/daily-discovery/history'),
  updateDiscoveryFeedback: (id: string, feedback: { is_dismissed?: boolean; is_shared?: boolean; is_viewed?: boolean }) =>
    request<any>('PATCH', `/ai/daily-discovery/${id}/feedback`, feedback),
};

// ─── Resources ────────────────────────────────────────────────────────────────

export const resources = {
  list: (category?: string) => {
    const qs = category ? `?category=${category}` : '';
    return request<ResourcesResponse>('GET', `/resources${qs}`, undefined, false);
  },
};

// ─── Profile ──────────────────────────────────────────────────────────────────

export interface ProfileResponse {
  id: string;
  user_id: string;
  unlocked_badges?: string[];
  badge_history?: any[];
  emergency_contact?: string;
  notify_on_crisis?: boolean;
  is_premium?: boolean;
  subscription_expires_at?: string | null;
  created: string;
}

export const profile = {
  get: () => request<ProfileResponse>('GET', '/profile'),
  update: (data: { emergency_contact?: string; notify_on_crisis?: boolean }) => request<ProfileResponse>('PATCH', '/profile', data),
  patchMilestones: (unlockedBadges: string[]) => request<any>('PATCH', '/profile/milestones', { unlockedBadges }),
};

export const user = {
  me: () => request<{ id: string; email: string }>('GET', '/user/me'),
  exportData: () => request<any>('GET', '/user/export-data'),
  deleteAccount: (password: string) => request<{ message: string }>('DELETE', '/user/delete-account', { password }),
};

// ─── Billing & Subscriptions ──────────────────────────────────────────────────

export const billing = {
  checkout: (cardNumber: string, cvc: string, expiry: string) =>
    request<{
      status: string;
      message: string;
      is_premium: boolean;
      subscription_expires_at: string;
    }>('POST', '/billing/checkout', {
      card_number: cardNumber,
      cvc,
      expiry,
    }),

  cancel: () =>
    request<{ status: string; message: string }>('POST', '/billing/cancel'),
};

export const payments = {
  createCreemCheckout: () =>
    request<{ checkout_url: string; error?: string }>('POST', '/payments/creem-checkout'),
  startTrial: () =>
    request<{ success: boolean; trial_ends_at: string; message: string; error?: string }>('POST', '/payments/start-trial'),
  trialStatus: () =>
    request<{ trial_active: boolean; days_remaining: number; trial_ends_at?: string; trial_used: boolean }>('GET', '/payments/trial-status'),
};



