'use client';

import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import { ForecastData } from '@/types/forecast';
import { Zap, AlertCircle } from 'lucide-react';
import { formatAmount, orDash } from '@/lib/format';

interface ForecastViewProps {
  forecast: ForecastData;
  /** Taken from the bill so amounts render in the currency actually billed. */
  currencySymbol: string;
}

export const ForecastView: React.FC<ForecastViewProps> = ({ forecast, currencySymbol }) => {
  const unreliable = forecast.reliable === false;

  // Both series are consumption in kWh. The backend projects a single flat
  // figure per future month, so the chart shows that figure rather than an
  // invented kWh band derived from the rupee range.
  const chartData = [
    ...forecast.historicalTrend.map((h) => ({
      month: h.month,
      Historical: h.kwh,
      Forecasted: null,
    })),
    ...forecast.forecastTrend.map((f) => ({
      month: f.month,
      Historical: null,
      Forecasted: f.kwh,
    })),
  ];

  return (
    <div className="space-y-6 font-sans">
      {/* Header Banner */}
      <div className="p-6 md:p-8 rounded-3xl bg-gradient-to-r from-slate-900 via-slate-800 to-emerald-950 text-white shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-semibold mb-3 border border-emerald-500/30">
              <Zap className="w-3.5 h-3.5 fill-emerald-300" />
              Predictive Forecast Engine
            </div>
            <h2 className="text-2xl md:text-4xl font-extrabold tracking-tight">
              Next Month Forecast ({orDash(forecast.targetMonth)})
            </h2>
            <p className="text-xs md:text-sm text-slate-300 mt-1">
              Projected from the consumption periods on file, priced against the tariff slab
              that applies to this connection.
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-md border border-white/15 rounded-2xl p-4 md:px-6 md:py-4 text-left shrink-0">
            <div className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
              Expected Amount Range
            </div>
            <div className="text-2xl md:text-3xl font-extrabold text-white mt-0.5">
              {unreliable
                ? 'Not enough history'
                : `${formatAmount(currencySymbol, forecast.expectedAmountMin)} – ${formatAmount(currencySymbol, forecast.expectedAmountMax)}`}
            </div>
            <div className="text-xs text-emerald-300 font-medium mt-1">
              {unreliable
                ? 'Upload earlier bills to enable a forecast'
                : `Expected usage: ~${forecast.expectedUnitsKwh} kWh`}
            </div>
          </div>
        </div>
      </div>

      {/* Historical vs Forecast Chart */}
      <div className="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-extrabold text-slate-900">
              Historical Consumption vs Projected Consumption
            </h3>
            <p className="text-xs text-slate-500">
              Recorded months from your bills, followed by the projected figure.
            </p>
          </div>
        </div>

        <div className="h-72 w-full mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 12 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 11 }} />
              <Tooltip
                formatter={(val: any, name: string) => [
                  val ? `${Math.round(val)} kWh` : 'N/A',
                  name === 'Historical' ? 'Actual kWh' : 'Projected kWh',
                ]}
                contentStyle={{ backgroundColor: '#0F172A', borderRadius: '12px', color: '#fff', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Bar dataKey="Historical" fill="#10B981" radius={[6, 6, 0, 0]} maxBarSize={40} name="Historical kWh" />
              <Bar dataKey="Forecasted" fill="#60A5FA" radius={[6, 6, 0, 0]} maxBarSize={40} name="Projected kWh" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* What could affect your next bill? */}
      <div className="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-xs">
        <h3 className="text-base font-extrabold text-slate-900 mb-4 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500" />
          What could affect your next bill?
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {forecast.affectingFactors.map((factor, i) => (
            <div key={i} className="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg bg-emerald-100/70 text-emerald-800 flex items-center justify-center shrink-0 mt-0.5 font-bold">
                {i + 1}
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">{factor.title}</h4>
                <p className="text-xs text-slate-500 mt-1 leading-snug">{factor.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
