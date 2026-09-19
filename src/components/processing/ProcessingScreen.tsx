'use client';

import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Logo } from '@/components/brand/Logo';
import { FileText, CheckCircle2, Loader2, Circle, Lightbulb } from 'lucide-react';
import { AnalysisPipelineStep, LiveAnalysis } from '@/types/analysis';
import {
  INITIAL_PIPELINE_STEPS,
  analysisService,
  failureMessage,
} from '@/services/analysisService';

interface ProcessingScreenProps {
  /** The document the user actually chose. */
  file: File;
  onComplete: (live: LiveAnalysis) => void;
  onFailed: (message: string) => void;
}

export const ProcessingScreen: React.FC<ProcessingScreenProps> = ({
  file,
  onComplete,
  onFailed,
}) => {
  const [steps, setSteps] = useState<AnalysisPipelineStep[]>(INITIAL_PIPELINE_STEPS);
  const [activeTipIndex, setActiveTipIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('Uploading your bill...');

  // The callbacks are read through refs so the effect can run exactly once for
  // a given file; a parent re-render must not restart the upload.
  const onCompleteRef = useRef(onComplete);
  const onFailedRef = useRef(onFailed);
  onCompleteRef.current = onComplete;
  onFailedRef.current = onFailed;

  const tips = [
    'Weather and appliance usage can significantly impact your electricity bill.',
    'Did you know? Inverter ACs save up to 40% energy compared to non-inverter models.',
    'Air conditioners contribute up to 35-50% of summer electricity costs in Indian households.',
    'Peak grid hours are usually 6 PM to 10 PM. Running heavy loads during off-peak hours improves grid stability.'
  ];

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    analysisService
      .runLiveAnalysis(
        file,
        {
          onStepChange: (next, status) => {
            if (cancelled) return;
            setSteps(next);
            setProgress(status.progress ?? 0);
            if (status.message) setMessage(status.message);
          },
        },
        controller.signal
      )
      .then((live) => {
        if (!cancelled) onCompleteRef.current(live);
      })
      .catch((error) => {
        if (cancelled) return;
        onFailedRef.current(failureMessage(error));
      });

    const tipInterval = setInterval(() => {
      setActiveTipIndex(prev => (prev + 1) % tips.length);
    }, 3200);

    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(tipInterval);
    };
  }, [file]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-slate-50/60 relative overflow-hidden flex flex-col justify-between p-6 md:p-10 font-sans"
    >
      {/* Soft Ambient Background Glow */}
      <div className="absolute top-10 left-1/2 -translate-x-1/2 w-[550px] h-[550px] bg-gradient-to-b from-emerald-100/50 via-teal-50/30 to-transparent rounded-full blur-3xl pointer-events-none" />

      {/* Top Bar Navigation */}
      <header className="w-full max-w-5xl mx-auto z-10 flex items-center justify-between">
        <Logo size="md" />
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200/80 shadow-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Analysing your bill...
        </div>
      </header>

      {/* Center Processing Container */}
      <main className="w-full max-w-lg mx-auto z-10 my-auto text-center py-6">
        {/* Animated Circular Graphic */}
        <div className="relative w-32 h-32 mx-auto mb-6 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-4 border-emerald-100 border-t-emerald-500 animate-spin" />
          <div className="absolute inset-2 rounded-full bg-gradient-to-tr from-emerald-50 via-teal-50 to-white flex items-center justify-center shadow-inner">
            <motion.div
              animate={{ scale: [1, 1.08, 1] }}
              transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
              className="w-14 h-14 rounded-2xl bg-white border border-emerald-200/70 flex items-center justify-center text-emerald-600 shadow-sm"
            >
              <FileText className="w-7 h-7 stroke-[1.8]" />
            </motion.div>
          </div>
        </div>

        {/* Headings */}
        <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight mb-2">
          Analysing your electricity bill...
        </h2>
        <p className="text-xs md:text-sm text-slate-500 max-w-sm mx-auto mb-8">
          {message} Everything runs on this machine; your bill is not uploaded anywhere.
        </p>

        {/* Real progress, reported by the backend job. */}
        <div className="max-w-md mx-auto mb-6">
          <div className="h-1.5 w-full rounded-full bg-slate-200/80 overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-emerald-500"
              animate={{ width: `${Math.round(progress * 100)}%` }}
              transition={{ ease: 'easeOut', duration: 0.3 }}
            />
          </div>
          <div className="mt-1.5 text-[11px] font-semibold text-slate-400 tabular-nums">
            {Math.round(progress * 100)}%
          </div>
        </div>

        {/* Pipeline Checklist */}
        <div className="bg-white/80 border border-slate-200/80 rounded-2xl p-5 md:p-6 text-left shadow-md shadow-slate-900/5 backdrop-blur-md mb-8 max-w-md mx-auto space-y-3.5">
          {steps.map((step) => {
            const isDone = step.status === 'completed';
            const isCurrent = step.status === 'processing';

            return (
              <div key={step.id} className="flex items-center gap-3 transition-colors duration-300">
                <div className="shrink-0">
                  {isDone ? (
                    <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }}>
                      <CheckCircle2 className="w-5 h-5 text-emerald-500 fill-emerald-50" />
                    </motion.div>
                  ) : isCurrent ? (
                    <Loader2 className="w-5 h-5 text-emerald-600 animate-spin" />
                  ) : (
                    <Circle className="w-5 h-5 text-slate-300 stroke-[1.5]" />
                  )}
                </div>
                <span
                  className={`text-xs md:text-sm font-semibold transition-colors duration-200 ${
                    isDone
                      ? 'text-slate-900 font-bold'
                      : isCurrent
                      ? 'text-emerald-700 font-semibold'
                      : 'text-slate-400 font-normal'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Bottom Tip Banner */}
        <motion.div
          key={activeTipIndex}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -5 }}
          className="bg-emerald-50/60 border border-emerald-100 rounded-2xl p-4 flex items-start gap-3 text-left max-w-md mx-auto"
        >
          <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 mt-0.5">
            <Lightbulb className="w-4 h-4 stroke-[2]" />
          </div>
          <div className="text-[12px] text-slate-700 leading-snug">
            <span className="font-bold text-slate-900 block mb-0.5">Did you know?</span>
            {tips[activeTipIndex]}
          </div>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mx-auto text-center z-10 text-[12px] text-slate-400 py-2">
        Local processing only • Document never leaves this device
      </footer>
    </motion.div>
  );
};
