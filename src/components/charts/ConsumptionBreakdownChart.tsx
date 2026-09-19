'use client';

import React from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { ApplianceBreakdown } from '@/types/forecast';

interface ConsumptionBreakdownChartProps {
  data: ApplianceBreakdown[];
  /** Null when the bill did not state a units-consumed figure. */
  totalKwh: number | null;
}

export const ConsumptionBreakdownChart: React.FC<ConsumptionBreakdownChartProps> = ({
  data,
  totalKwh,
}) => {
  if (data.length === 0) {
    // Nothing to break down: the backend only emits a breakdown when it has a
    // units figure to apportion, so an empty list is a real answer, not a gap
    // to fill with a placeholder donut.
    return (
      <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex flex-col h-full font-sans">
        <h3 className="text-base font-extrabold text-slate-900 mb-2">
          Consumption Breakdown
        </h3>
        <div className="flex-1 flex items-center justify-center text-center py-10">
          <p className="text-xs text-slate-400 max-w-[16rem] leading-relaxed">
            No appliance breakdown available for this bill.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex flex-col justify-between h-full font-sans">
      <h3 className="text-base font-extrabold text-slate-900 mb-2">
        Consumption Breakdown
      </h3>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 my-auto">
        {/* Donut Chart with Center Text */}
        <div className="relative w-44 h-44 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip
                formatter={(val: number) => [`${val}%`, 'Usage Share']}
                contentStyle={{
                  backgroundColor: '#0F172A',
                  borderRadius: '12px',
                  color: '#fff',
                  fontSize: '12px',
                  border: 'none',
                }}
              />
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={72}
                paddingAngle={4}
                dataKey="percentage"
                stroke="none"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          {/* Center Overlay Text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
            <span className="text-base font-extrabold text-slate-900 leading-none">
              {totalKwh != null ? `${totalKwh} kWh` : '—'}
            </span>
            <span className="text-[11px] font-semibold text-slate-400 mt-0.5">
              Total
            </span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex-1 space-y-2 w-full">
          {data.map((item, idx) => (
            <div key={idx} className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-slate-700 font-medium">{item.name}</span>
              </div>
              <span className="text-slate-900 font-bold">{item.percentage}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
