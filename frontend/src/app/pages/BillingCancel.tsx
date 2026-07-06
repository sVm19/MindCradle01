import { useNavigate } from 'react-router';
import { AlertCircle, ArrowLeft } from 'lucide-react';

export default function BillingCancel() {
  const navigate = useNavigate();
  
  return (
    <div className="max-w-md mx-auto bg-bg2 text-text rounded-[28px] border border-border shadow-2xl p-8 sm:p-12 text-center animate-fadeIn space-y-6">
      <div className="w-16 h-16 rounded-full bg-rose/10 border border-rose/20 text-rose flex items-center justify-center mx-auto shadow-[0_0_20px_rgba(233,75,111,0.2)]">
        <AlertCircle className="w-8 h-8" />
      </div>
      
      <div className="space-y-2">
        <h1 className="font-[family-name:var(--font-serif)] text-3xl font-light text-text">
          Payment Cancelled
        </h1>
        <p className="text-sm text-text3 font-light leading-relaxed">
          Your subscription was not completed. You can still enjoy our free tier or try again anytime.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 pt-4">
        <button 
          onClick={() => navigate('/pricing')}
          className="flex-1 py-3 px-6 bg-accent hover:bg-accent2 text-white font-semibold rounded-xl text-sm transition-all shadow-lg cursor-pointer"
        >
          Try Again
        </button>
        <button 
          onClick={() => navigate('/dashboard')}
          className="flex-1 py-3 px-6 bg-bg3 border border-border hover:bg-bg4 text-text2 hover:text-text font-semibold rounded-xl text-sm transition-all cursor-pointer flex items-center justify-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Dashboard</span>
        </button>
      </div>
    </div>
  );
}
