import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { payments, profile as profileApi } from '@/lib/api';
import { Loader2, ShieldCheck, AlertCircle, Sparkles, ArrowLeft, Check, Lock } from 'lucide-react';
import GuestGate from '@/app/components/GuestGate';

export default function Billing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const [isPremium, setIsPremium] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Load user premium status and check if returning from PayPal
  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    async function init() {
      try {
        const prof = await profileApi.get();
        setIsPremium(!!prof.is_premium);

        // Check if returning from a successful PayPal checkout
        const isSuccess = searchParams.get('success') === 'true';
        const token = searchParams.get('token');

        if (isSuccess && token) {
          setProcessing(true);
          setMessage('Confirming your payment and setting up your subscription...');
          
          const storedPlanId = localStorage.getItem('mc_paypal_plan_id') || 'paypal-premium';
          
          const res = await payments.executePaypalSubscription(storedPlanId, token);
          if (res.success) {
            setSuccess(true);
            setIsPremium(true);
            setMessage('Your Premium subscription is now active! Enjoy unlimited access.');
            localStorage.removeItem('mc_paypal_plan_id');
          } else {
            setError(res.error || 'Failed to complete subscription payment. Please try again.');
          }
        } else if (searchParams.get('success') === 'false') {
          setError('Subscription checkout was cancelled.');
        }
      } catch (err: any) {
        setError(err.message || 'An error occurred while loading billing status.');
      } finally {
        setLoading(false);
        setProcessing(false);
      }
    }

    init();
  }, [user, searchParams]);

  // Load PayPal SDK Script
  useEffect(() => {
    const script = document.createElement('script');
    script.src = "https://www.paypal.com/sdk/js?client-id=your-client-id";
    script.async = true;
    document.head.appendChild(script);
    return () => {
      document.head.removeChild(script);
    };
  }, []);

  const handlePayPalSubscription = async () => {
    setProcessing(true);
    setError('');
    setMessage('Connecting to PayPal...');
    try {
      const res = await payments.createPaypalSubscription();
      if (res.error) {
        setError(res.error);
        setProcessing(false);
        return;
      }
      
      const token = res.plan_id;
      localStorage.setItem('mc_paypal_plan_id', token);
      
      // Redirect to PayPal (dynamically use the URL returned by the backend, falling back to live)
      const paypalUrl = res.approval_url || `https://www.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=${token}`;
      window.location.href = paypalUrl;
    } catch (err: any) {
      setError(err.message || 'Failed to create subscription plan.');
      setProcessing(false);
    }
  };

  if (!user) {
    return (
      <GuestGate
        title="Billing & Upgrade"
        description="Access premium features, unlimited AI reflections with ARIA, and advanced monthly emotion analytics."
        icon={<ShieldCheck className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  if (loading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
        <p className="text-sm text-text3">Loading billing status...</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8 animate-fadeIn text-left">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link 
          to="/pricing" 
          className="p-2 bg-bg3 border border-border hover:bg-bg4 rounded-xl text-text2 hover:text-text transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">BILLING</div>
          <h1 className="text-3xl font-light text-text">Upgrade & Payments</h1>
        </div>
      </div>

      {/* Main Card */}
      <div className="bg-bg2 border border-border rounded-[24px] p-6 sm:p-8 space-y-6 relative overflow-hidden shadow-xl">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(233,75,111,0.06),transparent_60%)] pointer-events-none" />

        {error && (
          <div className="bg-rose/10 border border-rose/30 text-rose text-sm rounded-xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {processing && (
          <div className="bg-accent-glow border border-accent/20 text-text2 text-sm rounded-xl p-4 flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-accent animate-spin shrink-0" />
            <div>{message}</div>
          </div>
        )}

        {success && (
          <div className="bg-green/10 border border-green/30 text-green text-sm rounded-xl p-4 flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-green shrink-0 mt-0.5" />
            <div>{message}</div>
          </div>
        )}

        {isPremium && !processing && !success && (
          <div className="space-y-6">
            <div className="flex items-center gap-4 bg-green/5 border border-green/20 rounded-xl p-4">
              <div className="w-10 h-10 rounded-full bg-green/10 flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-green" />
              </div>
              <div>
                <h3 className="font-semibold text-text text-sm">MindCradle Premium Active</h3>
                <p className="text-xs text-text3">Thank you for supporting MindCradle! You have full unlimited access.</p>
              </div>
            </div>
            
            <div className="pt-4 text-center">
              <Link 
                to="/dashboard" 
                className="inline-flex items-center justify-center px-6 py-2.5 bg-accent hover:bg-accent2 text-white text-sm font-semibold rounded-xl transition-all shadow-lg"
              >
                Go to Dashboard
              </Link>
            </div>
          </div>
        )}

        {!isPremium && !processing && (
          <div className="space-y-8 animate-fadeIn">
            {/* Plan Header */}
            <div className="border-b border-border/80 pb-6 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] tracking-widest font-bold text-rose bg-rose-dim border border-rose/20 px-3 py-1 rounded-full uppercase">
                  Premium Pass
                </span>
                <span className="text-[10.5px] uppercase tracking-wider font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-full">
                  7-Day Free Trial
                </span>
              </div>
              
              <div className="flex items-baseline gap-2 mt-4">
                <h2 className="text-4xl font-extralight text-text tracking-tight">$9.99</h2>
                <span className="text-sm font-normal text-text3">/ month</span>
              </div>
              
              <p className="text-sm text-text2 leading-relaxed font-light">
                Unlock all premium mental wellness tools, unlimited AI companion reflections, and detailed mood analytics.
              </p>
            </div>

            {/* Premium Features List */}
            <div className="space-y-4">
              <h4 className="text-xs font-semibold text-text3 uppercase tracking-wider">Features Included:</h4>
              <ul className="space-y-3.5">
                {[
                  "Unlimited morning & evening rituals",
                  "Unlimited chat & reflections with ARIA (AI Companion)",
                  "30-day automatic monthly emotion analytics",
                  "Detailed recovery pattern & theme insights",
                  "Full data export (GDPR compliant) & priority support",
                  "Ad-free focused meditation experience"
                ].map((feat, i) => (
                  <li key={i} className="flex items-start gap-3.5 text-sm text-text2">
                    <div className="w-5 h-5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                      <Check className="w-3.5 h-3.5" strokeWidth={3} />
                    </div>
                    <span className="font-light">{feat}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Subscribe Action */}
            <div className="pt-6 border-t border-border/80 space-y-4">
              <button
                onClick={handlePayPalSubscription}
                disabled={processing}
                className="w-full h-[54px] bg-gradient-to-r from-[#FFD140] via-[#FFB800] to-[#FFA800] text-[#003087] font-bold rounded-xl text-sm flex items-center justify-center gap-2.5 transition-all shadow-lg hover:shadow-[0_0_22px_rgba(255,184,0,0.3)] hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
              >
                {/* Custom SVG PayPal Monogram */}
                <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M20.067 8.478c0 3.238-2.316 6.386-5.882 6.386h-2.128c-.46 0-.853.332-.937.787l-1.042 5.56a.465.465 0 0 1-.46.389H6.467c-.297 0-.518-.268-.466-.56l2.368-12.63c.084-.455.477-.787.937-.787h5.187c3.566 0 5.574 1.706 5.574 3.85h-.004z" fill="#0079C1" />
                  <path d="M17.15 4.397c0 3.238-2.316 6.386-5.882 6.386H9.14c-.46 0-.853.332-.937.787L7.16 17.13c-.052.292.17.56.466.56h3.151c.46 0 .853-.332.937-.787l1.042-5.56a.465.465 0 0 1 .46-.389h2.128c3.566 0 5.574-1.706 5.574-3.85s-2.008-3.707-5.574-3.707H10.15c-.296 0-.518.268-.466.56l.942-5.02c.084-.455.477-.787.937-.787H12.18c3.566 0 4.97 1.636 4.97 3.774v.006z" fill="#00457C" />
                </svg>
                <span className="font-extrabold tracking-tight">Pay with PayPal</span>
              </button>
              
              <div className="flex items-center justify-center gap-1.5 text-[11px] text-text3">
                <Lock className="w-3.5 h-3.5 text-text3" />
                <span>Secured by PayPal encryption protocols. Cancel anytime.</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
