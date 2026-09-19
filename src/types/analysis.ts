export type StepStatus = 'pending' | 'processing' | 'completed';

export interface AnalysisPipelineStep {
  id: string;
  label: string;
  status: StepStatus;
  detail?: string;
}

export type AppStage =
  | 'landing'
  | 'processing'
  | 'complete'
  | 'failed'
  | 'preparing_demo'
  | 'dashboard';

export interface AnalysisResult {
  bill: import('./bill').BillData;
  insights: import('./insight').InsightItem[];
  forecast: import('./forecast').ForecastData;
  weather: import('./weather').WeatherData;
  recommendations: import('./insight').Recommendation[];
}

/** Per-job facts that describe the analysis rather than the bill itself. */
export interface AnalysisMeta {
  jobId: string;
  /** Non-fatal notices, such as a thin history or missing weather context. */
  warnings: string[];
  /** Fields the backend could not read and deliberately left null. */
  missingFields: string[];
  detectedLanguage: string;
  ocrEngine: string | null;
  ocrMeanConfidence: number | null;
  timings: { stage: string; durationMs: number }[];
}

export interface LiveAnalysis {
  result: AnalysisResult;
  meta: AnalysisMeta;
}
