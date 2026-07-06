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
  const [trialStatus, setTrialStatus] = useState<{
    trial_active: boolean;
    days_remaining: number;
    trial_ends_at?: string;
    trial_used: boolean;
  }>({
    trial_active: false,
    days_remaining: 0,
    trial_used: false,
  });

  // Load user premium status
  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    async function init() {
      try {
        const prof = await profileApi.get();
        setIsPremium(!!prof.is_premium);

        const statusData = await payments.trialStatus();
        setTrialStatus(statusData);

        // Check if returning from a successful Creem checkout
        const isSuccess = searchParams.get('success') === 'true';
        if (isSuccess) {
          setSuccess(true);
          setIsPremium(true);
          setMessage('Your Premium subscription is now active! Enjoy unlimited access.');
        } else if (searchParams.get('success') === 'false') {
          setError('Subscription checkout was cancelled.');
        }
      } catch (err: any) {
        setError(err.message || 'An error occurred while loading billing status.');
      } finally {
        setLoading(false);
      }
    }

    init();
  }, [user, searchParams]);

  const handleCreemCheckout = async () => {
    setProcessing(true);
    setError('');
    setMessage('Connecting to Creem...');
    try {
      const res = await payments.createCreemCheckout();
      if (res.error) {
        setError(res.error);
        setProcessing(false);
        return;
      }
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      } else {
        throw new Error('No checkout URL returned.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create subscription checkout session.');
      setProcessing(false);
    }
  };

  const handleStartTrial = async () => {
    setProcessing(true);
    setError('');
    setMessage('Starting your 7-day free trial...');
    try {
      const res = await payments.startTrial();
      if (res.error) {
        setError(res.error);
        setProcessing(false);
        return;
      }
      if (res.success) {
        setSuccess(true);
        setIsPremium(true);
        setTrialStatus({
          trial_active: true,
          days_remaining: 7,
          trial_ends_at: res.trial_ends_at,
          trial_used: true
        });
        setMessage('Your 7-day Premium trial is now active! Enjoy unlimited features.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to start trial.');
    } finally {
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
            {trialStatus.trial_active ? (
              <div className="flex items-center gap-4 bg-accent/5 border border-accent/20 rounded-xl p-4">
                <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-accent animate-pulse" />
                </div>
                <div>
                  <h3 className="font-semibold text-text text-sm">Free Trial Active ✅</h3>
                  <p className="text-xs text-text3">
                    {trialStatus.days_remaining} days remaining. Trial expires on {trialStatus.trial_ends_at ? new Date(trialStatus.trial_ends_at).toLocaleDateString() : ''}.
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-4 bg-green/5 border border-green/20 rounded-xl p-4">
                <div className="w-10 h-10 rounded-full bg-green/10 flex items-center justify-center">
                  <ShieldCheck className="w-5 h-5 text-green" />
                </div>
                <div>
                  <h3 className="font-semibold text-text text-sm">MindCradle Premium Active</h3>
                  <p className="text-xs text-text3">Thank you for supporting MindCradle! You have full unlimited access.</p>
                </div>
              </div>
            )}
            
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
              {!trialStatus.trial_used ? (
                <button
                  onClick={handleStartTrial}
                  disabled={processing}
                  className="w-full h-[54px] bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-bold rounded-xl text-sm flex items-center justify-center gap-2.5 transition-all shadow-lg cursor-pointer"
                >
                  <span className="font-semibold tracking-tight">Start 7-Day Free Trial</span>
                </button>
              ) : (
                <button
                  onClick={handleCreemCheckout}
                  disabled={processing}
                  className="w-full h-[54px] bg-gradient-to-r from-violet-600 via-indigo-600 to-accent text-white font-bold rounded-xl text-sm flex items-center justify-center gap-2.5 transition-all duration-300 shadow-lg hover:shadow-[0_0_24px_rgba(139,92,246,0.35)] hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
                >
                  {/* Premium Credit Card SVG Monogram */}
                  <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="5" width="20" height="14" rx="2" />
                    <line x1="2" y1="10" x2="22" y2="10" />
                    <path d="M6 14h.01M10 14h2" />
                  </svg>
                  <span className="font-semibold tracking-tight">Pay with Creem</span>
                </button>
              )}
              
              <div className="flex items-center justify-center gap-1.5 text-[11px] text-text3">
                <Lock className="w-3.5 h-3.5 text-text3" />
                <span>
                  {!trialStatus.trial_used 
                    ? "No credit card required. Cancel anytime." 
                    : "Secured by Creem encryption protocols. Cancel anytime."}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
