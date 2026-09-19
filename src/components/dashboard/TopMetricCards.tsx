'use client';

import React from 'react';
import { FileText, Zap, BarChart2, ArrowDown, ArrowUp, Minus } from 'lucide-react';
import { BillData } from '@/types/bill';
import { ForecastData } from '@/types/forecast';
import { orDash, formatAmount } from '@/lib/format';

interface TopMetricCardsProps {
  bill: BillData;
  forecast: ForecastData;
}

type Delta = { percent: number; falling: boolean };

/**
 * Month-on-month change taken from the two most recent periods actually on
 * file. Returns null when there is nothing to compare against, and the badge
 * is then omitted — a placeholder percentage here would be indistinguishable
 * from a measured one.
 */
function periodDelta(values: { kwh: number; amount: number }[], pick: (v: { kwh: number; amount: number }) => number): Delta | null {
  if (values.length < 2) return null;
  const previous = pick(values[values.length - 2]);
  const current = pick(values[values.length - 1]);
  if (!previous) return null;
  const percent = ((current - previous) / previous) * 100;
  if (!Number.isFinite(percent)) return null;
  return { percent, falling: percent < 0 };
}

const DeltaBadge: React.FC<{ delta: Delta; goodWhenFalling?: boolean }> = ({
  delta,
  goodWhenFalling = true,
}) => {
  const Icon = Math.abs(delta.percent) < 0.5 ? Minus : delta.falling ? ArrowDown : ArrowUp;
  const positive = goodWhenFalling ? delta.falling : !delta.falling;
  return (
    <div
      className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border ${
        positive
          ? 'bg-emerald-50 text-emerald-700 border-emerald-200/60'
          : 'bg-amber-50 text-amber-700 border-amber-200/60'
      }`}
    >
      <Icon className="w-3.5 h-3.5 stroke-[2.5]" />
      <span>{Math.abs(delta.percent).toFixed(0)}%</span>
      <span className="hidden xl:inline text-[10px] opacity-70 font-normal ml-0.5">
        vs prev
      </span>
    </div>
  );
};

export const TopMetricCards: React.FC<TopMetricCardsProps> = ({ bill, forecast }) => {
  const history = forecast.historicalTrend ?? [];
  const amountDelta = periodDelta(history, (v) => v.amount);
  const unitsDelta = periodDelta(history, (v) => v.kwh);
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
              {formatAmount(bill.currencySymbol, bill.totalAmount)}
            </div>
            <div className="text-[12px] text-slate-400 font-medium mt-0.5">
              {orDash(bill.billingPeriod)}
            </div>
          </div>
        </div>

        {amountDelta && <DeltaBadge delta={amountDelta} />}
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
              {bill.unitsConsumed != null
                ? `${bill.unitsConsumed} ${bill.unitLabel}`
                : '—'}
            </div>
            <div className="text-[12px] text-slate-400 font-medium mt-0.5">
              {orDash(bill.meterType)}
            </div>
          </div>
        </div>

        {unitsDelta && <DeltaBadge delta={unitsDelta} />}
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
              {forecast.reliable === false
                ? 'Not enough history'
                : `${formatAmount(bill.currencySymbol, forecast.expectedAmountMin)} – ${formatAmount(bill.currencySymbol, forecast.expectedAmountMax)}`}
            </div>
            <div className="text-[12px] text-slate-400 font-medium mt-0.5">
              {forecast.reliable === false
                ? 'Upload earlier bills to enable a forecast'
                : forecast.targetMonth}
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
