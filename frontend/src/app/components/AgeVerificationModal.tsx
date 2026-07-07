import { useState } from 'react';
import { auth as authApi } from '@/lib/api';
import { ShieldAlert, Phone, MessageSquare, AlertCircle, Check } from 'lucide-react';

interface AgeVerificationModalProps {
  isOpen: boolean;
  onVerified: () => void;
  onDeclined: () => void;
}

export default function AgeVerificationModal({ isOpen, onVerified, onDeclined }: AgeVerificationModalProps) {
  const [isChecked, setIsChecked] = useState(false);
  const [showCrisis, setShowCrisis] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleYes = async () => {
    setError('');
    if (!isChecked) {
      setError('Please acknowledge the checkbox statement before proceeding.');
      return;
    }

    setLoading(true);
    try {
      await authApi.verifyAge(true);
      localStorage.setItem('age_verified', 'true');
      setLoading(false);
      onVerified();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Age verification failed. Please try again.');
      setLoading(false);
    }
  };

  const handleNo = () => {
    // Show crisis resources screen
    setShowCrisis(true);
  };

  const handleContinueUnderage = () => {
    localStorage.setItem('age_verified', 'false');
    onDeclined();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-fadeIn">
      <div className="bg-bg2 border border-border w-full max-w-md rounded-2xl shadow-2xl overflow-hidden p-6 text-left space-y-6 animate-slideIn">
        
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-border pb-4">
          <div className="w-10 h-10 rounded-full bg-accent/15 flex items-center justify-center text-accent">
            <ShieldAlert size={22} />
          </div>
          <div>
            <h2 className="text-lg font-light text-text">Age Verification</h2>
            <p className="text-xs text-text3">MindCradle Safety Compliance</p>
          </div>
        </div>

        {!showCrisis ? (
          /* Main Verification Step */
          <div className="space-y-5">
            <p className="text-sm text-text2 leading-relaxed">
              MindCradle's AI companion **ARIA** is designed for users **18 and older**. Please confirm your age.
            </p>

            {error && (
              <div className="bg-rose/10 border border-rose/30 text-rose text-xs rounded-xl p-3 flex items-start gap-2">
                <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Checkbox */}
            <label className="flex gap-3 items-start cursor-pointer group select-none bg-bg3/50 border border-border/40 rounded-xl p-3.5 hover:border-border transition-all">
              <div className="relative mt-0.5">
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={(e) => setIsChecked(e.target.checked)}
                  className="sr-only"
                />
                <div className={`w-5 h-5 rounded border transition-all flex items-center justify-center ${isChecked ? 'bg-accent border-accent text-white' : 'border-border bg-bg3 group-hover:border-border2'}`}>
                  {isChecked && <Check size={14} />}
                </div>
              </div>
              <span className="text-xs text-text2 leading-relaxed">
                I understand ARIA is **not** a substitute for professional clinical services or emergency response.
              </span>
            </label>

            <div className="space-y-2.5">
              <div className="text-xs text-text3 font-medium uppercase tracking-wider text-center">Are you 18 years or older?</div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleYes}
                  disabled={loading}
                  className="flex-1 py-3 bg-gradient-to-r from-accent2 to-accent text-white rounded-xl font-semibold text-sm hover:opacity-95 transition-all disabled:opacity-50 flex justify-center items-center gap-1.5"
                >
                  {loading ? 'Verifying...' : "Yes, I'm 18+"}
                </button>
                <button
                  type="button"
                  onClick={handleNo}
                  disabled={loading}
                  className="flex-1 py-3 bg-bg3 border border-border text-text2 hover:text-text rounded-xl font-medium text-sm hover:bg-bg4 transition-all disabled:opacity-50"
                >
                  No, I'm under 18
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Underage Crisis Screen Step */
          <div className="space-y-5 animate-fadeIn">
            <div className="space-y-1.5">
              <p className="text-sm text-text leading-relaxed font-medium">
                ARIA is only available for users 18+.
              </p>
              <p className="text-xs text-text2 leading-relaxed">
                If you need assistance or someone to talk to, please reach out to a trusted professional, supporter, or one of these free services:
              </p>
            </div>

            {/* Helpline List */}
            <div className="space-y-2">
              <a
                href="tel:988"
                className="w-full flex items-center gap-3 px-4 py-3 bg-rose/10 hover:bg-rose/25 border border-rose/30 rounded-xl text-left text-rose transition-all"
              >
                <Phone size={16} />
                <div>
                  <div className="text-xs font-semibold">988 Suicide & Crisis Lifeline</div>
                  <div className="text-[10px] opacity-80">Call or Text 988 (Free, Confidential, 24/7)</div>
                </div>
              </a>
              <a
                href="sms:741741?&body=HOME"
                className="w-full flex items-center gap-3 px-4 py-3 bg-indigo/10 hover:bg-indigo/25 border border-indigo/30 rounded-xl text-left text-indigo-400 transition-all"
              >
                <MessageSquare size={16} />
                <div>
                  <div className="text-xs font-semibold">Crisis Text Line</div>
                  <div className="text-[10px] opacity-80">Text HOME to 741741 (Free, 24/7 support)</div>
                </div>
              </a>
            </div>

            <div className="border-t border-border pt-4">
              <button
                type="button"
                onClick={handleContinueUnderage}
                className="w-full py-3 bg-bg3 border border-border hover:bg-bg4 text-text2 hover:text-text rounded-xl font-medium text-sm transition-all"
              >
                Continue to MindCradle App
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
