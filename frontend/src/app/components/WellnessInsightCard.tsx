import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { 
  BookOpen, 
  Heart, 
  Moon, 
  Activity, 
  Users, 
  Clock, 
  Droplet, 
  Palette, 
  Leaf, 
  Wind, 
  Sparkles, 
  ArrowRight 
} from 'lucide-react';

const INSIGHTS = [
  {
    icon: BookOpen,
    iconColor: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
    text: "Journaling three times a week builds 40% greater mental clarity",
    cta: "Start reflection journal",
    path: "/journal"
  },
  {
    icon: Heart,
    iconColor: "text-rose-400 bg-rose-500/10 border-rose-500/20",
    text: "Taking a 5-minute pause daily increases self-awareness and focus",
    cta: "Try a morning pause",
    path: "/morning"
  },
  {
    icon: Moon,
    iconColor: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    text: "Consistent sleep schedules improve daily rhythm and balance by 35%",
    cta: "Log evening routine",
    path: "/wind-down"
  },
  {
    icon: Activity,
    iconColor: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    text: "A 15-minute walk boosts focus, energy, and overall clarity",
    cta: "Start morning walk",
    path: "/morning"
  },
  {
    icon: Users,
    iconColor: "text-teal-400 bg-teal-500/10 border-teal-500/20",
    text: "Reflecting on your interactions helps build connection and balance",
    cta: "Chat with ARIA",
    path: "/aria"
  },
  {
    icon: Clock,
    iconColor: "text-accent bg-accent-glow border-accent/20",
    text: "Morning routines increase productivity and focus by 50%",
    cta: "Start morning routine",
    path: "/morning"
  },
  {
    icon: Droplet,
    iconColor: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    text: "Staying hydrated increases energy levels and focus by 15%",
    cta: "Drink water",
    path: "/morning"
  },
  {
    icon: Palette,
    iconColor: "text-pink-400 bg-pink-500/10 border-pink-500/20",
    text: "Expressive art or creative writing for 45 minutes builds calm and focus",
    cta: "Be creative",
    path: "/journal"
  },
  {
    icon: Leaf,
    iconColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    text: "Spending 20 minutes in nature significantly raises calmness and awareness",
    cta: "Spend time outside",
    path: "/morning"
  },
  {
    icon: Wind,
    iconColor: "text-sky-400 bg-sky-500/10 border-sky-500/20",
    text: "Deep breathing exercises for 2 minutes help lower heart rate and restore calm",
    cta: "Start breathwork",
    path: "/morning"
  }
];

export const WellnessInsightCard = () => {
  const [insight, setInsight] = useState(INSIGHTS[0]);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Get today's date as seed for consistent daily rotation
    const today = new Date();
    const dayOfYear = Math.floor(
      (today.getTime() - new Date(today.getFullYear(), 0, 0).getTime()) / 86400000
    );
    const index = dayOfYear % INSIGHTS.length;
    setInsight(INSIGHTS[index]);
    
    // Fade in animation
    const timer = setTimeout(() => setVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  const IconComponent = insight.icon;

  return (
    <div 
      className={`border border-border/80 rounded-[20px] p-6 relative overflow-hidden bg-bg2 backdrop-blur-md shadow-xl transition-all duration-500 ease-out transform ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
      }`}
    >
      {/* Ambient glow in background */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(240,147,160,0.06),transparent_50%)] pointer-events-none" />

      {/* Header with icon */}
      <div className="flex items-center gap-3.5 mb-4 select-none relative z-10">
        <div className={`w-10 h-10 rounded-xl border flex items-center justify-center flex-shrink-0 ${insight.iconColor}`}>
          <IconComponent className="w-5 h-5" />
        </div>
        <h3 className="font-[family-name:var(--font-serif)] text-[13px] tracking-[0.14em] uppercase text-rose font-medium flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          Daily Rhythm Insight
        </h3>
      </div>
      
      {/* Insight text */}
      <p className="font-[family-name:var(--font-serif)] text-[15px] sm:text-base font-light text-text2 leading-relaxed italic my-4 relative z-10">
        "{insight.text}"
      </p>
      
      {/* CTA Link Button */}
      <Link 
        to={insight.path}
        className="inline-flex items-center justify-center gap-2 h-[46px] px-6 bg-rose-dim hover:bg-rose/25 text-rose border border-rose/30 hover:border-rose/50 rounded-full text-xs font-semibold tracking-wider transition-all cursor-pointer relative z-10 no-underline"
      >
        {insight.cta} <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  );
};
