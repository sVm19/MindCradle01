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

  // Always attach authorization header if we have a token, even if requiresAuth is false
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
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

export interface TimelineEvent {
  id: string;
  user_id: string;
  event_type: 'morning' | 'mood' | 'journal' | 'discovery' | 'milestone' | 'wind_down' | 'letter';
  source_id?: string;
  event_date: string;
  event_ts: string;
  title?: string;
  summary?: string;
  emotion?: string;
  mood_level?: number;
  metadata: Record<string, any>;
  created_at: string;
}

export interface TimelinePage {
  events: TimelineEvent[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
  date_span?: { earliest: string; latest: string };
  types_present: string[];
}

export interface SearchResultItem {
  id: string;
  user_id: string;
  event_type: string;
  source_id?: string;
  event_date: string;
  event_ts: string;
  title?: string;
  summary?: string;
  emotion?: string;
  mood_level?: number;
  metadata: Record<string, any>;
  rank_score: number;
  similarity?: number;
}

export interface SearchPage {
  results: SearchResultItem[];
  total: number;
  query: string;
  search_mode: 'semantic' | 'keyword' | 'hybrid';
  has_embeddings: boolean;
}

export interface KnowledgeNode {
  id: string;
  label: string;
  node_type: string;
  confidence: number;
  importance: number;
  valence: number;
  mention_count: number;
  first_seen_at: string;
  last_seen_at: string;
  source_reason?: string;
  is_confirmed: boolean;
  is_archived: boolean;
  metadata: Record<string, any>;
}

export interface KnowledgeEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  weight: number;
  evidence_count: number;
  last_reinforced_at: string;
}

export interface KnowledgeGraphResponse {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export interface GrowthMetricItem {
  metric_type: string;
  period: string;
  value: number;
  previous_value?: number;
  delta?: number;
  computed_at: string;
}

export interface GrowthMetricsResponse {
  metrics: GrowthMetricItem[];
}

export interface KnowledgeChapter {
  id: string;
  user_id: string;
  title: string;
  chapter_number: number;
  start_date: string;
  end_date?: string;
  is_current: boolean;
  theme_summary?: string;
  dominant_emotion?: string;
  mood_average?: number;
  growth_score?: number;
  key_events: any[];
  dominant_themes: string[];
  goals_started: string[];
  goals_achieved: string[];
  node_ids: string[];
  detected_by: string;
  confidence: number;
}

export interface KnowledgeChaptersListResponse {
  chapters: KnowledgeChapter[];
}

export interface KnowledgeComparisonItem {
  metric_type: string;
  current_value: number;
  previous_value: number;
  delta: number;
}

export interface KnowledgeComparisonResponse {
  current_chapter_title: string;
  previous_chapter_title: string;
  improvements: string[];
  challenge: string;
  comparison_metrics: KnowledgeComparisonItem[];
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
  linguistic_shift?: string;
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
  loginWithGoogle: (token: string) =>
    request<AuthResponse>('POST', '/auth/google', { token }, false),

  loginWithGoogleCode: (code: string) =>
    request<AuthResponse>('POST', '/auth/google', { code }, false),

  requestMagicLink: (email: string) =>
    request<{ message: string; session_id?: string }>('POST', '/auth/magic-link', { email }, false),

  loginWithMagicToken: (token: string) =>
    request<AuthResponse>('POST', '/auth/magic-login', { token }, false),

  verifyMagicLink: (token: string, deviceInfo: string) =>
    request<AuthResponse>('POST', '/auth/verify-magic-link', { token, device_info: deviceInfo }, false),

  checkSessionStatus: (sessionId: string) =>
    request<{ verified: boolean; token?: string; user_id?: string; name?: string; email?: string }>('GET', `/auth/check-session/${sessionId}`, undefined, false),

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

  withdrawConsent: (password?: string) =>
    request<{ success: boolean; message: string }>('DELETE', '/auth/withdraw-consent', {
      password,
    }),
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

  getMorningPrompt: () =>
    request<{ prompt: string }>('GET', '/rituals/morning/prompt'),

  getWindDownPrompt: () =>
    request<{ prompt: string }>('GET', '/rituals/winddown/prompt'),
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

  // ─── Timeline ───────────────────────────────────────────────────────────────
  getTimeline: (params?: {
    page?: number;
    page_size?: number;
    types?: string;       // comma-separated: "mood,journal,discovery"
    start_date?: string;  // YYYY-MM-DD
    end_date?: string;    // YYYY-MM-DD
    q?: string;           // keyword search
  }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    if (params?.types) qs.set('types', params.types);
    if (params?.start_date) qs.set('start_date', params.start_date);
    if (params?.end_date) qs.set('end_date', params.end_date);
    if (params?.q) qs.set('q', params.q);
    const queryStr = qs.toString() ? `?${qs.toString()}` : '';
    return request<TimelinePage>('GET', `/ai/timeline${queryStr}`);
  },

  rebuildTimeline: () => request<{ success: boolean; events_cached: number }>('POST', '/ai/timeline/rebuild'),

