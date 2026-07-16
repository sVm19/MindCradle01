import { BookOpen, ExternalLink } from 'lucide-react';
import SEO from '@/app/components/SEO';

export default function Resources() {
  return (
    <div className="bg-bg2 text-text rounded-[28px] border border-border shadow-2xl p-8 sm:p-12 text-left animate-fadeIn relative overflow-hidden">
      <SEO 
        title="Resources & Articles - MindCradle"
        description="Read articles about AI conversation memory limitations, context preservation, and the technology behind ARIA companion."
      />
      
      {/* Ambient background glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(139,124,248,0.06),transparent_50%)] pointer-events-none" />

      <div className="w-full relative z-10 max-w-3xl mx-auto space-y-8">
        <div className="text-center space-y-3">
          <h1 className="font-[family-name:var(--font-serif)] text-4xl font-light text-text flex items-center justify-center gap-2.5">
            <BookOpen className="w-8 h-8 text-accent animate-pulse" /> Read Our Articles
          </h1>
          <p className="text-sm text-text3 max-w-xl mx-auto font-light leading-relaxed">
            Exploring the challenges of AI memory, contextual learning, and longitudinal companion design.
          </p>
        </div>

        <div className="space-y-4 pt-4">
          <a 
            href="https://medium.com/@imshubham7004/why-every-ai-conversation-starts-from-zero-and-why-thats-broken-7bb8bd14d65b" 
            target="_blank" 
            rel="noopener noreferrer"
            className="block p-6 bg-bg/50 border border-border hover:border-border2 hover:bg-bg/85 rounded-2xl transition-all cursor-pointer group"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="space-y-2">
                <h3 className="font-semibold text-text text-lg group-hover:text-accent transition-colors flex items-center gap-2">
                  Why Every AI Conversation Starts From Zero
                </h3>
                <p className="text-xs sm:text-sm text-text3 leading-relaxed">
                  Exploring AI memory limitations, state preservation challenges, and why context matters in relational systems.
                </p>
              </div>
              <ExternalLink className="w-4 h-4 text-text3 group-hover:text-accent transition-colors flex-shrink-0 mt-1" />
            </div>
          </a>

          <a 
            href="https://medium.com/@imshubham7004/your-ai-has-a-memory-problem-heres-why-that-matters-1f69802b2aea" 
            target="_blank" 
            rel="noopener noreferrer"
            className="block p-6 bg-bg/50 border border-border hover:border-border2 hover:bg-bg/85 rounded-2xl transition-all cursor-pointer group"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="space-y-2">
                <h3 className="font-semibold text-text text-lg group-hover:text-accent transition-colors flex items-center gap-2">
                  Your AI Has a Memory Problem
                </h3>
                <p className="text-xs sm:text-sm text-text3 leading-relaxed">
                  How we solved conversation context limits in ARIA using compounding structured memory engines.
                </p>
              </div>
              <ExternalLink className="w-4 h-4 text-text3 group-hover:text-accent transition-colors flex-shrink-0 mt-1" />
            </div>
          </a>

          <a 
            href="https://medium.com/@imshubham7004/the-missing-layer-between-chatbots-and-human-intelligence-22cdc54b1fcd" 
            target="_blank" 
            rel="noopener noreferrer"
            className="block p-6 bg-bg/50 border border-border hover:border-border2 hover:bg-bg/85 rounded-2xl transition-all cursor-pointer group"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="space-y-2">
                <h3 className="font-semibold text-text text-lg group-hover:text-accent transition-colors flex items-center gap-2">
                  The Missing Layer Between Chatbots and Human Intelligence
                </h3>
                <p className="text-xs sm:text-sm text-text3 leading-relaxed">
                  Bridging the gap between raw generative outputs and compounding personal human intelligence.
                </p>
              </div>
              <ExternalLink className="w-4 h-4 text-text3 group-hover:text-accent transition-colors flex-shrink-0 mt-1" />
            </div>
          </a>
        </div>
      </div>
    </div>
  );
}
