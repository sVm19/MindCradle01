import { Sparkles, Heart, ShieldCheck } from 'lucide-react';
import SEO from '@/app/components/SEO';

export default function About() {
  const aboutSchema = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    "name": "About MindCradle",
    "description": "Learn about MindCradle's mission to empower self-reflection and habit building using a persistent AI memory engine.",
    "publisher": {
      "@type": "Organization",
      "name": "MindCradle",
      "url": "https://mindcradle.online"
    }
  };

  return (
    <div className="bg-bg2 text-text rounded-[28px] border border-border shadow-2xl p-8 sm:p-12 text-left animate-fadeIn relative overflow-hidden">
      <SEO 
        title="About Us | MindCradle"
        description="Discover our mission to empower self-awareness and wellness through daily check-ins, guided rituals, and relational AI companions."
        schema={aboutSchema}
      />
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
          A Sanctuary for Your Rhythm & Self-Awareness
        </p>

        <div className="space-y-8 text-text2">
          <section className="bg-bg/40 border border-border/80 rounded-2xl p-6 mb-6">
            <p className="text-[15px] sm:text-base font-light leading-relaxed">
              MindCradle is a personal growth app designed to help you build calm, self-awareness, and consistency 
              through daily check-ins, reflection journaling, and daily routines. We offer a calming digital space 
              where self-reflection meets habit-building.
            </p>
          </section>

          <section>
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-rose animate-pulse" /> Our Mission
            </h2>
            <p className="text-[15px] sm:text-base font-light">
              Our mission is to empower people to build calm, self-awareness, and consistency through daily routines, 
              reflection, and habit building. We believe personal growth is a gentle, ongoing path rather than a 
              destination, and we walk alongside you with calming audio, grounding prompts, and supportive AI companion features.
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
                  <strong>Daily check-ins:</strong> Record energy levels and routine streaks with a weekly Calm Index.
                </div>
              </li>
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>Guided Morning Routines:</strong> Set daily focuses, check-in with your goals, and choose grounding habits.
                </div>
              </li>
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>Guided Evening Wind Downs:</strong> Clear your mind, list your gratitudes, and select relaxing sleep soundscapes.
                </div>
              </li>
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>Reflection Journaling:</strong> Write with ambient soundscapes like rain or quiet libraries.
                </div>
              </li>
              <li className="p-4 bg-bg/50 border border-border rounded-xl flex items-start gap-3">
                <span className="text-rose font-bold text-lg">•</span>
                <div>
                  <strong>ARIA AI Companion:</strong> Receive warm, validating responses and daily rhythm suggestions.
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
              MindCradle is built with your support in mind. Our AI companion features integrated safety keyword detection, 
              helpful contacts, age verification gates (18+), and off-topic filters to ensure it remains a supportive 
              personal growth space rather than a replacement for professional guidance.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
