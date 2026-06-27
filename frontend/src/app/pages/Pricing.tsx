import { useState, useEffect } from 'react';
import { Check, Star, HelpCircle, ArrowRight, Sparkles, CreditCard, Lock, RefreshCw, X } from 'lucide-react';
import { Link } from 'react-router';
import { useAuth } from '@/lib/auth';
import { billing, profile as profileApi, type ProfileResponse } from '@/lib/api';

export default function Pricing() {
  const { user } = useAuth();
  const [profileData, setProfileData] = useState<ProfileResponse | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [emailSubscribed, setEmailSubscribed] = useState(false);
  const [emailInput, setEmailInput] = useState('');

  // Checkout modal states
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [paymentSuccess, setPaymentSuccess] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  // Cancellation modal states
  const [isCancelConfirmOpen, setIsCancelConfirmOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  // Load user profile on mount / auth change
  useEffect(() => {
    if (user) {
      setLoadingProfile(true);
      profileApi.get()
        .then(data => setProfileData(data))
        .catch(err => console.error("Error fetching profile:", err))
        .finally(() => setLoadingProfile(false));
    } else {
      setProfileData(null);
    }
  }, [user]);

  const handleSubscribeUpdates = (e: React.FormEvent) => {
    e.preventDefault();
    if (emailInput.trim()) {
      setEmailSubscribed(true);
      setEmailInput('');
    }
  };

  // Card input formatters
  const formatCardNumber = (value: string) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = (matches && matches[0]) || '';
    const parts = [];

    for (let i = 0, len = match.length; i < len; i += 4) {
      parts.push(match.substring(i, i + 4));
    }

    if (parts.length > 0) {
      return parts.join(' ');
    } else {
      return v;
    }
  };

  const formatExpiry = (value: string) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    if (v.length >= 2) {
      return `${v.substring(0, 2)}/${v.substring(2, 4)}`;
    }
    return v;
  };

  // Submit checkout handler
  const handleCheckoutSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPaymentError(null);
    setPaymentSuccess(null);
    setProcessing(true);

    try {
      const res = await billing.checkout(cardNumber, cvc, expiry);
      if (res.status === 'success') {
        setPaymentSuccess('Your Premium subscription has been successfully activated!');
        // Reload user profile
        const updatedProfile = await profileApi.get();
        setProfileData(updatedProfile);
        setTimeout(() => {
          setIsCheckoutOpen(false);
          setCardNumber('');
          setExpiry('');
          setCvc('');
          setPaymentSuccess(null);
        }, 2000);
      } else {
        setPaymentError(res.message || 'Payment verification failed.');
      }
    } catch (err: any) {
      setPaymentError(err.message || 'Failed to process payment. Please verify card credentials.');
    } finally {
      setProcessing(false);
    }
  };

  // Submit cancellation handler
  const handleCancelSubscription = async () => {
    setPaymentError(null);
    setCancelling(true);

    try {
      const res = await billing.cancel();
      if (res.status === 'success') {
        // Reload user profile
        const updatedProfile = await profileApi.get();
        setProfileData(updatedProfile);
        setIsCancelConfirmOpen(false);
      } else {
        alert(res.message || 'Failed to cancel subscription.');
      }
    } catch (err: any) {
      alert(err.message || 'An error occurred during cancellation.');
    } finally {
      setCancelling(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12 space-y-16 animate-fadeIn text-left">
      {/* Header Section */}
      <header className="text-center space-y-4 max-w-2xl mx-auto">
        <h1 className="font-[family-name:var(--font-serif)] text-3xl sm:text-4xl lg:text-5xl font-light text-text leading-tight">
          Simple, Transparent Pricing
        </h1>
        <p className="text-sm sm:text-base text-text3 font-light leading-relaxed">
          Choose the plan that fits your wellness journey
        </p>
      </header>

      {/* Pricing Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch max-w-4xl mx-auto">
        
        {/* Free Plan Card */}
        <div className="bg-slate-50 text-slate-900 border border-slate-200 rounded-[24px] p-8 flex flex-col justify-between shadow-lg relative overflow-hidden transition-all duration-300 hover:-translate-y-1">
          <div className="space-y-6">
            <div>
              <span className="text-xs uppercase tracking-wider font-semibold text-slate-500 bg-slate-200/60 px-3 py-1 rounded-full">
                Free
              </span>
              <h2 className="font-[family-name:var(--font-serif)] text-3xl font-light mt-4 text-slate-900">
                $0<span className="text-sm font-normal text-slate-500">/month</span>
              </h2>
              <p className="text-sm text-slate-600 mt-2 font-medium">
                Perfect for getting started
              </p>
            </div>

            {/* Features list */}
            <ul className="space-y-3.5 text-left border-t border-slate-200/80 pt-6">
              {[
                "Daily mood tracking",
                "1 ritual per day",
                "50 ARIA messages/day",
                "Basic journal",
                "Dashboard insights"
              ].map((feature, i) => (
                <li key={i} className="flex items-start gap-3 text-slate-700 text-sm">
                  <Check className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" strokeWidth={3} />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="pt-8">
            {user ? (
              profileData?.is_premium ? (
                <button
                  onClick={() => setIsCancelConfirmOpen(true)}
                  className="w-full h-[48px] border border-red-200 hover:bg-red-50 text-red-600 rounded-xl text-sm font-semibold flex items-center justify-center transition-all cursor-pointer"
                >
                  Downgrade to Free
                </button>
              ) : (
                <div className="w-full h-[48px] border border-slate-300 bg-slate-100 text-slate-500 rounded-xl text-sm font-semibold flex items-center justify-center select-none">
                  Your Current Plan
                </div>
              )
            ) : (
              <Link
                to="/signup"
                className="inline-flex items-center justify-center gap-2 w-full h-[48px] bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-sm font-semibold transition-all shadow-md cursor-pointer"
              >
                Get Started - Free <ArrowRight className="w-4 h-4" />
              </Link>
            )}
          </div>
        </div>

        {/* Premium Plan Card */}
        <div 
          className="bg-bg2 border-2 rounded-[24px] p-8 flex flex-col justify-between shadow-2xl relative overflow-hidden transition-all duration-300 hover:-translate-y-1"
          style={{ borderColor: "#E94B6F" }}
        >
          {/* Subtle glow background */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(233,75,111,0.1),transparent_60%)] pointer-events-none" />

          {/* Recommended badge */}
          <div className="absolute top-4 right-4">
            <span 
              className="inline-flex items-center gap-1 text-[10.5px] uppercase tracking-wider font-semibold text-white px-3 py-1 rounded-full shadow-lg"
              style={{ backgroundColor: "#E94B6F" }}
            >
              <Star className="w-3.5 h-3.5" fill="white" /> Recommended
            </span>
          </div>

          <div className="space-y-6">
            <div>
              <span className="text-xs uppercase tracking-wider font-semibold text-rose bg-rose-dim border border-rose/20 px-3 py-1 rounded-full">
                Premium
              </span>
              <h2 className="font-[family-name:var(--font-serif)] text-3xl font-light text-text mt-4">
                $9.99<span className="text-sm font-normal text-text3">/month</span>
              </h2>
              <p className="text-sm text-text2 mt-2">
                Unlock your full potential
              </p>
            </div>

            {/* Features list */}
            <ul className="space-y-3.5 text-left border-t border-border pt-6">
              {[
                "Everything in Free",
                "Unlimited rituals",
                "Unlimited ARIA chat",
                "30-day emotion analytics",
                "Recovery pattern detection",
                "Export your data",
                "No ads",
                "Priority support"
              ].map((feature, i) => (
                <li key={i} className="flex items-start gap-3 text-text2 text-sm">
                  <Check className="w-5 h-5 text-green shrink-0 mt-0.5" strokeWidth={3} />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="pt-8 space-y-3 text-center">
            {user ? (
              profileData?.is_premium ? (
                <div 
                  className="w-full h-[48px] text-white rounded-xl text-sm font-semibold flex items-center justify-center select-none"
                  style={{ 
                    backgroundColor: "#10B981",
                    boxShadow: "0 4px 14px rgba(16, 185, 129, 0.3)"
                  }}
                >
                  ✓ Active Premium Plan
                </div>
              ) : (
                <button
                  onClick={() => setIsCheckoutOpen(true)}
                  className="inline-flex items-center justify-center gap-2 w-full h-[48px] text-white rounded-xl text-sm font-semibold transition-all shadow-lg hover:brightness-110 cursor-pointer"
                  style={{ 
                    backgroundColor: "#E94B6F",
                    boxShadow: "0 4px 14px rgba(233, 75, 111, 0.3)"
                  }}
                >
                  Start Free Trial <Sparkles className="w-4 h-4 text-white" />
                </button>
              )
            ) : (
              <Link
                to="/signup"
                className="inline-flex items-center justify-center gap-2 w-full h-[48px] text-white rounded-xl text-sm font-semibold transition-all shadow-lg hover:brightness-110 cursor-pointer"
                style={{ 
                  backgroundColor: "#E94B6F",
                  boxShadow: "0 4px 14px rgba(233, 75, 111, 0.3)"
                }}
              >
                Start Free Trial <Sparkles className="w-4 h-4 text-white" />
              </Link>
            )}
            {profileData?.is_premium && (
              <button
                onClick={() => setIsCancelConfirmOpen(true)}
                className="text-xs text-text3 hover:text-rose transition-all underline cursor-pointer"
              >
                Cancel Subscription
              </button>
            )}
            {!profileData?.is_premium && (
              <span className="block text-[11px] text-text3 font-medium">
                7 days free, then $9.99/month. Cancel anytime.
              </span>
            )}
          </div>
        </div>

      </div>

      {/* FAQ Section */}
      <section className="max-w-3xl mx-auto space-y-8 pt-8 border-t border-border/65">
        <div className="text-center">
          <h2 className="font-[family-name:var(--font-serif)] text-2xl font-light text-text">
            Frequently Asked Questions
          </h2>
          <p className="text-xs text-text3 mt-1.5">
            Everything you need to know about our plans
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-8">
          {[
            {
              q: "Can I cancel anytime?",
              a: "Yes, cancel your subscription anytime with one click. No questions asked."
            },
            {
              q: "Is there a long-term commitment?",
              a: "No. Pay monthly, cancel monthly. Complete flexibility."
            },
            {
              q: "Do you offer annual pricing?",
              a: "Coming soon! Sign up for updates."
            },
            {
              q: "What happens to my data if I cancel?",
              a: "Your data stays with you. Export it anytime."
            }
          ].map((faq, i) => (
            <div key={i} className="bg-bg2 border border-border p-5 rounded-[20px] space-y-2 text-left relative overflow-hidden">
              <div className="absolute top-4 right-4 text-text3/15">
                <HelpCircle className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-sm text-text pr-6">
                {faq.q}
              </h3>
              <p className="text-xs text-text2 leading-relaxed">
                {faq.a}
              </p>
              {faq.q.includes("annual") && (
                <div className="pt-2">
                  {emailSubscribed ? (
                    <span className="text-[10px] text-green bg-green-dim border border-green/20 px-2.5 py-0.5 rounded-full font-medium">
                      ✓ Subscribed to updates!
                    </span>
                  ) : (
                    <form onSubmit={handleSubscribeUpdates} className="flex gap-2 max-w-[240px]">
                      <input 
                        type="email" 
                        value={emailInput}
                        onChange={(e) => setEmailInput(e.target.value)}
                        placeholder="your@email.com" 
                        className="bg-bg border border-border rounded-lg px-2.5 py-1 text-[11px] text-text flex-1 focus:outline-none focus:border-rose/50"
                        required
                      />
                      <button 
                        type="submit" 
                        className="bg-rose text-white text-[10px] font-semibold px-3 py-1 rounded-lg hover:opacity-90 transition-all cursor-pointer"
                      >
                        Notify me
                      </button>
                    </form>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Checkout/Payment Modal */}
      {isCheckoutOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#120921] border border-border w-full max-w-md rounded-[28px] p-6 sm:p-8 space-y-6 shadow-2xl relative animate-scaleIn text-left">
            <button 
              onClick={() => setIsCheckoutOpen(false)}
              className="absolute top-4 right-4 text-text3 hover:text-text transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <header className="space-y-2 border-b border-border pb-4">
              <h3 className="text-xl font-semibold text-text flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-rose" /> Upgrade to Premium
              </h3>
              <p className="text-xs text-text3">
                Enter your card details to activate your 7-day free trial.
              </p>
            </header>

            <form onSubmit={handleCheckoutSubmit} className="space-y-4">
              {paymentError && (
                <div className="bg-rose-dim border border-rose/30 text-rose text-xs p-3 rounded-xl">
                  {paymentError}
                </div>
              )}
              {paymentSuccess && (
                <div className="bg-green-dim border border-green/30 text-green text-xs p-3 rounded-xl">
                  {paymentSuccess}
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text2">Card Number</label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    disabled={processing}
                    placeholder="4111 2222 3333 4444"
                    maxLength={19}
                    value={cardNumber}
                    onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                    className="bg-bg border border-border rounded-xl pl-10 pr-4 py-2.5 text-sm text-text focus:outline-none focus:border-rose/50 w-full"
                  />
                  <CreditCard className="w-4 h-4 text-text3 absolute left-3.5 top-3.5" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text2">Expiration</label>
                  <input
                    type="text"
                    required
                    disabled={processing}
                    placeholder="MM/YY"
                    maxLength={5}
                    value={expiry}
                    onChange={(e) => setExpiry(formatExpiry(e.target.value))}
                    className="bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-text focus:outline-none focus:border-rose/50 w-full"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text2">CVC</label>
                  <input
                    type="text"
                    required
                    disabled={processing}
                    placeholder="123"
                    maxLength={4}
                    value={cvc}
                    onChange={(e) => setCvc(e.target.value.replace(/[^0-9]/g, ''))}
                    className="bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-text focus:outline-none focus:border-rose/50 w-full"
                  />
                </div>
              </div>

              <div className="bg-bg/40 rounded-xl p-3.5 border border-border/50 text-[11px] text-text3 flex items-start gap-2.5">
                <Lock className="w-4 h-4 text-green shrink-0 mt-0.5" />
                <div>
                  Your payment credentials are secure and processed through mock encryption protocols to guarantee database-wide authorization checks.
                </div>
              </div>

              <div className="pt-2 flex gap-3">
                <button
                  type="button"
                  disabled={processing}
                  onClick={() => setIsCheckoutOpen(false)}
                  className="flex-1 h-[44px] border border-border hover:bg-bg rounded-xl text-sm font-semibold text-text transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={processing}
                  className="flex-1 h-[44px] text-white rounded-xl text-sm font-semibold transition-all hover:brightness-110 flex items-center justify-center gap-2 cursor-pointer"
                  style={{ backgroundColor: "#E94B6F" }}
                >
                  {processing ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    'Activate Trial'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cancellation Confirmation Modal */}
      {isCancelConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#120921] border border-border w-full max-w-sm rounded-[28px] p-6 space-y-6 shadow-2xl relative animate-scaleIn text-left">
            <button 
              onClick={() => setIsCancelConfirmOpen(false)}
              className="absolute top-4 right-4 text-text3 hover:text-text transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-text">
                Cancel Subscription?
              </h3>
              <p className="text-xs text-text3 leading-relaxed">
                Are you sure you want to cancel your Premium subscription? You will lose access to unlimited rituals, unlimited ARIA chat, and advanced analytics.
              </p>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                disabled={cancelling}
                onClick={() => setIsCancelConfirmOpen(false)}
                className="flex-1 h-[40px] border border-border hover:bg-bg rounded-lg text-xs font-semibold text-text transition-all cursor-pointer"
              >
                Keep Premium
              </button>
              <button
                disabled={cancelling}
                onClick={handleCancelSubscription}
                className="flex-1 h-[40px] bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                {cancelling ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  'Yes, Cancel'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
