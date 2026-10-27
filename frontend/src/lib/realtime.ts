import { useEffect, useRef } from 'react';
import { createClient } from '@supabase/supabase-js';
import type { RealtimeChannel } from '@supabase/supabase-js';

// Default to project Supabase instance
const SUPABASE_URL =
  import.meta.env.VITE_SUPABASE_URL || 'https://nnwuthynlxrbvuxmpjgu.supabase.co';
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5ud3V0aHlubHhyYnZ1eG1wamd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5Mjg0NjUsImV4cCI6MjA5NjUwNDQ2NX0.XEvui77UlfrzwCEfRA9oTWjUq4LOjbJm5epCOMerrzo';

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
 * Safely handles connection failures without throwing unhandled exceptions.
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

    let isMounted = true;

    try {
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
            if (isMounted && payload.new && typeof payload.new === 'object') {
              onProfileUpdate(payload.new as UserProfileChange);
            }
          }
        )
        .subscribe((status, err) => {
          if (status === 'SUBSCRIBED') {
            // Connected successfully to Supabase Realtime
          } else if (status === 'CHANNEL_ERROR') {
            // Gracefully handle Realtime WebSocket disconnection
            if (import.meta.env.DEV) {
              console.debug('Supabase Realtime offline or disabled on project:', err?.message || status);
            }
          }
        });

      channelRef.current = channel;
    } catch (e) {
      if (import.meta.env.DEV) {
        console.debug('Failed to initialize Supabase Realtime subscription:', e);
      }
    }

    return () => {
      isMounted = false;
      if (channelRef.current) {
        try {
          supabase.removeChannel(channelRef.current);
        } catch { /* ignore */ }
        channelRef.current = null;
      }
    };
  }, [userId, onProfileUpdate]);
}
