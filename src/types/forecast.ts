export interface MonthlyConsumption {
  month: string;
  fullMonth: string;
  kwh: number;
  amount: number;
  isCurrent?: boolean;
}

export interface ApplianceBreakdown {
  name: string;
  percentage: number;
  color: string;
  estimatedKwh: number;
}

export interface ForecastData {
  targetMonth: string; // e.g. "Nov 2024"
  expectedAmountMin: number; // e.g. 2650
  expectedAmountMax: number; // e.g. 2950
  expectedUnitsKwh: number; // e.g. 386
  historicalTrend: MonthlyConsumption[];
  forecastTrend: { month: string; kwh: number; amountMin: number; amountMax: number }[];
  affectingFactors: {
    icon: string;
    title: string;
    description: string;
  }[];
  applianceBreakdown: ApplianceBreakdown[];
}
