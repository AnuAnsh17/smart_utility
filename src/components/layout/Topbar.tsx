'use client';

import React from 'react';
import { Search, MapPin, Sun, Menu } from 'lucide-react';

interface TopbarProps {
  onOpenMobileMenu?: () => void;
  location?: string;
  tempC?: number;
}

export const Topbar: React.FC<TopbarProps> = ({
  onOpenMobileMenu,
  location = 'Mumbai, MH',
  tempC = 28,
}) => {
  return (
    <header className="h-16 border-b border-slate-200/80 bg-white/80 backdrop-blur-md px-4 md:px-8 flex items-center justify-between sticky top-0 z-10 font-sans">
      <div className="flex items-center gap-3 flex-1 max-w-md">
        {onOpenMobileMenu && (
          <button
            onClick={onOpenMobileMenu}
            className="lg:hidden p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-xl cursor-pointer"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Search Bar Input */}
        <div className="relative w-full max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search anything..."
            className="w-full bg-slate-50 border border-slate-200/80 focus:border-emerald-400 focus:bg-white focus:ring-3 focus:ring-emerald-500/10 rounded-full pl-9 pr-4 py-1.5 text-xs font-medium text-slate-800 placeholder:text-slate-400 outline-none transition-all duration-200"
          />
        </div>
      </div>

      {/* Right Utility Status Pills & Avatar */}
      <div className="flex items-center gap-2.5 md:gap-4">
        {/* Location Badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200/80 text-xs font-semibold text-slate-700 shadow-2xs">
          <MapPin className="w-3.5 h-3.5 text-slate-400" />
          <span>{location}</span>
        </div>

        {/* Weather Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-50/70 border border-amber-200/60 text-xs font-bold text-amber-800 shadow-2xs">
          <Sun className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
          <span>{tempC}°C</span>
        </div>

        {/* Profile Avatar */}
        <div className="w-8 h-8 rounded-full bg-slate-900 text-white font-bold text-xs flex items-center justify-center shadow-sm cursor-pointer hover:ring-2 hover:ring-emerald-500/30 transition-all">
          A
        </div>
      </div>
    </header>
  );
};
