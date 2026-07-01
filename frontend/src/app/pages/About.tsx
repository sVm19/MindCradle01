import { Sparkles, Heart, ShieldCheck } from 'lucide-react';

export default function About() {
  return (
    <div className="bg-bg2 text-text rounded-[28px] border border-border shadow-2xl p-8 sm:p-12 text-left animate-fadeIn relative overflow-hidden">
      {/* Ambient background glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(240,147,160,0.06),transparent_50%)] pointer-events-none" />

      <div 
        className="w-full relative z-10"
        style={{ 
          marginLeft: 'auto',
          marginRight: 'auto',
          maxWidth: '800px',
          fontSize: '16px',
          lineHeight: '1.8'
        }}
      >
        <h1 className="font-[family-name:var(--font-serif)] text-3xl sm:text-4xl font-light mb-2 text-text flex items-center gap-2">
          About MindCradle
        </h1>
        <p className="text-sm text-text3 mb-8 font-light">
          A Sanctuary for Your Mind & Heart
        </p>

        <div className="space-y-8 text-text2">
          <section className="bg-bg/40 border border-border/80 rounded-2xl p-6 mb-6">
            <p className="text-[15px] sm:text-base font-light leading-relaxed">
              MindCradle is a personal wellness app designed to help you understand your emotional 
              health through mood tracking, journaling, and daily rituals. We offer a calming digital sanctuary 
              where self-discovery meets habit-building.
            </p>
          </section>

          <section>
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-rose animate-pulse" /> Our Mission
            </h2>
            <p className="text-[15px] sm:text-base font-light">
              Our mission is to empower people to take control of their mental wellness through self-discovery, 
              habit building, and meaningful reflection. We believe wellness is a gentle, ongoing path rather than a 
              destination, and we walk alongside you with calming audio, validating prompts, and compassionate AI support.
            </p>
          </section>

          <section>
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6 flex items-center gap-2">
              <Heart className="w-5 h-5 text-rose" /> Features Built For You
            </h2>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-[14px]">
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>Daily mood tracking:</strong> Record mood shifts and check-in streaks with a weekly Calm Score.
                </div>
              </li>
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>Guided Morning Rituals:</strong> Set daily intentions, check-in with your body, and stretch.
                </div>
              </li>
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>Guided Evening Wind Downs:</strong> Let go of stressful items and reflect with gratitude timers.
                </div>
              </li>
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>Reflective Journaling:</strong> Write with ambient backing sounds like rain or ocean waves.
                </div>
              </li>
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>ARIA AI Companion:</strong> Receive warm, validating responses and structural insights.
                </div>
              </li>
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>Privacy-First Focus:</strong> Full GDPR support, easy data exports, and secure database architecture.
                </div>
              </li>
            </ul>
          </section>

          <section className="border-t border-border pt-6 mt-8">
            <h2 className="text-[20px] font-bold text-text mb-3 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-rose" /> Guardrails & Safety
            </h2>
            <p className="text-[14px] text-text3 leading-relaxed">
              MindCradle is built with safety in mind. Our AI companion features integrated crisis keyword detection, 
              safety handover links, age verification gates (18+), and off-topic filters to ensure it remains a helpful 
              mental wellness space rather than a replacement for clinical therapy.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
