/**
 * MindCradle API Client
 * Central fetch wrapper with auto-auth headers, typed methods,
 * and automatic JWT refresh on 401.
 * The Vite dev proxy rewrites /api → http://localhost:8000.
 */

const BASE = '/api';

// ─── Token helpers ────────────────────────────────────────────────────────────

function getToken(): string | null {
  return localStorage.getItem('mc_token');
}

function getRefreshToken(): string | null {
  return localStorage.getItem('mc_refresh_token');
}

function setTokens(token: string, refreshToken: string) {
  localStorage.setItem('mc_token', token);
  localStorage.setItem('mc_refresh_token', refreshToken);
}

function clearTokens() {
  localStorage.removeItem('mc_token');
  localStorage.removeItem('mc_refresh_token');
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
    const rt = getRefreshToken();
    if (!rt) return false;

    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      });

      if (!res.ok) return false;

      const data = await res.json();
      setTokens(data.token, data.refresh_token);

      // Also update the stored user object with the new token
      const stored = localStorage.getItem('mc_user');
      if (stored) {
        try {
          const user = JSON.parse(stored);
          user.token = data.token;
          localStorage.setItem('mc_user', JSON.stringify(user));
        } catch { /* ignore */ }
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

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
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

export interface AIChatResponse {
  reply: string;
  conversation_id: string;
  crisis_detected?: boolean;
  crisis_severity?: number;
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
};

// ─── AI ───────────────────────────────────────────────────────────────────────

export const ai = {
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
  created: string;
}

export const profile = {
  get: () => request<ProfileResponse>('GET', '/profile'),
  update: (data: { emergency_contact?: string }) => request<ProfileResponse>('PATCH', '/profile', data),
  patchMilestones: (unlockedBadges: string[]) => request<any>('PATCH', '/profile/milestones', { unlockedBadges }),
};
