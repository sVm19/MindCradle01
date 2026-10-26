import { useEffect, useRef } from 'react';
import { createClient } from '@supabase/supabase-js';
import type { RealtimeChannel } from '@supabase/supabase-js';

// Default to project Supabase instance if environment variables are not yet populated
const SUPABASE_URL =
  import.meta.env.VITE_SUPABASE_URL || 'https://nnwuthynlxrbvuxmpjgu.supabase.co';
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5ud3V0aHlubHhyYnZ1eG1wamd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAxNTMwOTksImV4cCI6MjA1NTcyOTA5OX0.eKq3Y0H1-6rXvYJj7Q51-w4v7J8z4qZ-jK3m2x_8Y7M';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

export interface UserProfileChange {
  id?: string;
  user_id?: string;
  cognito_sub?: string;
  name?: string;
  email?: string;
  is_premium?: boolean;
  trial_active?: boolean;
  unlocked_badges?: string[];
  [key: string]: unknown;
}

/**
 * Hook to subscribe to real-time updates for a user's profile in Supabase.
 * Triggered automatically when backend JIT sync, payments, or background jobs modify user_profiles.
 */
export function useUserProfileRealtime(
  userId: string | undefined,
  onProfileUpdate: (updatedProfile: UserProfileChange) => void
) {
  const channelRef = useRef<RealtimeChannel | null>(null);

  useEffect(() => {
    if (!userId) {
      return;
    }

    // Subscribe to changes on user_profiles for this specific user
    const channel = supabase
      .channel(`profile-sync-${userId}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'user_profiles',
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          if (payload.new && typeof payload.new === 'object') {
            onProfileUpdate(payload.new as UserProfileChange);
          }
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          // Connected to Supabase Realtime WebSocket
        }
      });

    channelRef.current = channel;

    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [userId, onProfileUpdate]);
}
