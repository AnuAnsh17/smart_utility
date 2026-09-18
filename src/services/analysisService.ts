import { UploadedBillFile, BillData } from '../types/bill';
import { AnalysisResult, AnalysisPipelineStep } from '../types/analysis';

export const INITIAL_PIPELINE_STEPS: AnalysisPipelineStep[] = [
  { id: 'upload', label: 'File uploaded', status: 'completed' },
  { id: 'language', label: 'Detecting language', status: 'pending' },
  { id: 'extract', label: 'Extracting bill information', status: 'pending' },
  { id: 'patterns', label: 'Analysing consumption patterns', status: 'pending' },
  { id: 'weather', label: 'Fetching weather data', status: 'pending' },
  { id: 'dashboard', label: 'Preparing your dashboard', status: 'pending' },
];

export const MOCK_BILL_DATA: BillData = {
  id: 'bill-oct-2024',
  fileName: 'electricity_bill_october.pdf',
  provider: 'Tata Power',
  consumerNumber: '02819481920',
  billingPeriod: 'Oct 2024',
  billDate: '02 Oct 2024',
  dueDate: '16 Oct 2024',
  previousReading: 4120,
  currentReading: 4472,
  unitsConsumed: 352,
  unitLabel: 'kWh',
  totalAmount: 2430,
  currencySymbol: '₹',
  language: 'English / Hindi',
  meterType: 'Smart Digital Single Phase',
  tariffCategory: 'Residential LT-1',
};

export const MOCK_ANALYSIS_RESULT: AnalysisResult = {
  bill: MOCK_BILL_DATA,
  forecast: {
    targetMonth: 'Nov 2024',
    expectedAmountMin: 2650,
    expectedAmountMax: 2950,
    expectedUnitsKwh: 386,
    historicalTrend: [
      { month: 'May', fullMonth: 'May 2024', kwh: 260, amount: 1820 },
      { month: 'Jun', fullMonth: 'Jun 2024', kwh: 290, amount: 2030 },
      { month: 'Jul', fullMonth: 'Jul 2024', kwh: 310, amount: 2170 },
      { month: 'Aug', fullMonth: 'Aug 2024', kwh: 380, amount: 2660 },
      { month: 'Sep', fullMonth: 'Sep 2024', kwh: 330, amount: 2310 },
      { month: 'Oct', fullMonth: 'Oct 2024', kwh: 352, amount: 2430, isCurrent: true },
    ],
    forecastTrend: [
      { month: 'Oct', kwh: 352, amountMin: 2430, amountMax: 2430 },
      { month: 'Nov', kwh: 386, amountMin: 2650, amountMax: 2950 },
      { month: 'Dec', kwh: 340, amountMin: 2350, amountMax: 2600 },
      { month: 'Jan', kwh: 310, amountMin: 2100, amountMax: 2400 },
    ],
    affectingFactors: [
      {
        icon: 'thermometer',
        title: 'Cooling Demand',
        description: 'Humidity in Nov may require higher AC usage during daytime hours.'
      },
      {
        icon: 'cloud-sun',
        title: 'Seasonal Transition',
        description: 'Slight cooling toward late Nov expected to stabilize baseline evening loads.'
      },
      {
        icon: 'zap',
        title: 'Slab Rate Shift',
        description: 'Crossing 300 units pushes kWh slab rate into higher tariff bracket (₹7.20/unit).'
      }
    ],
    applianceBreakdown: [
      { name: 'AC', percentage: 38, color: '#3B82F6', estimatedKwh: 133.7 },
      { name: 'Refrigerator', percentage: 18, color: '#10B981', estimatedKwh: 63.3 },
      { name: 'Lighting', percentage: 12, color: '#06B6D4', estimatedKwh: 42.2 },
      { name: 'Fans', percentage: 10, color: '#F97316', estimatedKwh: 35.2 },
      { name: 'Other', percentage: 22, color: '#F59E0B', estimatedKwh: 77.4 },
    ]
  },
  weather: {
    location: 'Mumbai, MH',
    tempC: 28,
    condition: 'Hot & Humid',
    humidityPercent: 78,
    impactLevel: 'Moderate',
    impactSummary: 'Moderate impact on consumption',
    detailNote: 'High relative humidity (78%) increases compressor run-time for air conditioners.'
  },
  insights: [
    {
      id: 'ins-1',
      type: 'warning',
      iconName: 'zap',
      text: 'Your consumption increased by 5% compared to similar households.'
    },
    {
      id: 'ins-2',
      type: 'positive',
      iconName: 'shieldCheck',
      text: 'AC usage is higher than average for this season.'
    },
    {
      id: 'ins-3',
      type: 'neutral',
      iconName: 'droplet',
      text: 'Your bill is within the expected range.'
    },
    {
      id: 'ins-4',
      type: 'info',
      iconName: 'sparkles',
      text: 'Consider using a 5-star rated AC to reduce consumption.'
    }
  ],
  recommendations: [
    {
      id: 'rec-1',
      title: 'Reduce AC usage by 1 hour daily',
      impactLevel: 'High',
      suggestedAction: 'Set AC timer to automatically turn off at 5 AM.',
      whyItMatters: 'Compressors consume ~1.5 kWh per hour of active cooling.',
      potentialImpact: 'Save ~₹350/month',
      iconName: 'leaf'
    },
    {
      id: 'rec-2',
      title: 'Use 5-star rated appliances',
      impactLevel: 'High',
      suggestedAction: 'Upgrade old inverter AC and refrigerator.',
      whyItMatters: 'Older non-inverter units draw up to 40% more electricity.',
      potentialImpact: 'Save up to ₹800/month',
      iconName: 'shield'
    },
    {
      id: 'rec-3',
      title: 'Avoid high usage during peak hours',
      impactLevel: 'Medium',
      suggestedAction: 'Shift heavy washing machine runs to off-peak afternoon periods.',
      whyItMatters: 'Grid demand is highest between 6 PM - 10 PM.',
      potentialImpact: 'Reduces peak load demand',
      iconName: 'clock'
    }
  ]
};

export class AnalysisService {
  async simulateAnalysisProgress(
    onStepChange: (stepId: string, stepIndex: number) => void
  ): Promise<AnalysisResult> {
    const steps = ['language', 'extract', 'patterns', 'weather', 'dashboard'];
    for (let i = 0; i < steps.length; i++) {
      await new Promise(res => setTimeout(res, 800));
      onStepChange(steps[i], i + 1);
    }
    await new Promise(res => setTimeout(res, 600));
    return MOCK_ANALYSIS_RESULT;
  }
}

export const analysisService = new AnalysisService();
