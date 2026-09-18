'use client';

import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Logo } from '@/components/brand/Logo';
import { Sparkles, Loader2 } from 'lucide-react';

interface PreparingSampleScreenProps {
  onComplete: () => void;
}

export const PreparingSampleScreen: React.FC<PreparingSampleScreenProps> = ({ onComplete }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onComplete();
    }, 1000);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-slate-50/70 relative overflow-hidden flex flex-col justify-between p-6 md:p-10 font-sans"
    >
      {/* Background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-gradient-to-tr from-emerald-100/50 via-teal-50/30 to-transparent rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <header className="w-full max-w-5xl mx-auto z-10">
        <Logo size="md" />
      </header>

      {/* Content */}
      <main className="w-full max-w-md mx-auto z-10 my-auto text-center py-8">
        <div className="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-600 mx-auto mb-6 shadow-sm">
          <Sparkles className="w-8 h-8 animate-pulse stroke-[1.8]" />
        </div>

        <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight mb-2">
          Preparing sample analysis...
        </h2>
        <p className="text-xs text-slate-500 max-w-xs mx-auto mb-6">
          Loading synthetic bill metrics, consumption trends, and AI recommendations.
        </p>

        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-2xs text-xs font-semibold text-slate-700">
          <Loader2 className="w-4 h-4 text-emerald-600 animate-spin" />
          Loading dashboard dataset...
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mx-auto text-center z-10 text-[12px] text-slate-400 py-2">
        Demo Mode • Smart Utility AI
      </footer>
    </motion.div>
  );
};
