import { useAuth } from '@/lib/auth';

interface GuestGateProps {
  title: string;
  description: string;
  icon: React.ReactNode;
}

export default function GuestGate({ title, description, icon }: GuestGateProps) {
  const { setAuthModalOpen } = useAuth();

  return (
    <div className="flex flex-col items-center justify-center text-center p-8 py-16 min-h-[450px] max-w-md mx-auto animate-fadeIn">
      {/* Icon frame */}
      <div className="w-16 h-16 rounded-2xl bg-bg2 border border-border flex items-center justify-center text-accent mb-6 shadow-lg shadow-accent/5">
        {icon}
      </div>
      
      {/* Title */}
      <h2 className="font-[family-name:var(--font-serif)] text-2xl font-light text-text mb-3">
        {title}
      </h2>
      
      {/* Description */}
      <p className="text-sm text-text3 leading-relaxed mb-8">
        {description}
      </p>
      
      {/* Primary CTA */}
      <button
        type="button"
        onClick={() => setAuthModalOpen(true)}
        className="px-6 py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-xl font-medium text-sm hover:opacity-90 transition-all shadow-lg shadow-accent/10 cursor-pointer"
      >
        Sign in to unlock
      </button>
    </div>
  );
}
