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

      <div className="w-full relative z-10 max-w-4xl mx-auto space-y-12">
        {/* Hero */}
        <div className="text-center space-y-4">
          <h1 className="font-[family-name:var(--font-serif)] text-4xl sm:text-5xl font-light text-text">
            About MindCradle
          </h1>
          <p className="text-base sm:text-lg text-text3 max-w-2xl mx-auto font-light leading-relaxed">
            Empowering people to understand themselves better through daily wellness practices.
          </p>
        </div>
        
        {/* Mission */}
        <section className="bg-bg/40 border border-border/80 rounded-2xl p-6 sm:p-8">
          <h2 className="text-xl font-bold text-text mb-3 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-rose animate-pulse" /> Our Mission
          </h2>
          <p className="text-text2 font-light leading-relaxed text-sm sm:text-[15px]">
            We believe mental wellness should be accessible, private, and empowering. 
            MindCradle is built to help you discover patterns in your emotions, build 
            sustainable habits, and develop a deeper connection with yourself.
          </p>
        </section>
        
        {/* Values */}
        <section className="space-y-6">
          <h2 className="text-xl font-bold text-text flex items-center gap-2">
            <Heart className="w-5 h-5 text-rose" /> Our Values
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-5 bg-bg/50 border border-border rounded-xl space-y-2">
              <h3 className="font-semibold text-text flex items-center gap-2 text-sm sm:text-base">
                🔒 Privacy First
              </h3>
              <p className="text-xs text-text3 leading-relaxed">
                Your data is yours. End-to-end encrypted. GDPR compliant. Never sold.
              </p>
            </div>
            <div className="p-5 bg-bg/50 border border-border rounded-xl space-y-2">
              <h3 className="font-semibold text-text flex items-center gap-2 text-sm sm:text-base">
                🤝 Authentic
              </h3>
              <p className="text-xs text-text3 leading-relaxed">
                No corporate jargon. Real support. Designed with users, not at them.
              </p>
            </div>
            <div className="p-5 bg-bg/50 border border-border rounded-xl space-y-2">
              <h3 className="font-semibold text-text flex items-center gap-2 text-sm sm:text-base">
                📈 Empowering
              </h3>
              <p className="text-xs text-text3 leading-relaxed">
                Tools for self-discovery. Insights you can act on. Growth you control.
              </p>
            </div>
            <div className="p-5 bg-bg/50 border border-border rounded-xl space-y-2">
              <h3 className="font-semibold text-text flex items-center gap-2 text-sm sm:text-base">
                🌍 Accessible
              </h3>
              <p className="text-xs text-text3 leading-relaxed">
                $0 free tier. No paywall for core features. Mental wellness for everyone.
              </p>
            </div>
          </div>
        </section>
        
        {/* Stats */}
        <section className="bg-bg/60 border border-border/75 rounded-2xl p-8">
          <h2 className="text-xl font-bold text-text text-center mb-6">By The Numbers</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
            <div className="space-y-1">
              <h3 className="text-3xl font-extrabold text-rose">487+</h3>
              <p className="text-xs text-text3">User Reviews</p>
            </div>
            <div className="space-y-1">
              <h3 className="text-3xl font-extrabold text-rose">4.8★</h3>
              <p className="text-xs text-text3">Average Rating</p>
            </div>
            <div className="space-y-1">
              <h3 className="text-3xl font-extrabold text-rose">50K+</h3>
              <p className="text-xs text-text3">Active Users</p>
            </div>
            <div className="space-y-1">
              <h3 className="text-3xl font-extrabold text-rose">150+</h3>
              <p className="text-xs text-text3">Countries</p>
            </div>
          </div>
        </section>
        
        {/* Team */}
        <section className="bg-bg/40 border border-border/80 rounded-2xl p-6">
          <h2 className="text-xl font-bold text-text mb-3">Built By</h2>
          <p className="text-text2 font-light leading-relaxed text-sm">
            Founded by Shubham Kumar, a passionate developer focused on building 
            products that genuinely help people. Built in public, with community feedback.
          </p>
        </section>
        
        {/* CTA */}
        <section className="text-center pt-4 space-y-4">
          <h2 className="text-xl font-bold text-text">Ready to Start Your Wellness Journey?</h2>
          <a 
            href="/signup" 
            className="inline-block px-8 py-3 bg-gradient-to-r from-rose to-accent text-white font-semibold text-sm rounded-full shadow-lg hover:opacity-95 transition-all transform hover:scale-105 smooth-hover-btn animate-pulse"
          >
            Get Started Free
          </a>
        </section>
      </div>
    </div>
  );
}
