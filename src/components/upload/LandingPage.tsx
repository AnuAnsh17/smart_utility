'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Logo } from '@/components/brand/Logo';
import { UploadZone } from './UploadZone';
import { FeatureBadges } from './FeatureBadges';
import { UploadedBillFile } from '@/types/bill';

interface LandingPageProps {
  onFileSelect: (file: UploadedBillFile) => void;
  onUseSample: () => void;
  onStartAnalysis: () => void;
  selectedFile: UploadedBillFile | null;
  onClearFile: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onFileSelect,
  onUseSample,
  onStartAnalysis,
  selectedFile,
  onClearFile,
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
      <header className="w-full max-w-6xl mx-auto z-10">
        <Logo size="md" showTagline={true} />
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