  // ─── Predictive Intelligence ───────────────────────────────────────────────
  getPredictions: () => request<{
    active_predictions: {
      id: string;
      user_id: string;
      prediction_type: string;
      prediction_text: string;
      target_date: string;
      confidence_score: number;
      is_correct: boolean | null;
      metadata: Record<string, any>;
      created_at: string;
    }[];
    stats: {
      total_evaluated: number;
      correct_count: number;
      accuracy_rate: number;
    };
  }>('GET', '/ai/predictions'),

  rebuildPredictions: () => request<{ success: boolean; message: string }>('POST', '/ai/predictions/rebuild'),

  submitPredictionFeedback: (id: string, isCorrect: boolean) =>
    request<{ success: boolean }>('PATCH', `/ai/predictions/${id}/feedback`, { isCorrect }),

  // ─── Semantic Search ─────────────────────────────────────────────────────────
  semanticSearch: (params: {
    q: string;
    types?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }) => {
    const qs = new URLSearchParams();
    qs.set('q', params.q);
    if (params.types) qs.set('types', params.types);
    if (params.start_date) qs.set('start_date', params.start_date);
    if (params.end_date) qs.set('end_date', params.end_date);
    if (params.limit) qs.set('limit', String(params.limit));
    return request<SearchPage>('GET', `/ai/search?${qs.toString()}`);
  },

  getSearchSuggestions: () =>
    request<{ suggestions: string[] }>('GET', '/ai/search/suggestions', undefined, false),

  getBlogPosts: () =>
    request<any[]>('GET', '/blog', undefined, false),

  getBlogPostBySlug: (slug: string) =>
    request<any>('GET', `/blog/${slug}`, undefined, false),

  getDocs: () =>
    request<any[]>('GET', '/docs', undefined, false),

  getDocBySlug: (slug: string) =>
    request<any>('GET', `/docs/${slug}`, undefined, false),

  generateEmbeddings: () =>
    request<{ total: number; embedded: number; failed: number; skipped: number }>(
      'POST', '/ai/embeddings/generate'
    ),

  // ─── Knowledge Graph / CIE ──────────────────────────────────────────────────
  processKnowledge: (sourceType: string, sourceId: string, text: string) =>
    request<{ success: boolean; nodes_processed: number }>('POST', '/aria/knowledge/process', {
      source_type: sourceType,
      source_id: sourceId,
      text,
    }),

  getKnowledgeGraph: () =>
    request<KnowledgeGraphResponse>('GET', '/aria/knowledge/graph'),

  getKnowledgeContext: (topic?: string) => {
    const qs = topic ? `?topic=${encodeURIComponent(topic)}` : '';
    return request<{ context_packet: string }>('GET', `/aria/knowledge/context${qs}`);
  },

  getGrowthMetrics: () =>
    request<GrowthMetricsResponse>('GET', '/aria/knowledge/growth'),

  deleteKnowledgeNode: (nodeId: string) =>
    request<{ success: boolean; message: string }>('DELETE', `/aria/knowledge/nodes/${nodeId}`),

  getLifeChapters: () =>
    request<KnowledgeChaptersListResponse>('GET', '/aria/knowledge/chapters'),

  updateKnowledgeNode: (nodeId: string, updates: { label?: string; is_confirmed?: boolean; is_archived?: boolean; valence?: number }) =>
    request<KnowledgeNode>('PATCH', `/aria/knowledge/nodes/${nodeId}`, updates),

  getChapterComparison: () =>
    request<KnowledgeComparisonResponse>('GET', '/aria/knowledge/comparison'),
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
  deleteAccount: (password?: string) => request<{ message: string }>('DELETE', '/user/delete-account', { password }),
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


// ─── Product Growth & Experimentation ──────────────────────────────────────────

export interface ActiveAssignment {
  experiment_id: string;
  experiment_name: string;
  variant: string;
  variants: string[];
}

export interface ActiveAssignmentsList {
  assignments: ActiveAssignment[];
}

export interface ExperimentVariantStats {
  variant: string;
  sample_size: number;
  conversions: number;
  conversion_rate: number;
}

export interface ExperimentAnalytics {
  id: string;
  name: string;
  description?: string;
  status: 'draft' | 'running' | 'paused' | 'completed';
  variants: ExperimentVariantStats[];
  p_value: number;
  is_significant: boolean;
  improvement_delta: number;
  conclusion: string;
}

export interface FunnelStepAnalytics {
  step: number;
  name: string;
  count: number;
  percent: number;
}

export interface GrowthAnalyticsResponse {
  experiments: ExperimentAnalytics[];
  funnel: FunnelStepAnalytics[];
}

export const growth = {
  getActiveAssignments: () =>
    request<ActiveAssignmentsList>('GET', '/growth/experiments/active'),
    
  trackEvent: (eventName: string, properties: Record<string, any> = {}) =>
    request<{ success: boolean }>('POST', '/growth/events', {
      event_name: eventName,
      properties,
    }),
    
  getStats: () =>
    request<GrowthAnalyticsResponse>('GET', '/growth/experiments/stats'),
    
  createExperiment: (name: string, description: string, variants: string[] = ['control', 'treatment']) =>
    request<any>('POST', '/growth/experiments/create', {
      name,
      description,
      variants,
    }),
    
  updateExperimentStatus: (id: string, status: 'draft' | 'running' | 'paused' | 'completed') =>
    request<any>('POST', `/growth/experiments/${id}/status`, {
      status,
    }),
};




