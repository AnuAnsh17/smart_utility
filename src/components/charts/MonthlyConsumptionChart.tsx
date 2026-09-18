'use client';

import React, { useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { MonthlyConsumption } from '@/types/forecast';
import { ChevronDown } from 'lucide-react';

interface MonthlyConsumptionChartProps {
  data: MonthlyConsumption[];
}

export const MonthlyConsumptionChart: React.FC<MonthlyConsumptionChartProps> = ({ data }) => {
  const [range, setRange] = useState<'6m' | '1y' | '3y'>('6m');

  const customTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item: MonthlyConsumption = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white text-xs p-2.5 rounded-xl shadow-xl border border-slate-800">
          <div className="font-bold text-slate-200">{item.fullMonth || item.month}</div>
          <div className="text-emerald-400 font-semibold mt-0.5">
            Consumption: {item.kwh} kWh
          </div>
          <div className="text-slate-400 text-[11px]">
            Est. Cost: ₹{item.amount.toLocaleString('en-IN')}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex flex-col justify-between h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-extrabold text-slate-900">
          Monthly Consumption
        </h3>

        {/* Filter Dropdown */}
        <div className="relative">
          <select
            value={range}
            onChange={(e) => setRange(e.target.value as any)}
            className="appearance-none bg-slate-50 border border-slate-200/90 rounded-lg pl-3 pr-7 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 cursor-pointer outline-none"
          >
            <option value="6m">Last 6 Months</option>
            <option value="1y">1 Year</option>
            <option value="3y">3 Years</option>
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

      {/* Chart */}
      <div className="h-56 w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#64748B', fontSize: 12, fontWeight: 500 }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#94A3B8', fontSize: 11 }}
              domain={[0, 500]}
              ticks={[0, 100, 200, 300, 400, 500]}
            />
            <Tooltip content={customTooltip} cursor={{ fill: 'rgba(241, 245, 249, 0.6)' }} />
            <Bar dataKey="kwh" radius={[6, 6, 0, 0]} maxBarSize={38}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.isCurrent ? '#059669' : '#5EEAD4'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
