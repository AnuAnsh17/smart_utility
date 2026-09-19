import { BillData } from '../types/bill';
import {
  AnalysisResult,
  AnalysisPipelineStep,
  AnalysisMeta,
  LiveAnalysis,
} from '../types/analysis';
import { CENTRALIZED_SAMPLE_ANALYSIS } from '../config/sampleData';
import {
  ApiError,
  JobStatusPayload,
  fetchAnalysis,
  followJob,
  uploadBill,
} from './apiClient';

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

/**
 * How the backend reports a step failing in a way the user can act on, and the
 * three messages the specification fixes verbatim. Anything the backend sends
 * that is not one of these is treated as a generic unreadable-document failure
 * rather than being shown raw.
 */
export const FAILURE_MESSAGES = {
  unreadable: 'Unable to read this document. Try a clearer image or PDF.',
  partial: 'Some information could not be extracted.',
  thinHistory: 'Not enough historical data to generate a reliable forecast.',
} as const;

function failureMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === 'backend_unreachable') {
    return error.message;
  }
  if (error instanceof ApiError && error.status === 422) {
    return error.message;
  }
  return FAILURE_MESSAGES.unreadable;
}

/** Map a backend stage index onto the pipeline list shown in the UI. */
export function stepsForIndex(index: number): AnalysisPipelineStep[] {
  const clamped = Math.max(0, Math.min(index, INITIAL_PIPELINE_STEPS.length));
  return INITIAL_PIPELINE_STEPS.map((step, i) => ({
    ...step,
    status: i < clamped ? 'completed' : i === clamped ? 'processing' : 'pending',
  }));
}

function allStepsComplete(): AnalysisPipelineStep[] {
  return INITIAL_PIPELINE_STEPS.map((step) => ({ ...step, status: 'completed' }));
}

function toMeta(payload: {
  job_id: string;
  warnings: string[];
  missing_fields: string[];
  detected_language: string;
  ocr_engine: string | null;
  ocr_mean_confidence: number | null;
  timings: { stage: string; duration_ms: number }[];
}): AnalysisMeta {
  return {
    jobId: payload.job_id,
    warnings: payload.warnings ?? [],
    missingFields: payload.missing_fields ?? [],
    detectedLanguage: payload.detected_language,
    ocrEngine: payload.ocr_engine,
    ocrMeanConfidence: payload.ocr_mean_confidence,
    timings: (payload.timings ?? []).map((t) => ({
      stage: t.stage,
      durationMs: t.duration_ms,
    })),
  };
}

export interface LiveAnalysisHandlers {
  /** Called on every progress update with the pipeline list to render. */
  onStepChange: (steps: AnalysisPipelineStep[], status: JobStatusPayload) => void;
}

export class AnalysisService {
  /**
   * Run a real upload through the local backend.
   *
   * The document goes to the loopback backend, which stores it, queues a job
   * and processes it. Progress reported here is the backend's own; nothing in
   * this file advances on a timer, so a stalled job looks stalled rather than
   * completing itself.
   */
  async runLiveAnalysis(
    file: File,
    handlers: LiveAnalysisHandlers,
    signal?: AbortSignal
  ): Promise<LiveAnalysis> {
    const accepted = await uploadBill(file);

    const finished = await new Promise<JobStatusPayload>((resolve, reject) => {
      const stop = followJob(
        accepted.job_id,
        {
          onStatus: (status) => {
            handlers.onStepChange(stepsForIndex(status.ui_step_index), status);
            if (status.status === 'completed') {
              stop();
              resolve(status);
            } else if (status.status === 'failed') {
              stop();
              reject(
                new ApiError(
                  status.error_message || FAILURE_MESSAGES.unreadable,
                  status.error_code ?? 'job_failed'
                )
              );
            }
          },
          onError: (error) => {
            stop();
            reject(error);
          },
        },
        signal
      );
      signal?.addEventListener(
        'abort',
        () => reject(new ApiError('Analysis cancelled.', 'cancelled')),
        { once: true }
      );
    });

    handlers.onStepChange(allStepsComplete(), finished);
    const payload = await fetchAnalysis(accepted.job_id);
    return { result: payload.analysis, meta: toMeta({ ...payload, job_id: accepted.job_id }) };
  }

  /** The explicit demo path. Never used for a file the user actually picked. */
  async getSampleAnalysis(): Promise<AnalysisResult> {
    return CENTRALIZED_SAMPLE_ANALYSIS;
  }
}

export { failureMessage };

export const analysisService = new AnalysisService();
