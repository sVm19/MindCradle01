import { useEffect } from 'react';
import { useNavigate } from 'react-router';
import { ShieldCheck, ArrowRight } from 'lucide-react';

export default function BillingSuccess() {
  const navigate = useNavigate();
  
  useEffect(() => {
    const timer = setTimeout(() => {
      navigate('/dashboard');
    }, 3000);
    return () => clearTimeout(timer);
  }, [navigate]);
  
  return (
    <div className="max-w-md mx-auto bg-bg2 text-text rounded-[28px] border border-border shadow-2xl p-8 sm:p-12 text-center animate-fadeIn space-y-6">
      <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto shadow-[0_0_20px_rgba(16,185,129,0.2)]">
        <ShieldCheck className="w-8 h-8" />
      </div>
      
      <div className="space-y-2">
        <h1 className="font-[family-name:var(--font-serif)] text-3xl font-light text-text">
          Upgrade Successful!
        </h1>
        <p className="text-sm text-text3 font-light leading-relaxed">
          Welcome to MindCradle Premium. Your premium pass is now active, unlocking unlimited routines and ARIA support.
        </p>
      </div>

      <div className="bg-bg rounded-2xl p-4 border border-border/80 text-xs text-text3 font-light">
        Redirecting to dashboard in 3 seconds...
      </div>

      <button 
        onClick={() => navigate('/dashboard')}
        className="w-full py-3 px-6 bg-accent hover:bg-accent2 text-white font-semibold rounded-xl text-sm flex items-center justify-center gap-2 transition-all shadow-lg cursor-pointer"
      >
        <span>Go to Dashboard Now</span>
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
