import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';

// Steps list matching the product requirements
const TERMINAL_SEQUENCES = [
  {
    type: 'analysis',
    title: 'Analyzing personal growth...',
    steps: [
      { text: 'Analyzing personal growth...', progress: 40 },
      { text: 'Reading journal history...', progress: 70 },
      { text: 'Finding emotional patterns...', progress: 90 },
      { text: 'Comparing 184 reflections...', progress: 100 },
      { text: 'Pattern found.', progress: 100, success: true }
    ]
  },
  {
    type: 'message',
    icon: '💜',
    content: (
      <div className="space-y-4">
        <p className="text-sm font-medium text-text">I noticed something.</p>
        <p className="text-[15px] font-light leading-relaxed text-text2">
          This is the first month you described mornings as{' '}
          <span className="text-teal font-semibold drop-shadow-[0_0_8px_var(--teal-glow)]">"calm"</span>
          {' '}more often than{' '}
          <span className="text-rose font-semibold drop-shadow-[0_0_8px_var(--rose-glow)]">"busy."</span>
        </p>
      </div>
    )
  },
  {
    type: 'analysis',
    title: 'Searching memories...',
    steps: [
      { text: 'Searching memory...', progress: 100 },
      { text: 'Comparing past reflections...', progress: 100 },
      { text: 'Finding growth...', progress: 100, success: true }
    ]
  },
  {
    type: 'message',
    icon: '✦',
    content: (
      <div className="space-y-4 text-left">
        <div className="space-y-1.5 opacity-80">
          <p className="text-xs text-text3">Three months ago, you wrote:</p>
          <p className="text-[13px] italic text-amber font-light border-l-2 border-amber/30 pl-3">
            "I don't think I'll ever get through this."
          </p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-text3">Today:</p>
          <p className="text-sm text-text font-medium">
            You didn't mention it once.
          </p>
        </div>
      </div>
    )
  },
  {
    type: 'analysis',
    title: 'Generating predictive models...',
    steps: [
      { text: 'Generating tomorrow...', progress: 100, success: true }
    ]
  },
  {
    type: 'message',
    icon: '🔮',
    content: (
      <div className="space-y-4">
        <p className="text-[15px] font-light leading-relaxed text-text2">
          Tomorrow is usually your{' '}
          <span className="text-accent font-semibold drop-shadow-[0_0_8px_var(--accent-glow)]">busiest day.</span>
        </p>
        <p className="text-sm text-text font-medium">
          Let's prepare together.
        </p>
      </div>
    )
  }
];

