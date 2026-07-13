import { BarChart3, Sun, PenTool, MessageSquare, LineChart, ShieldCheck } from 'lucide-react';
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
        title="Features | MindCradle"
        description="Explore the features that make MindCradle a complete wellness app: daily mood logs, guided breathing rituals, reflective journals, and private AI insights."
        schema={featuresSchema}
      />
      {/* Ambient background glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(240,147,160,0.06),transparent_50%)] pointer-events-none" />

      <div className="w-full relative z-10 max-w-4xl mx-auto space-y-8">
        <div className="text-center space-y-3">
          <h1 className="font-[family-name:var(--font-serif)] text-4xl font-light text-text">
            Features
          </h1>
          <p className="text-sm text-text3 max-w-xl mx-auto font-light leading-relaxed">
            Everything you need to track your thoughts, align your energy, and build a consistent routine.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
          <div className="p-6 bg-bg/50 border border-border rounded-xl flex gap-4 items-start">
            <div className="p-3 rounded-lg bg-rose/10 text-rose"><BarChart3 className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">📊 Mood Tracking</h3>
              <p className="text-xs text-text3 leading-relaxed">Log your mood daily and spot patterns over weeks and months.</p>
            </div>
          </div>
          
          <div className="p-6 bg-bg/50 border border-border rounded-xl flex gap-4 items-start">
            <div className="p-3 rounded-lg bg-teal/10 text-teal"><Sun className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">🌅 Daily Rituals</h3>
              <p className="text-xs text-text3 leading-relaxed">3-minute guided practices to build consistency and calm.</p>
            </div>
          </div>
          
          <div className="p-6 bg-bg/50 border border-border rounded-xl flex gap-4 items-start">
            <div className="p-3 rounded-lg bg-indigo-500/10 text-indigo-400"><PenTool className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">📝 Guided Journal</h3>
              <p className="text-xs text-text3 leading-relaxed">Reflective prompts and AI-powered insights on your entries.</p>
            </div>
          </div>
          
          <div className="p-6 bg-bg/50 border border-border rounded-xl flex gap-4 items-start">
            <div className="p-3 rounded-lg bg-amber-500/10 text-amber-400"><MessageSquare className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">🤖 ARIA Companion</h3>
              <p className="text-xs text-text3 leading-relaxed">AI that learns your context and offers personalized support.</p>
            </div>
          </div>
          
          <div className="p-6 bg-bg/50 border border-border rounded-xl flex gap-4 items-start">
            <div className="p-3 rounded-lg bg-green/10 text-green"><LineChart className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">📈 Emotion Analytics</h3>
              <p className="text-xs text-text3 leading-relaxed">Understand your recovery patterns and emotional trends.</p>
            </div>
          </div>
          
          <div className="p-6 bg-bg/50 border border-border rounded-xl flex gap-4 items-start">
            <div className="p-3 rounded-lg bg-rose/10 text-rose"><ShieldCheck className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="font-semibold text-text text-sm sm:text-base">🔐 Privacy First</h3>
              <p className="text-xs text-text3 leading-relaxed">Your data encrypted, GDPR compliant, never sold.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
