'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Logo } from '@/components/brand/Logo';
import { UploadZone } from './UploadZone';
import { FeatureBadges } from './FeatureBadges';
import { UploadedBillFile } from '@/types/bill';
import { ArrowRight, Sparkles } from 'lucide-react';

interface LandingPageProps {
  onFileSelect: (file: UploadedBillFile) => void;
  onUseSample: () => void;
  onStartAnalysis: () => void;
  selectedFile: UploadedBillFile | null;
  onClearFile: () => void;
  isDemoMode: boolean;
  onToggleDemoMode: (enabled: boolean) => void;
  onExploreSampleDashboard: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onFileSelect,
  onUseSample,
  onStartAnalysis,
  selectedFile,
  onClearFile,
  isDemoMode,
  onToggleDemoMode,
  onExploreSampleDashboard,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-slate-50/60 relative overflow-hidden flex flex-col justify-between p-6 md:p-10 font-sans"
    >
      {/* Background ambient lighting */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-br from-emerald-100/40 via-teal-50/20 to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 left-10 w-[400px] h-[400px] bg-gradient-to-tr from-emerald-50/50 via-blue-50/30 to-transparent rounded-full blur-3xl pointer-events-none" />

      {/* Top Header Navigation */}
      <header className="w-full max-w-6xl mx-auto z-10 flex items-center justify-between">
        <Logo size="md" showTagline={true} />

        {/* Top-Right Demo Mode Switch */}
        <div className="flex flex-col items-end gap-1">
          <label className="inline-flex items-center gap-2 cursor-pointer select-none">
            <span className="text-xs font-semibold text-slate-600">Demo</span>
            <button
              type="button"
              role="switch"
              aria-checked={isDemoMode}
              onClick={() => onToggleDemoMode(!isDemoMode)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                isDemoMode ? 'bg-emerald-600' : 'bg-slate-300'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                  isDemoMode ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </label>
          {isDemoMode && (
            <motion.span
              initial={{ opacity: 0, y: -2 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200/60"
            >
              Explore the dashboard with sample data
            </motion.span>
          )}
        </div>
      </header>

      {/* Main Content Hero Section */}
      <main className="w-full max-w-4xl mx-auto z-10 my-auto py-8">
        <div className="text-center mb-8 md:mb-10">
          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-3xl md:text-5xl font-extrabold text-slate-900 tracking-tight leading-[1.15]"
          >
            Understand your <br className="hidden sm:inline" />
            electricity better.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-sm md:text-base text-slate-500 max-w-xl mx-auto mt-3 font-normal"
          >
            Upload your electricity bill and get AI-powered insights, forecasts and personalized recommendations.
          </motion.p>
        </div>

        {/* Upload Card Dropzone */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <UploadZone
            onFileSelect={onFileSelect}
            onUseSample={onUseSample}
            onStartAnalysis={onStartAnalysis}
            selectedFile={selectedFile}
            onClearFile={onClearFile}
          />

          {/* Secondary Demo Mode CTA if Demo Mode is ON */}
          <AnimatePresence>
            {isDemoMode && (
              <motion.div
                initial={{ opacity: 0, y: 10, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -5, height: 0 }}
                className="mt-4 text-center"
              >
                <button
                  type="button"
                  onClick={onExploreSampleDashboard}
                  className="px-5 py-2.5 rounded-full border border-emerald-300 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-bold shadow-xs hover:shadow-md transition-all duration-200 cursor-pointer inline-flex items-center gap-2 group"
                >
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  Explore sample dashboard
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Feature Badges */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <FeatureBadges />
        </motion.div>
      </main>

      {/* Subtle Footer */}
      <footer className="w-full max-w-6xl mx-auto text-center z-10 text-[12px] text-slate-400 py-2">
        Smart Utility AI Platform • Confidential Prototype • Privacy Preserving
      </footer>
    </motion.div>
  );
};
