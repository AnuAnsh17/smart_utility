'use client';

import React from 'react';
import { Download, Sparkles } from 'lucide-react';

interface DashboardHeaderProps {
  onDownloadReport: () => void;
  onAskAssistant: () => void;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  onDownloadReport,
  onAskAssistant,
}) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
          Your Electricity Insights
        </h1>
        <p className="text-xs md:text-sm text-slate-500 font-normal mt-0.5">
          Here&apos;s what we found from your bill and usage pattern.
        </p>
      </div>

      <div className="flex items-center gap-2.5">
        <button
          type="button"
          onClick={onDownloadReport}
          className="px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200/90 text-slate-700 text-xs font-semibold rounded-full shadow-2xs hover:shadow-xs transition-all cursor-pointer inline-flex items-center gap-1.5"
        >
          <Download className="w-3.5 h-3.5 text-slate-500" />
          Download Report
        </button>

        <button
          type="button"
          onClick={onAskAssistant}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-full shadow-md shadow-emerald-600/20 hover:shadow-lg transition-all cursor-pointer inline-flex items-center gap-1.5"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Ask Assistant
        </button>
      </div>
    </div>
  );
};
