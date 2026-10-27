import { useAuth } from '@/lib/auth';
import Logo from './Logo';
import { X } from 'lucide-react';
import CognitoAuthForm from './CognitoAuthForm';

export default function AuthCardModal() {
  const { authModalOpen, setAuthModalOpen } = useAuth();

  const handleClose = () => {
    setAuthModalOpen(false);
    sessionStorage.setItem('mc_signup_popup_shown', 'true');
  };

  if (!authModalOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="w-full max-w-[420px] bg-bg2 border border-border rounded-[24px] px-8 py-8 relative layer-4 animate-slideIn text-left">
        {/* Close button */}
        <button
          type="button"
          onClick={handleClose}
          className="absolute top-5 right-5 w-10 h-10 min-w-[40px] min-h-[40px] flex items-center justify-center text-text3 hover:text-text hover:bg-bg3/60 rounded-full cursor-pointer transition-colors"
          aria-label="Close"
        >
          <X size={18} />
        </button>

        {/* Logo */}
        <div className="flex justify-center mb-5">
          <Logo className="h-10 w-auto text-text" />
        </div>

        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">
          Direct Authentication
        </div>
        <h1 className="text-2xl font-light text-text mb-1.5">
          Join MindCradle
        </h1>
        <p className="text-xs text-text3 mb-5 leading-relaxed">
          Sign in or create your account directly to sync your growth journey.
        </p>

        <CognitoAuthForm
          onSuccess={handleClose}
          initialTab="signup"
          isModal={true}
        />
      </div>
    </div>
  );
}
