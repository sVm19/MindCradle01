import { useEffect, useState } from 'react';
import { Download, Sparkles, X } from 'lucide-react';

export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [showPrompt, setShowPrompt] = useState(false);

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      // Prevent Chrome 67 and earlier from automatically showing the prompt
      e.preventDefault();
      // Stash the event so it can be triggered later.
      setDeferredPrompt(e);
      // Delay showing the prompt to improve initial load performance & LCP
      setTimeout(() => {
        setShowPrompt(true);
      }, 5000);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstall = async () => {
    if (deferredPrompt) {
      // Show the install prompt
      deferredPrompt.prompt();
      // Wait for the user to respond to the prompt
      const { outcome } = await deferredPrompt.userChoice;
      if (import.meta.env.DEV) {
        console.log(`User response to the install prompt: ${outcome}`);
      }
      // We've used the prompt, and can't use it again
      setDeferredPrompt(null);
      setShowPrompt(false);
    }
  };

  if (!showPrompt) return null;

  return (
    <div className="fixed bottom-6 right-6 max-w-sm w-[calc(100vw-3rem)] md:w-96 bg-bg2/90 backdrop-blur-md border border-border/80 rounded-[20px] p-5 shadow-2xl z-[1000] animate-in fade-in slide-in-from-bottom-5 duration-300">
      {/* Ambient glow in background */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,rgba(240,147,160,0.08),transparent_60%)] pointer-events-none rounded-[20px]" />
      
      {/* Close button */}
      <button 
        onClick={() => setShowPrompt(false)}
        className="absolute top-4 right-4 text-text3 hover:text-text cursor-pointer transition-colors p-1 rounded-full hover:bg-white/5"
        aria-label="Close prompt"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="flex gap-4 items-start relative z-10">
        {/* App Icon Container */}
        <div className="w-12 h-12 rounded-xl border border-rose/30 bg-rose-dim flex items-center justify-center flex-shrink-0 text-rose select-none">
          <Sparkles className="w-6 h-6 animate-pulse" />
        </div>

        {/* Text Details */}
        <div className="flex-1">
          <h3 className="font-[family-name:var(--font-serif)] text-[17px] font-semibold text-text leading-tight mb-1 flex items-center gap-1.5">
            MindCradle App
          </h3>
          <p className="text-[13px] text-text3 leading-relaxed mb-4">
            Install the app on your home screen for quick offline access and daily wellness rituals.
          </p>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button 
              onClick={handleInstall}
              className="inline-flex items-center justify-center gap-1.5 h-9 px-4 bg-gradient-to-r from-[#E94B6F] to-[#f0739c] text-white hover:opacity-95 text-xs font-semibold rounded-full shadow-md shadow-[#E94B6F]/20 active:scale-[0.98] transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              Install
            </button>
            <button 
              onClick={() => setShowPrompt(false)}
              className="h-9 px-4 border border-border2 hover:border-text3 text-text2 hover:text-text text-xs font-semibold rounded-full bg-transparent active:scale-[0.98] transition-all cursor-pointer"
            >
              Not now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
