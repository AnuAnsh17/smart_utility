'use client';

import React from 'react';
import { Sun, Thermometer, ShieldAlert, Sparkles } from 'lucide-react';
import { WeatherData } from '@/types/weather';

interface WeatherImpactCardProps {
  weather: WeatherData;
}

export const WeatherImpactCard: React.FC<WeatherImpactCardProps> = ({ weather }) => {
  return (
    <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex flex-col justify-between h-full font-sans">
      <h3 className="text-base font-extrabold text-slate-900 mb-3">
        Weather Impact
      </h3>

      <div className="space-y-3 my-auto">
        {/* Row 1: Current Temp */}
        <div className="flex items-center gap-3 p-2 rounded-xl bg-amber-50/60 border border-amber-100">
          <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center shrink-0">
            <Sun className="w-4 h-4 fill-amber-400 stroke-[2]" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-900">
              {weather.tempC}°C
            </div>
            <div className="text-[11px] text-slate-500 font-medium">
              Current Temperature
            </div>
          </div>
        </div>

        {/* Row 2: Condition */}
        <div className="flex items-center gap-3 p-2 rounded-xl bg-orange-50/50 border border-orange-100">
          <div className="w-8 h-8 rounded-lg bg-orange-100 text-orange-600 flex items-center justify-center shrink-0">
            <Thermometer className="w-4 h-4 stroke-[2]" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-900">
              {weather.condition}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">
              Conditions ({weather.humidityPercent}% humidity)
            </div>
          </div>
        </div>

        {/* Row 3: Impact Summary */}
        <div className="flex items-center gap-3 p-2 rounded-xl bg-emerald-50/60 border border-emerald-100">
          <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4 stroke-[2]" />
          </div>
          <div>
            <div className="text-xs font-bold text-emerald-800">
              {weather.impactSummary}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">
              {weather.detailNote}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
