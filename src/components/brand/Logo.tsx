import React from 'react';
import { Leaf } from 'lucide-react';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showTagline?: boolean;
}

export const Logo: React.FC<LogoProps> = ({ size = 'md', showTagline = false }) => {
  const iconSizes = {
    sm: 'w-5 h-5',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  const textSizes = {
    sm: 'text-lg font-bold',
    md: 'text-xl font-bold',
    lg: 'text-2xl font-extrabold',
  };

  return (
    <div className="flex items-center justify-between w-full">
      <div className="flex items-center gap-2.5">
        <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200/60 flex items-center justify-center text-emerald-600 shadow-sm">
          <Leaf className={`${iconSizes[size]} fill-emerald-500/20 stroke-[2.2]`} />
        </div>
        <div className="flex flex-col">
          <span className={`${textSizes[size]} tracking-tight text-slate-900 font-sans`}>
            Urja
          </span>
        </div>
      </div>
      {showTagline && (
        <span className="text-[12px] font-medium text-slate-400 tracking-normal hidden md:inline">
          Smarter homes. Brighter tomorrows.
        </span>
      )}
    </div>
  );
};
