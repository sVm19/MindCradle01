import { useNavigate, Navigate } from 'react-router';
import Logo from '@/app/components/Logo';
import { useAuth } from '@/lib/auth';
import CognitoAuthForm from '@/app/components/CognitoAuthForm';

export default function Login() {
  const { user } = useAuth();
  const navigate = useNavigate();

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-[75vh] flex items-center justify-center p-4 animate-fadeIn">
      <div className="w-full max-w-[420px] bg-bg2 border border-border rounded-[24px] px-8 py-8 relative shadow-2xl animate-slideIn text-left">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <Logo className="h-10 w-auto text-text" />
        </div>

        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">
          Direct Authentication
        </div>
        <h1 className="text-2xl font-light text-text mb-2">
          Welcome to MindCradle
        </h1>
        <p className="text-xs text-text3 mb-5 leading-relaxed">
          Sign in or create an account to save your daily rituals and reflections.
        </p>

        <CognitoAuthForm
          onSuccess={() => navigate('/dashboard', { replace: true })}
          initialTab="signin"
          isModal={false}
        />
      </div>
    </div>
  );
}