export default function AriaTerminalCard() {
  const [sequenceIndex, setSequenceIndex] = useState(0);
  const [visibleStepCount, setVisibleStepCount] = useState(0);
  const currentSequence = TERMINAL_SEQUENCES[sequenceIndex];

  // Auto-advance steps in analysis mode, then auto-advance to next sequence
  useEffect(() => {
    if (currentSequence.type === 'analysis') {
      setVisibleStepCount(0);
      const steps = currentSequence.steps || [];
      
      // Reveal each step sequentially
      const timers: any[] = [];
      steps.forEach((_, idx) => {
        const t = setTimeout(() => {
          setVisibleStepCount(idx + 1);
        }, idx * 1000 + 400); // delay each step entry
        timers.push(t);
      });

      // Total time for analysis: steps * 1s + 2s pause
      const nextSequenceTimeout = setTimeout(() => {
        setSequenceIndex((prev) => (prev + 1) % TERMINAL_SEQUENCES.length);
      }, steps.length * 1000 + 2000);

      return () => {
        timers.forEach(clearTimeout);
        clearTimeout(nextSequenceTimeout);
      };
    } else {
      // Message mode: stay on screen for 5 seconds before fading out
      const nextSequenceTimeout = setTimeout(() => {
        setSequenceIndex((prev) => (prev + 1) % TERMINAL_SEQUENCES.length);
      }, 5500);

      return () => clearTimeout(nextSequenceTimeout);
    }
  }, [sequenceIndex]);

  return (
    <motion.div
      animate={{ y: [0, -6, 0] }}
      transition={{
        duration: 5,
        repeat: Infinity,
        ease: 'easeInOut'
      }}
      className="relative w-full max-w-[400px] aspect-[4/3] rounded-[24px] bg-[#0c0819]/40 border border-white/10 p-5 backdrop-blur-xl shadow-[0_30px_70px_rgba(139,124,248,0.12)] overflow-hidden flex flex-col text-left group"
    >
      {/* Decorative Glow inside the card */}
      <div className="absolute -right-20 -top-20 w-44 h-44 rounded-full bg-accent/15 blur-3xl pointer-events-none group-hover:bg-accent/20 transition-all duration-1000" />
      <div className="absolute -left-20 -bottom-20 w-44 h-44 rounded-full bg-teal/10 blur-3xl pointer-events-none" />

      {/* Terminal Title Bar */}
      <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4 select-none">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose/40 border border-rose/10" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber/40 border border-amber/10" />
          <span className="w-2.5 h-2.5 rounded-full bg-green/40 border border-green/10" />
        </div>
        <span className="text-[10px] font-mono text-text3 tracking-widest uppercase">
          aria core v1.0.4
        </span>
        <span className="w-4 h-4" /> {/* spacer */}
      </div>

      {/* Dynamic Content Window */}
      <div className="flex-1 flex flex-col justify-center relative font-mono text-xs text-text2">
        <AnimatePresence mode="wait">
          {currentSequence.type === 'analysis' ? (
            <motion.div
              key={`seq-${sequenceIndex}`}
              initial={{ opacity: 0, filter: 'blur(4px)' }}
              animate={{ opacity: 1, filter: 'blur(0px)' }}
              exit={{ opacity: 0, filter: 'blur(4px)' }}
              transition={{ duration: 0.6 }}
              className="space-y-3.5"
            >
              {currentSequence.steps?.slice(0, visibleStepCount).map((step, idx) => (
                <div key={idx} className="space-y-1.5">
                  <div className="flex justify-between items-center text-[11px] tracking-wide">
                    <span className={step.success ? 'text-teal font-medium' : 'text-text2'}>
                      {step.success ? '✓' : '✦'} {step.text}
                    </span>
                    <span className="text-[10px] text-text3">{step.progress}%</span>
                  </div>
                  {/* Progress track */}
                  <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${step.progress}%` }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                      className={`h-full rounded-full ${
                        step.success
                          ? 'bg-gradient-to-r from-teal to-accent'
                          : 'bg-gradient-to-r from-accent/50 to-accent'
                      }`}
                    />
                  </div>
                </div>
              ))}
            </motion.div>
          ) : (
            <motion.div
              key={`seq-${sequenceIndex}`}
              initial={{ opacity: 0, filter: 'blur(6px)', scale: 0.96 }}
              animate={{ opacity: 1, filter: 'blur(0px)', scale: 1 }}
              exit={{ opacity: 0, filter: 'blur(6px)', scale: 0.96 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              className="flex items-start gap-4"
            >
              {/* Ethereal realization icon */}
              <div className="w-12 h-12 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center text-xl shrink-0 shadow-lg shadow-accent/5 relative">
                <span className="relative z-10">{currentSequence.icon}</span>
                <span className="absolute inset-0 bg-accent/20 rounded-2xl blur-md animate-pulse" />
              </div>
              
              <div className="flex-1 font-[family-name:var(--font-serif)] text-left py-1">
                {currentSequence.content}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer hint */}
      <div className="border-t border-white/5 pt-3 mt-4 flex items-center justify-between text-[9px] text-text3 font-mono">
        <span>MODE: OBSERVING</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-accent rounded-full animate-ping" />
          <span>CONNECTED</span>
        </span>
      </div>
    </motion.div>
  );
}
