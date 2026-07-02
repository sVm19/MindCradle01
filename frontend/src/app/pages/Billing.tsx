import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { payments, profile as profileApi } from '@/lib/api';
import { Loader2, ShieldCheck, AlertCircle, Sparkles, ArrowLeft, Check } from 'lucide-react';
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
      
      // Redirect to PayPal Express Checkout Sandbox/Production page
      const paypalUrl = `https://www.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=${token}`;
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
          <div className="space-y-6">
            <div className="border-b border-border pb-6 space-y-2">
              <span className="text-xs font-semibold text-rose bg-rose-dim border border-rose/10 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                Premium Monthly
              </span>
              <h2 className="text-3xl font-light text-text mt-4">
                $9.99<span className="text-sm font-normal text-text3"> / month</span>
              </h2>
              <p className="text-sm text-text2">
                Unlock all advanced wellness and AI features in MindCradle.
              </p>
            </div>

            {/* Premium Features List */}
            <ul className="space-y-3">
              {[
                "Unlimited morning & evening rituals",
                "Unlimited conversation with ARIA (AI Companion)",
                "30-day automatic monthly emotion analytics",
                "Full data export and privacy-first logs",
                "Priority response time and support"
              ].map((feat, i) => (
                <li key={i} className="flex items-center gap-3 text-sm text-text2">
                  <Check className="w-4 h-4 text-green shrink-0" />
                  <span>{feat}</span>
                </li>
              ))}
            </ul>

            {/* Subscribe Action */}
            <div className="pt-6 space-y-4">
              <button
                onClick={handlePayPalSubscription}
                disabled={processing}
                className="w-full h-[52px] bg-[#FFB730] hover:bg-[#F2AE2B] text-[#003087] font-bold rounded-xl text-sm flex items-center justify-center gap-2.5 transition-all shadow-md cursor-pointer hover:scale-[1.01]"
              >
                <Sparkles className="w-4 h-4 text-[#003087]" />
                Subscribe with PayPal
              </button>
              
              <p className="text-[11px] text-text3 text-center">
                7 days free trial, cancel anytime. Processed securely via PayPal encryption protocols.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
