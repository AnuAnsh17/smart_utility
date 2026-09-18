'use client';

import React from 'react';
import { Recommendation } from '@/types/insight';
import { Leaf, ShieldCheck, Clock, Zap, ChevronRight } from 'lucide-react';

interface TopRecommendationsCardProps {
  recommendations: Recommendation[];
  onViewAll?: () => void;
}

export const TopRecommendationsCard: React.FC<TopRecommendationsCardProps> = ({
  recommendations,
  onViewAll,
}) => {
  const getIcon = (iconName: Recommendation['iconName']) => {
    switch (iconName) {
      case 'leaf':
        return Leaf;
      case 'shield':
        return ShieldCheck;
      case 'clock':
        return Clock;
      default:
        return Zap;
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex flex-col justify-between h-full font-sans">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-extrabold text-slate-900">
          Top Recommendations
        </h3>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-0.5 cursor-pointer"
          >
            View All
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      <div className="space-y-3 my-auto">
        {recommendations.map((rec) => {
          const Icon = getIcon(rec.iconName);
          return (
            <div
              key={rec.id}
              className="flex items-start gap-3 p-2.5 rounded-xl border border-emerald-100/70 bg-emerald-50/30 hover:bg-emerald-50/80 transition-colors"
            >
              <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 border border-emerald-200/60 flex items-center justify-center shrink-0 mt-0.5">
                <Icon className="w-3.5 h-3.5 stroke-[2.2]" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-900 leading-snug">
                  {rec.title}
                </p>
                <p className="text-[11px] text-slate-500 font-normal mt-0.5">
                  {rec.suggestedAction}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
