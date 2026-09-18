export type StepStatus = 'pending' | 'processing' | 'completed';

export interface AnalysisPipelineStep {
  id: string;
  label: string;
  status: StepStatus;
  detail?: string;
}

export type AppStage = 'landing' | 'processing' | 'complete' | 'dashboard';

export interface AnalysisResult {
  bill: import('./bill').BillData;
  insights: import('./insight').InsightItem[];
  forecast: import('./forecast').ForecastData;
  weather: import('./weather').WeatherData;
  recommendations: import('./insight').Recommendation[];
}
