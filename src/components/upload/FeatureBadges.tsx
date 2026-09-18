import React from 'react';
import { FileText, Sparkles, TrendingUp, Lightbulb } from 'lucide-react';

const FEATURES = [
  {
    icon: FileText,
    label: 'Multi-format support',
    bg: 'bg-emerald-50 text-emerald-600 border-emerald-100',
  },
  {
    icon: Sparkles,
    label: 'AI-powered analysis',
    bg: 'bg-blue-50 text-blue-600 border-blue-100',
  },
  {
    icon: TrendingUp,
    label: 'Consumption forecasting',
    bg: 'bg-emerald-50 text-emerald-600 border-emerald-100',
  },
  {
    icon: Lightbulb,
    label: 'Personalized savings tips',
    bg: 'bg-amber-50 text-amber-600 border-amber-100',
  },
];

export const FeatureBadges: React.FC = () => {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 md:gap-6 max-w-3xl mx-auto mt-12 md:mt-16">
      {FEATURES.map((feat, i) => {
        const Icon = feat.icon;
        return (
          <div
            key={i}
            className="flex flex-col items-center text-center p-3 sm:p-4 rounded-2xl bg-white/60 border border-slate-100 shadow-sm hover:shadow-md hover:bg-white transition-all duration-200"
          >
            <div className={`w-10 h-10 rounded-xl ${feat.bg} border flex items-center justify-center mb-2.5`}>
              <Icon className="w-5 h-5 stroke-[2]" />
            </div>
            <span className="text-[13px] font-semibold text-slate-700 leading-tight">
              {feat.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};
