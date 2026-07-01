import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { useEffect } from 'react';
import { AuthProvider, useAuth } from '@/lib/auth';
import { ARIAProvider } from '@/context/ARIAContext';
import { registerFCMToken, listenForMessages } from '@/lib/firebase';
import { useCSRF } from '@/lib/csrf';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Morning from './pages/Morning';
import Mood from './pages/Mood';
import Journal from './pages/Journal';
import ARIA from './pages/ARIA';
import WindDown from './pages/WindDown';
import Settings from './pages/Settings';
import Signup from './pages/Signup';
import Pricing from './pages/Pricing';
import Privacy from './pages/Privacy';
import Terms from './pages/Terms';
import Refund from './pages/Refund';
import ForgotPassword from './pages/ForgotPassword';
import Reset from './pages/Reset';
import About from './pages/About';
import { PWAInstallPrompt } from './components/PWAInstallPrompt';



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