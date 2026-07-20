import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from '@/lib/auth';
import { ARIAProvider } from '@/context/ARIAContext';
import { GrowthProvider, useGrowth } from '@/context/GrowthContext';
import { registerFCMToken, listenForMessages } from '@/lib/firebase';
import { useCSRF } from '@/lib/csrf';
import Layout from './components/Layout';

// Lazy-loaded page components for optimization
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Morning = lazy(() => import('./pages/Morning'));
const Mood = lazy(() => import('./pages/Mood'));
const Journal = lazy(() => import('./pages/Journal'));
const ARIA = lazy(() => import('./pages/ARIA'));
const WindDown = lazy(() => import('./pages/WindDown'));
const Settings = lazy(() => import('./pages/Settings'));
const Login = lazy(() => import('./pages/Login'));
const AuthCallback = lazy(() => import('./pages/AuthCallback'));
const MagicLinkRequest = lazy(() => import('./pages/MagicLinkRequest'));
const MagicLinkCallback = lazy(() => import('./pages/MagicLinkCallback'));
const Pricing = lazy(() => import('./pages/Pricing'));
const Privacy = lazy(() => import('./pages/Privacy'));
const Terms = lazy(() => import('./pages/Terms'));
const Refund = lazy(() => import('./pages/Refund'));
const About = lazy(() => import('./pages/About'));
const Features = lazy(() => import('./pages/Features'));
const Billing = lazy(() => import('./pages/Billing'));
const BillingSuccess = lazy(() => import('./pages/BillingSuccess'));
const BillingCancel = lazy(() => import('./pages/BillingCancel'));
const Insights = lazy(() => import('./pages/Insights'));
const Discoveries = lazy(() => import('./pages/Discoveries'));
const Timeline = lazy(() => import('./pages/Timeline'));
const Understanding = lazy(() => import('./pages/Understanding'));
const GrowthDashboard = lazy(() => import('./pages/GrowthDashboard'));
const Blog = lazy(() => import('./pages/Blog'));
const BlogPost = lazy(() => import('./pages/BlogPost'));
const Docs = lazy(() => import('./pages/Docs'));
const Resources = lazy(() => import('./pages/Resources'));





function AppRoutes() {
  const { user, isLoading } = useAuth();
  const { trackEvent } = useGrowth();
  const location = useLocation();
  useCSRF();

  // Intercept and block sensitive file probes (.env, .git, .bak, config files)
  const probePath = location.pathname.toLowerCase();
  const isSensitiveProbe = 
    probePath.includes('.env') || 
    probePath.includes('.git') || 
    probePath.includes('.bak') || 
    probePath.includes('.sql') || 
    probePath.includes('.db') || 
    probePath.includes('.key') || 
    probePath.includes('.pem') || 
    probePath.includes('config.json') || 
    probePath.includes('wp-config') || 
    probePath.includes('server.js');

  if (isSensitiveProbe) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0c0714] text-white p-8 text-center font-sans">
        <div className="max-w-md space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-rose/10 border border-rose/30 flex items-center justify-center text-rose mx-auto text-2xl font-bold">
            404
          </div>
          <h1 className="text-xl font-semibold">404 — Access Restricted / Not Found</h1>
          <p className="text-sm text-text3 leading-relaxed">
            The requested file path or configuration resource does not exist or access is strictly blocked.
          </p>
          <a
            href="/"
            className="inline-block px-6 py-3 bg-gradient-to-r from-accent2 to-accent text-[#05020c] font-bold text-xs rounded-full hover:opacity-90 transition-all shadow-md"
          >
            Return to MindCradle →
          </a>
        </div>
      </div>
    );
  }

  // Auto-track pageviews
  useEffect(() => {
    if (user) {
      trackEvent('page_view', { path: location.pathname });
    }
  }, [location.pathname, user]);

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
      {/* Dedicated Login page handles traditional Sign In + Google OAuth */}
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/auth/magic-link" element={<MagicLinkRequest />} />
      <Route path="/auth/magic" element={<MagicLinkCallback />} />
      <Route path="/magic-login" element={<MagicLinkCallback />} />

      {/* Main app layout and routes */}
      <Route
        path="/*"
        element={
          <Layout>
            <Suspense fallback={
              <div className="min-h-[75vh] flex-grow flex items-center justify-center bg-bg w-full">
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
                <Route path="/settings/understanding" element={<Understanding />} />
                <Route path="/signup" element={<Navigate to="/login" replace />} />
                <Route path="/pricing" element={<Pricing />} />
                <Route path="/privacy" element={<Privacy />} />
                <Route path="/terms" element={<Terms />} />
                <Route path="/refund" element={<Refund />} />
                <Route path="/forgot-password" element={<Navigate to="/login" replace />} />
                <Route path="/reset" element={<Navigate to="/login" replace />} />
                <Route path="/about" element={<About />} />
                <Route path="/features" element={<Features />} />
                <Route path="/articles" element={<Resources />} />
                <Route path="/blog" element={<Blog />} />
                <Route path="/blog/:slug" element={<BlogPost />} />
                <Route path="/docs" element={<Docs />} />
                <Route path="/docs/:slug" element={<Docs />} />
                <Route path="/billing" element={<Billing />} />
                <Route path="/billing/success" element={<BillingSuccess />} />
                <Route path="/billing/cancel" element={<BillingCancel />} />
                <Route path="/insights" element={<Insights />} />
                <Route path="/discoveries" element={<Discoveries />} />
                <Route path="/timeline" element={<Timeline />} />
                <Route path="/admin/growth" element={<GrowthDashboard />} />
              </Routes>
            </Suspense>
          </Layout>
        }
      />
    </Routes>
  );
}

export default function App() {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '959765770210-ke5oeq1e67bo6a8051259qgi3ek24ipj.apps.googleusercontent.com';

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      (window as any).deferredPrompt = e;
      window.dispatchEvent(new CustomEvent('pwa-prompt-available'));
    };
    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <AuthProvider>
        <GrowthProvider>
          <ARIAProvider>
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </ARIAProvider>
        </GrowthProvider>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}
