import { UploadedBillFile, BillData } from '../types/bill';
import { AnalysisResult, AnalysisPipelineStep } from '../types/analysis';
import { CENTRALIZED_SAMPLE_ANALYSIS } from '../config/sampleData';

export const INITIAL_PIPELINE_STEPS: AnalysisPipelineStep[] = [
  { id: 'upload', label: 'File uploaded', status: 'completed' },
  { id: 'language', label: 'Detecting language', status: 'pending' },
  { id: 'extract', label: 'Extracting bill information', status: 'pending' },
  { id: 'patterns', label: 'Analysing consumption patterns', status: 'pending' },
  { id: 'weather', label: 'Fetching weather data', status: 'pending' },
  { id: 'dashboard', label: 'Preparing your dashboard', status: 'pending' },
];

export const MOCK_BILL_DATA: BillData = CENTRALIZED_SAMPLE_ANALYSIS.bill;
export const MOCK_ANALYSIS_RESULT: AnalysisResult = CENTRALIZED_SAMPLE_ANALYSIS;

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
    return CENTRALIZED_SAMPLE_ANALYSIS;
  }

  async getSampleAnalysis(): Promise<AnalysisResult> {
    return CENTRALIZED_SAMPLE_ANALYSIS;
  }
}

export const analysisService = new AnalysisService();
