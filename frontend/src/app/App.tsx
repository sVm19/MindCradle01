import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { AuthProvider, useAuth } from '@/lib/auth';
import { ARIAProvider } from '@/context/ARIAContext';
import { registerFCMToken, listenForMessages } from '@/lib/firebase';
import { useCSRF } from '@/lib/csrf';
import Layout from './components/Layout';
import { PWAInstallPrompt } from './components/PWAInstallPrompt';

// Lazy-loaded page components for optimization
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Morning = lazy(() => import('./pages/Morning'));
const Mood = lazy(() => import('./pages/Mood'));
const Journal = lazy(() => import('./pages/Journal'));
const ARIA = lazy(() => import('./pages/ARIA'));
const WindDown = lazy(() => import('./pages/WindDown'));
const Settings = lazy(() => import('./pages/Settings'));
const Signup = lazy(() => import('./pages/Signup'));
const Pricing = lazy(() => import('./pages/Pricing'));
const Privacy = lazy(() => import('./pages/Privacy'));
const Terms = lazy(() => import('./pages/Terms'));
const Refund = lazy(() => import('./pages/Refund'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const Reset = lazy(() => import('./pages/Reset'));
const About = lazy(() => import('./pages/About'));




function AppRoutes() {
  const { user, isLoading } = useAuth();
  useCSRF();

  // Listen for push messages once at app startup
  useEffect(() => {
    try {
      listenForMessages();
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to start listening for FCM messages:', error);
      }
    }
  }, []);

  // Register or update FCM token on app load (when user rehydrates) or on successful login
  useEffect(() => {
    if (user) {
      try {
        registerFCMToken().catch((error) => {
          if (import.meta.env.DEV) {
            console.error('Failed to register FCM token:', error);
          }
        });
      } catch (error) {
        if (import.meta.env.DEV) {
          console.error('Error calling registerFCMToken:', error);
        }
      }
    }
  }, [user]);

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-bg">
        <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <Routes>
      {/* Redirect old login/signup pages to main dashboard, opening auth modal */}
      <Route path="/login" element={<Navigate to="/" replace state={{ openAuth: true }} />} />

      {/* Main app layout and routes */}
      <Route
        path="/*"
        element={
          <Layout>
            <Suspense fallback={
              <div className="min-h-[60vh] flex items-center justify-center bg-bg">
                <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
              </div>
            }>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/morning" element={<Morning />} />
                <Route path="/mood" element={<Mood />} />
                <Route path="/journal" element={<Journal />} />
                <Route path="/aria" element={<ARIA />} />
                <Route path="/wind-down" element={<WindDown />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/signup" element={<Signup />} />
                <Route path="/pricing" element={<Pricing />} />
                <Route path="/privacy" element={<Privacy />} />
                <Route path="/terms" element={<Terms />} />
                <Route path="/refund" element={<Refund />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                <Route path="/reset" element={<Reset />} />
                <Route path="/about" element={<About />} />
              </Routes>
            </Suspense>
          </Layout>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ARIAProvider>
        <BrowserRouter>
          <PWAInstallPrompt />
          <AppRoutes />
        </BrowserRouter>
      </ARIAProvider>
    </AuthProvider>
  );
}