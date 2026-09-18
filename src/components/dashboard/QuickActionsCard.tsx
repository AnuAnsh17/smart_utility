'use client';

import React from 'react';
import { Link2, FileText, Calendar, Lightbulb } from 'lucide-react';

interface QuickActionsCardProps {
  onAction: (actionKey: string) => void;
}

export const QuickActionsCard: React.FC<QuickActionsCardProps> = ({ onAction }) => {
  const actions = [
    { key: 'compare', label: 'Compare with last month', icon: Link2 },
    { key: 'details', label: 'View bill details', icon: FileText },
    { key: 'forecast3m', label: 'Forecast next 3 months', icon: Calendar },
    { key: 'savingsTips', label: 'Get saving tips', icon: Lightbulb },
  ];

  return (
    <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex flex-col justify-between h-full font-sans">
      <h3 className="text-base font-extrabold text-slate-900 mb-3">
        Quick Actions
      </h3>

      <div className="grid grid-cols-2 gap-2.5 my-auto">
        {actions.map((act) => {
          const Icon = act.icon;
          return (
            <button
              key={act.key}
              onClick={() => onAction(act.key)}
              className="p-3 rounded-xl border border-blue-100 bg-blue-50/30 hover:bg-blue-50 hover:border-blue-200 text-slate-700 text-[12px] font-semibold text-left transition-all cursor-pointer flex items-center gap-2 group"
            >
              <div className="w-6 h-6 rounded-md bg-white border border-blue-200/70 text-blue-600 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                <Icon className="w-3.5 h-3.5 stroke-[2]" />
              </div>
              <span className="leading-snug">{act.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
