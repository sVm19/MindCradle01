import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';

// Use config values from Firebase console via Vite env
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: `${import.meta.env.VITE_FIREBASE_PROJECT_ID}.firebaseapp.com`,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: `${import.meta.env.VITE_FIREBASE_PROJECT_ID}.appspot.com`,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

// Initialize Firebase App and Messaging
let app;
let messaging: ReturnType<typeof getMessaging> | null = null;

try {
  if (
    import.meta.env.VITE_FIREBASE_API_KEY &&
    import.meta.env.VITE_FIREBASE_PROJECT_ID
  ) {
    app = initializeApp(firebaseConfig);
    messaging = getMessaging(app);
  } else {
    console.warn(
      'Firebase config env variables are missing. Firebase messaging won\'t initialize.'
    );
  }
} catch (error) {
  console.error('Failed to initialize Firebase Messaging:', error);
}

/**
 * Request notification permission, get FCM token, send it to the backend,
 * and save it to localStorage.
 */
export async function registerFCMToken(): Promise<string | null> {
  try {
    // 1. Request notification permission from user
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      console.warn('Notification permission not granted by user.');
      return null;
    }

    if (!messaging) {
      console.warn('Firebase Messaging not initialized.');
      return null;
    }

    // 2. Get FCM token from Firebase
    // Uses VITE_FIREBASE_VAPID_KEY if provided in the environment
    const vapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY;
    const token = await getToken(messaging, vapidKey ? { vapidKey } : undefined);

    if (!token) {
      console.warn('No FCM token obtained.');
      return null;
    }

    // 3. Save token to localStorage as 'fcm_token'
    localStorage.setItem('fcm_token', token);

    // Retrieve or generate a persistent device_id for this device
    let deviceId = localStorage.getItem('device_id');
    if (!deviceId) {
      deviceId =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : 'web_' +
          Math.random().toString(36).substring(2, 15) +
          Date.now().toString(36);
      localStorage.setItem('device_id', deviceId);
    }

    // 4. Send token to backend: POST /api/notifications/register-device
    const mcToken = localStorage.getItem('mc_token');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (mcToken) {
      headers['Authorization'] = `Bearer ${mcToken}`;
    }

    const response = await fetch('/api/notifications/register-device', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        push_token: token,
        platform: 'web',
        device_id: deviceId,
      }),
    });

    if (!response.ok) {
      console.error(
        'Failed to register FCM token with the backend:',
        response.statusText
      );
    } else {
      console.log('Successfully registered FCM token with backend.');
    }

    // 5. Return token
    return token;
  } catch (error) {
    console.error('Error during FCM token registration:', error);
    return null;
  }
}

/**
 * Listen for incoming push messages, log them, and trigger browser notifications.
 */
export function listenForMessages(): void {
  if (!messaging) {
    console.warn('Firebase Messaging not initialized.');
    return;
  }

  onMessage(messaging, (payload) => {
    console.log('FCM Message received in foreground:', payload);

    // Show browser notification when message arrives
    if (Notification.permission === 'granted') {
      const title = payload.notification?.title || 'New Notification';
      const options: NotificationOptions = {
        body: payload.notification?.body || '',
        icon: payload.notification?.image || '/favicon.ico',
      };
      new Notification(title, options);
    }
  });
}
