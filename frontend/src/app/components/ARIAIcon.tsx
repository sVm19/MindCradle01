import React from 'react';

interface ARIAIconProps {
  className?: string;
  size?: number;
}

/**
 * ARIAIcon — Cute, welcoming AI Companion Icon component
 * Built on a precision 24x24 grid with customizable size and CSS classes.
 */
export const ARIAIcon: React.FC<ARIAIconProps> = ({ className = '', size = 24 }) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      className={`shrink-0 transition-transform duration-300 ${className}`}
      aria-label="ARIA AI Companion Icon"
      role="img"
    >
      <defs>
        {/* Vibrant Gradient for ARIA's cute body */}
        <linearGradient id="aria-comp-grad" x1="4" y1="3" x2="20" y2="21" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#a899ff" />
          <stop offset="50%" stopColor="#8b7cf8" />
          <stop offset="100%" stopColor="#f093a0" />
        </linearGradient>

        {/* Soft Ambient Shadow */}
        <filter id="aria-comp-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="1.5" stdDeviation="1.5" floodColor="#8b7cf8" floodOpacity="0.4" />
        </filter>
      </defs>

      <g filter="url(#aria-comp-glow)">
        {/* Cute Ear Nubs / Antennae */}
        <path d="M7 6.5 C5.2 3.8 6.5 2 8.5 3.2 L9.5 5.5 Z" fill="url(#aria-comp-grad)" />
        <path d="M17 6.5 C18.8 3.8 17.5 2 15.5 3.2 L14.5 5.5 Z" fill="url(#aria-comp-grad)" />

        {/* Cute Main Character Body */}
        <path d="M12 4.5 C6.8 4.5 4 8.8 4 13.8 C4 18.2 7.6 21 12 21 C16.4 21 20 18.2 20 13.8 C20 8.8 17.2 4.5 12 4.5 Z" fill="url(#aria-comp-grad)" />

        {/* Cute Blush Cheeks */}
        <circle cx="7.2" cy="14.5" r="1.4" fill="#ffffff" opacity="0.4" />
        <circle cx="16.8" cy="14.5" r="1.4" fill="#ffffff" opacity="0.4" />

        {/* Expressive Happy Eyes */}
        <path d="M8 12.2 C8.8 10.8 10.2 10.8 11 12.2" stroke="#05020c" strokeWidth="1.75" strokeLinecap="round" fill="none" />
        <path d="M13 12.2 C13.8 10.8 15.2 10.8 16 12.2" stroke="#05020c" strokeWidth="1.75" strokeLinecap="round" fill="none" />

        {/* Cute Smile */}
        <path d="M11 15 C11.6 15.9 12.4 15.9 13 15" stroke="#05020c" strokeWidth="1.5" strokeLinecap="round" fill="none" />
      </g>
    </svg>
  );
};

export default ARIAIcon;
