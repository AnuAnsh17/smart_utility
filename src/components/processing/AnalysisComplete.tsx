'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Logo } from '@/components/brand/Logo';
import { FileText, CheckCircle2, Zap, Calendar, IndianRupee, ArrowRight, Info } from 'lucide-react';
import { BillData } from '@/types/bill';
import { AnalysisMeta } from '@/types/analysis';
import { orDash, formatAmount } from '@/lib/format';

interface AnalysisCompleteProps {
  bill: BillData;
  /** Null in demo mode, where nothing was actually parsed. */
  meta?: AnalysisMeta | null;
  onOpenDashboard: () => void;
}

export const AnalysisComplete: React.FC<AnalysisCompleteProps> = ({
  bill,
  meta,
  onOpenDashboard,
}) => {
  const notices = [
    ...(meta?.warnings ?? []),
    ...(meta && meta.missingFields.length > 0
      ? ['Some information could not be extracted.']
      : []),
  ];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-slate-50/60 relative overflow-hidden flex flex-col justify-between p-6 md:p-10 font-sans"
    >
      {/* Background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-gradient-to-tr from-emerald-100/40 via-blue-50/30 to-transparent rounded-full blur-3xl pointer-events-none" />

      {/* Top Bar */}
      <header className="w-full max-w-5xl mx-auto z-10 flex items-center justify-between">
        <Logo size="md" />
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200/80">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          Almost there...
        </div>
      </header>

      {/* Main Card */}
      <main className="w-full max-w-xl mx-auto z-10 my-auto text-center py-6">
        {/* Animated Visual Graphic */}
        <div className="relative w-28 h-28 mx-auto mb-6 flex items-center justify-center">
          <motion.div
            initial={{ scale: 0, rotate: -10 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 20 }}
            className="w-20 h-24 bg-white rounded-2xl border border-slate-200 shadow-xl flex flex-col p-3 relative"
          >
            <div className="w-full h-2 bg-slate-100 rounded mb-2" />
            <div className="w-3/4 h-2 bg-slate-100 rounded mb-2" />
            <div className="w-1/2 h-2 bg-slate-100 rounded" />

            <div className="absolute -bottom-2 -right-2 w-10 h-10 rounded-full bg-emerald-500 text-white flex items-center justify-center shadow-lg ring-4 ring-white">
              <CheckCircle2 className="w-6 h-6 stroke-[2.5]" />
            </div>
          </motion.div>
        </div>

        {/* Headings */}
        <motion.h2
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-2xl md:text-4xl font-extrabold text-slate-900 tracking-tight mb-2"
        >
          Analysis complete!
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-xs md:text-sm text-slate-500 max-w-md mx-auto mb-8 font-normal"
        >
          We&apos;ve successfully analysed your bill and prepared your personalized insights.
        </motion.p>

        {/* Primary CTA */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mb-8"
        >
          <button
            type="button"
            onClick={onOpenDashboard}
            className="px-8 py-3.5 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white text-sm font-semibold rounded-full shadow-lg shadow-emerald-600/25 hover:shadow-xl hover:shadow-emerald-600/35 transition-all duration-200 cursor-pointer inline-flex items-center gap-2.5 group"
          >
            Opening your dashboard...
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
          <p className="text-[12px] text-slate-400 mt-2.5">
            This will only take a moment.
          </p>
        </motion.div>

        {/* 3 Metric Summary Cards */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="grid grid-cols-3 gap-3 md:gap-4 max-w-md mx-auto"
        >
          {/* Card 1: Units Detected */}
          <div className="p-3.5 rounded-2xl bg-white border border-slate-200/80 shadow-sm text-left flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 flex items-center justify-center shrink-0">
              <Zap className="w-4 h-4 stroke-[2.2]" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 leading-tight">
                {bill.unitsConsumed != null
                  ? `${bill.unitsConsumed} ${bill.unitLabel}`
                  : '—'}
              </div>
              <div className="text-[11px] text-slate-400 font-medium">
                Units detected
              </div>
            </div>
          </div>

          {/* Card 2: Billing Period */}
          <div className="p-3.5 rounded-2xl bg-white border border-slate-200/80 shadow-sm text-left flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center shrink-0">
              <Calendar className="w-4 h-4 stroke-[2.2]" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 leading-tight truncate">
                {orDash(bill.billingPeriod)}
              </div>
              <div className="text-[11px] text-slate-400 font-medium">
                Billing period
              </div>
            </div>
          </div>

          {/* Card 3: Total Amount */}
          <div className="p-3.5 rounded-2xl bg-white border border-slate-200/80 shadow-sm text-left flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 border border-amber-100 flex items-center justify-center shrink-0">
              <IndianRupee className="w-4 h-4 stroke-[2.2]" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 leading-tight">
                {formatAmount(bill.currencySymbol, bill.totalAmount)}
              </div>
              <div className="text-[11px] text-slate-400 font-medium">
                Total amount
              </div>
            </div>
          </div>
        </motion.div>

        {/* Anything the backend flagged rather than guessed at. */}
        {notices.length > 0 && (
          <motion.ul
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-6 max-w-md mx-auto text-left space-y-2"
          >
            {notices.map((notice) => (
              <li
                key={notice}
                className="flex items-start gap-2.5 rounded-xl bg-amber-50/70 border border-amber-100 px-3.5 py-2.5"
              >
                <Info className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                <span className="text-[12px] text-amber-900 leading-snug">{notice}</span>
              </li>
            ))}
          </motion.ul>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mx-auto text-center z-10 text-[12px] text-slate-400 py-2">
        {notices.length > 0
          ? 'Bill parsed — review the notes above before relying on these figures'
          : 'Bill OCR parsing completed successfully'}
      </footer>
    </motion.div>
  );
};
