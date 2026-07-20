import React from 'react';
import { Sparkles } from 'lucide-react';

interface ARIAIconProps {
  className?: string;
  size?: number;
}

/**
 * ARIAIcon — Official Shadcn UI / Lucide React Icon component
 * Styled with MindCradle's signature theme color accent and glow effect.
 */
export const ARIAIcon: React.FC<ARIAIconProps> = ({ className = '', size = 24 }) => {
  const hasTextColor = /\btext-/.test(className);
  const themeColorClass = hasTextColor
    ? className
    : `text-purple-400 dark:text-purple-300 drop-shadow-[0_0_8px_rgba(168,153,255,0.45)] ${className}`;

  return (
    <Sparkles
      size={size}
      className={`shrink-0 transition-all duration-300 ${themeColorClass}`}
      aria-label="ARIA AI Companion Icon"
    />
  );
};

export default ARIAIcon;


