import React from 'react';

interface LogoProps extends React.SVGProps<SVGSVGElement> {
  showText?: boolean;
}

export default function Logo({ showText = true, className, ...props }: LogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={showText ? "0 0 320 80" : "0 0 80 80"}
      width="100%"
      height="100%"
      className={className}
      {...props}
    >
      <defs>
        <style>
          {`
            .mc-icon-shape {
              stroke: #E94B6F;
              stroke-width: 5.5px;
              fill: none;
              stroke-linejoin: round;
              stroke-linecap: round;
            }
            .mc-logo-text {
              font-family: 'Caveat', 'Brush Script MT', cursive, sans-serif;
              font-size: 46px;
              font-weight: 700;
              fill: currentColor;
            }
          `}
        </style>
      </defs>
      
      {/* Icon Area: 60x60 container centered vertically (y: 10 to 70), center of icon is (40, 40) */}
      <g id="logo-icon">
        {/* Large Corner Shape */}
        <path className="mc-icon-shape" d="M 23,37 L 23,17 L 63,17 L 63,57 L 43,57 L 43,37 Z" />
        
        {/* Small Nestled Square */}
        <rect className="mc-icon-shape" x="17" y="43" width="20" height="20" rx="2" />
      </g>
      
      {showText && (
        <text className="mc-logo-text" x="86" y="54">MindCradle</text>
      )}
    </svg>
  );
}
