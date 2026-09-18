'use client';

import React from 'react';
import { FileText, Zap, BarChart2, ArrowDown } from 'lucide-react';
import { BillData } from '@/types/bill';
import { ForecastData } from '@/types/forecast';

interface TopMetricCardsProps {
  bill: BillData;
  forecast: ForecastData;
}

export const TopMetricCards: React.FC<TopMetricCardsProps> = ({ bill, forecast }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* Card 1: Last Month's Bill */}
      <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs hover:shadow-md transition-shadow flex items-start justify-between">
        <div className="flex items-start gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 flex items-center justify-center shrink-0 mt-0.5">
            <FileText className="w-5 h-5 stroke-[2]" />
          </div>
          <div>
            <div className="text-[12px] font-semibold text-slate-400 uppercase tracking-wide">
              Last Month&apos;s Bill
            </div>
            <div className="text-2xl font-extrabold text-slate-900 tracking-tight mt-1">
              {bill.currencySymbol}{bill.totalAmount.toLocaleString('en-IN')}
            </div>
            <div className="text-[12px] text-slate-400 font-medium mt-0.5">
              {bill.billingPeriod}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200/60">
          <ArrowDown className="w-3.5 h-3.5 stroke-[2.5]" />
          <span>12%</span>
          <span className="hidden xl:inline text-[10px] text-emerald-600/80 font-normal ml-0.5">
            vs prev
          </span>
        </div>
      </div>

      {/* Card 2: Units Consumed */}
      <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs hover:shadow-md transition-shadow flex items-start justify-between">
        <div className="flex items-start gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center shrink-0 mt-0.5">
            <Zap className="w-5 h-5 stroke-[2]" />
          </div>
          <div>
            <div className="text-[12px] font-semibold text-slate-400 uppercase tracking-wide">
              Units Consumed
            </div>
            <div className="text-2xl font-extrabold text-slate-900 tracking-tight mt-1">
              {bill.unitsConsumed} {bill.unitLabel}
            </div>
            <div className="text-[12px] text-slate-400 font-medium mt-0.5">
              ↓ 5%
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200/60">
          <ArrowDown className="w-3.5 h-3.5 stroke-[2.5]" />
          <span>5%</span>
          <span className="hidden xl:inline text-[10px] text-emerald-600/80 font-normal ml-0.5">
            vs prev
          </span>
        </div>
      </div>

      {/* Card 3: Next Month Forecast */}
      <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs hover:shadow-md transition-shadow flex items-start justify-between">
        <div className="flex items-start gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center shrink-0 mt-0.5">
            <BarChart2 className="w-5 h-5 stroke-[2]" />
          </div>
          <div>
            <div className="text-[12px] font-semibold text-slate-400 uppercase tracking-wide">
              Next Month Forecast
            </div>
            <div className="text-xl lg:text-2xl font-extrabold text-slate-900 tracking-tight mt-1">
              ₹{forecast.expectedAmountMin.toLocaleString('en-IN')} – ₹{forecast.expectedAmountMax.toLocaleString('en-IN')}
            </div>
            <div className="text-[12px] text-slate-400 font-medium mt-0.5">
              {forecast.targetMonth}
            </div>
          </div>
        </div>

        {/* Decorative Mini Bar Visual */}
        <div className="flex items-end gap-1 h-8 shrink-0 self-center">
          <div className="w-1.5 h-4 bg-blue-200 rounded-xs" />
          <div className="w-1.5 h-6 bg-blue-300 rounded-xs" />
          <div className="w-1.5 h-5 bg-blue-400 rounded-xs" />
          <div className="w-1.5 h-7 bg-blue-500 rounded-xs" />
          <div className="w-1.5 h-8 bg-blue-600 rounded-xs" />
        </div>
      </div>
    </div>
  );
};
