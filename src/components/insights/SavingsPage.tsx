'use client';

import React from 'react';
import { Recommendation } from '@/types/insight';
import { PiggyBank, Leaf, ShieldCheck, Clock, Zap, ArrowRight } from 'lucide-react';

interface SavingsPageProps {
  recommendations: Recommendation[];
}

export const SavingsPage: React.FC<SavingsPageProps> = ({ recommendations }) => {
  return (
    <div className="space-y-6 font-sans">
      {/* Header Banner */}
      <div className="p-6 md:p-8 rounded-3xl bg-gradient-to-br from-emerald-600 via-teal-700 to-slate-900 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 text-white text-xs font-semibold mb-3 border border-white/20">
            <PiggyBank className="w-3.5 h-3.5" />
            Actionable Savings Engine
          </div>
          <h2 className="text-2xl md:text-4xl font-extrabold tracking-tight">
            Personalized Savings Plan
          </h2>
          <p className="text-xs md:text-sm text-emerald-100 max-w-xl mt-1">
            Based on your Oct 2024 consumption breakdown (352 kWh), targeting your top energy drivers can reduce your annual bill significantly.
          </p>
        </div>
      </div>

      {/* Recommendation Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {recommendations.map((rec) => (
          <div
            key={rec.id}
            className="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200/60">
                  {rec.impactLevel} Impact
                </span>
                <span className="text-xs font-bold text-emerald-600 bg-emerald-100/50 px-2.5 py-0.5 rounded-md">
                  {rec.potentialImpact}
                </span>
              </div>

              <h3 className="text-lg font-extrabold text-slate-900 mb-2">
                {rec.title}
              </h3>

              <div className="space-y-2.5 my-4">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Suggested Action
                  </div>
                  <div className="text-xs font-semibold text-slate-800 mt-0.5">
                    {rec.suggestedAction}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Why It Matters
                  </div>
                  <div className="text-xs font-medium text-slate-600 mt-0.5">
                    {rec.whyItMatters}
                  </div>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => alert(`Saving guide initiated for: ${rec.title}`)}
              className="w-full py-2.5 rounded-xl border border-emerald-200 bg-emerald-50/60 hover:bg-emerald-100 text-emerald-800 text-xs font-bold transition-colors cursor-pointer inline-flex items-center justify-center gap-1.5"
            >
              Apply Saving Tip
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
