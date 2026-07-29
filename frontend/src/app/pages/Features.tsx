import { BarChart3, Sun, PenTool, MessageSquare, LineChart, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router';
import SEO from '@/app/components/SEO';

export default function Features() {
  const featuresSchema = {
    "@context": "https://schema.org",
    "@type": "ItemPage",
    "name": "MindCradle Features",
    "description": "Explore MindCradle's key capabilities: Mood Tracking, Daily Rituals, Guided Journaling, and AI Insights."
  };

  return (
    <div className="bg-bg2 text-text rounded-[28px] border border-border shadow-2xl p-8 sm:p-12 text-left animate-fadeIn relative overflow-hidden">
      <SEO 
        title="Features - MindCradle"
        description="Mood tracking, daily rituals, journaling, AI companion, and emotion analytics. Everything for wellness."
        schema={featuresSchema}
      />
      {/* Ambient background glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(240,147,160,0.06),transparent_50%)] pointer-events-none" />

      <div className="w-full relative z-10 max-w-4xl mx-auto space-y-8">
        <div className="text-center space-y-3">
          <h1 className="font-[family-name:var(--font-serif)] text-4xl font-light text-text">
            MindCradle Features
          </h1>
          <p className="text-sm text-text3 max-w-xl mx-auto font-light leading-relaxed">
            Everything you need to track your thoughts, align your energy, and build a consistent routine. Our systems combine the latest breakthroughs in generative language modeling with classic cognitive-behavioral principles. Explore the key systems below that work together in complete privacy to help you build self-awareness and maintain emotional resilience.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
          <Link
            to="/mood"
            className="p-6 bg-bg/50 border border-border hover:border-border2 hover:bg-bg/80 rounded-xl flex gap-4 items-start transition-all cursor-pointer text-current decoration-none"
          >
            <div className="p-3 rounded-lg bg-rose/10 text-rose"><BarChart3 className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">Mood Tracking</h3>
              <p className="text-xs text-text3 leading-relaxed">Log your mood, energy levels, and sleep duration daily to map your emotional trajectory. Our intuitive check-in interface takes under 30 seconds, helping you systematically spot trends, isolate environmental stressors, and understand how your recovery metrics correlate with your overall well-being over weeks, months, and seasons.</p>
            </div>
          </Link>
          
          <Link
            to="/morning"
            className="p-6 bg-bg/50 border border-border hover:border-border2 hover:bg-bg/80 rounded-xl flex gap-4 items-start transition-all cursor-pointer text-current decoration-none"
          >
            <div className="p-3 rounded-lg bg-teal/10 text-teal"><Sun className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">Daily Rituals</h3>
              <p className="text-xs text-text3 leading-relaxed">Engage in guided morning intention-setting and ambient evening reflections designed to anchor your mind. Complete brief, science-backed 3-minute exercises to regulate your nervous system, build consistency, and cultivate mindful habits that build emotional resilience and lower cognitive overwhelm.</p>
            </div>
          </Link>
          
          <Link
            to="/journal"
            className="p-6 bg-bg/50 border border-border hover:border-border2 hover:bg-bg/80 rounded-xl flex gap-4 items-start transition-all cursor-pointer text-current decoration-none"
          >
            <div className="p-3 rounded-lg bg-indigo-500/10 text-indigo-400"><PenTool className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">Guided Journal</h3>
              <p className="text-xs text-text3 leading-relaxed">Express your thoughts with structured prompts that guide your reflections. Search past entries naturally using semantic hybrid vector search, and receive secure, personalized insights that help you understand the themes of your thoughts, your personal breakthroughs, and your progress.</p>
            </div>
          </Link>
          
          <Link
            to="/aria"
            className="p-6 bg-bg/50 border border-border hover:border-border2 hover:bg-bg/80 rounded-xl flex gap-4 items-start transition-all cursor-pointer text-current decoration-none"
          >
            <div className="p-3 rounded-lg bg-amber-500/10 text-amber-400"><MessageSquare className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">ARIA Companion</h3>
              <p className="text-xs text-text3 leading-relaxed">Meet ARIA, a supportive AI companion with longitudinal relational memory. Operating via our secure Memory Protocol, ARIA remembers your history, recognizes recurring stress cycles, and provides validating, personalized guidance tailored to your specific growth journey.</p>
            </div>
          </Link>
          
          <Link
            to="/insights"
            className="p-6 bg-bg/50 border border-border hover:border-border2 hover:bg-bg/80 rounded-xl flex gap-4 items-start transition-all cursor-pointer text-current decoration-none"
          >
            <div className="p-3 rounded-lg bg-green/10 text-green"><LineChart className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">Emotion Analytics</h3>
              <p className="text-xs text-text3 leading-relaxed">Visualize your recovery patterns, energy peaks, and emotional triggers with detailed dashboard charts. Our Compounding Intelligence Engine identifies themes in your logs, giving you actionable analytics to understand your stress limits and prevent burnout before it starts.</p>
            </div>
          </Link>
          
          <Link
            to="/privacy"
            className="p-6 bg-bg/50 border border-border hover:border-border2 hover:bg-bg/80 rounded-xl flex gap-4 items-start transition-all cursor-pointer text-current decoration-none"
          >
            <div className="p-3 rounded-lg bg-rose/10 text-rose"><ShieldCheck className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">Privacy First</h3>
              <p className="text-xs text-text3 leading-relaxed">Your personal growth and private thoughts are protected with end-to-end encryption in transit and at rest. We adhere to strict GDPR standards, run on fully segregated database schemas, and guarantee that your personal entries will never be sold or used to train public LLM models.</p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
