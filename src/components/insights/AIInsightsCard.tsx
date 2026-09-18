'use client';

import React from 'react';
import { InsightItem } from '@/types/insight';
import { Zap, ShieldCheck, Droplet, Sparkles, AlertTriangle, TrendingUp, ChevronRight } from 'lucide-react';

interface AIInsightsCardProps {
  insights: InsightItem[];
  onViewAll?: () => void;
}

export const AIInsightsCard: React.FC<AIInsightsCardProps> = ({ insights, onViewAll }) => {
  const getIconAndColors = (type: InsightItem['type'], iconName: InsightItem['iconName']) => {
    switch (type) {
      case 'warning':
        return {
          bg: 'bg-amber-50 text-amber-600 border-amber-200/80',
          Icon: Zap,
        };
      case 'positive':
        return {
          bg: 'bg-emerald-50 text-emerald-600 border-emerald-200/80',
          Icon: ShieldCheck,
        };
      case 'neutral':
        return {
          bg: 'bg-teal-50 text-teal-600 border-teal-200/80',
          Icon: Droplet,
        };
      case 'info':
        return {
          bg: 'bg-purple-50 text-purple-600 border-purple-200/80',
          Icon: Sparkles,
        };
      default:
        return {
          bg: 'bg-slate-50 text-slate-600 border-slate-200',
          Icon: TrendingUp,
        };
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex flex-col justify-between h-full font-sans">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-extrabold text-slate-900">
          AI Insights
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
        {insights.map((item) => {
          const { bg, Icon } = getIconAndColors(item.type, item.iconName);
          return (
            <div key={item.id} className="flex items-start gap-3 p-2.5 rounded-xl hover:bg-slate-50/80 transition-colors">
              <div className={`w-7 h-7 rounded-lg ${bg} border flex items-center justify-center shrink-0 mt-0.5`}>
                <Icon className="w-3.5 h-3.5 stroke-[2.2]" />
              </div>
              <p className="text-xs font-semibold text-slate-700 leading-snug">
                {item.text}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
