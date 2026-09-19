/**
 * Thin client for the local Smart Utility backend.
 *
 * Every request goes to a loopback address by default. Documents are posted as
 * multipart bodies to the local FastAPI process and never leave the machine
 * unless NEXT_PUBLIC_API_BASE is pointed somewhere else on purpose.
 */

import { AnalysisResult } from '@/types/analysis';

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000/api/v1';

/** Wire format: the backend serialises pydantic fields without an alias. */
export interface JobTiming {
  stage: string;
  duration_ms: number;
}

export interface JobStatusPayload {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  stage: string;
  ui_step: string;
  ui_step_index: number;
  progress: number;
  message: string;
  error_code?: string | null;
  error_message?: string | null;
  warnings: string[];
  timings: JobTiming[];
}

export interface AnalysisPayload {
  job_id: string;
  status: string;
  analysis: AnalysisResult;
  warnings: string[];
  missing_fields: string[];
  detected_language: string;
  ocr_engine: string | null;
  ocr_mean_confidence: number | null;
  timings: JobTiming[];
}

export interface UploadAccepted {
  job_id: string;
  document_id: string;
  file_name: string;
  size_bytes: number;
  status: string;
}

export interface DocumentSummaryPayload {
  id: string;
  job_id: string | null;
  file_name: string;
  provider: string | null;
  billing_period: string | null;
  units: number | null;
  amount: number | null;
  unit_label: string;
  currency_symbol: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  uploaded_at: string;
  size_bytes: number;
  detected_language: string | null;
  error_message: string | null;
}

export interface DocumentListPayload {
  documents: DocumentSummaryPayload[];
  total: number;
}

/** Raised for any backend error the caller should show to the user verbatim. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string = 'request_failed',
    readonly status?: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === 'string') return detail;
    if (detail?.message) return detail.message as string;
    if (body?.message) return body.message as string;
  } catch {
    // Non-JSON error body: fall through to the generic message.
  }
  return `The backend returned ${response.status}.`;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { signal, cache: 'no-store' });
  } catch {
    throw new ApiError(
      'Could not reach the local analysis service. Is the backend running?',
      'backend_unreachable'
    );
  }
  if (!response.ok) {
    throw new ApiError(await readError(response), 'request_failed', response.status);
  }
  return (await response.json()) as T;
}

export async function uploadBill(
  file: File,
  signal?: AbortSignal
): Promise<UploadAccepted> {
  const form = new FormData();
  form.append('file', file, file.name);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/bills/upload`, {
      method: 'POST',
      body: form,
      signal,
    });
  } catch {
    throw new ApiError(
      'Could not reach the local analysis service. Is the backend running?',
      'backend_unreachable'
    );
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), 'upload_failed', response.status);
  }
  return (await response.json()) as UploadAccepted;
}

export function fetchJobStatus(
  jobId: string,
  signal?: AbortSignal
): Promise<JobStatusPayload> {
  return getJson<JobStatusPayload>(`/bills/${jobId}`, signal);
}

export function fetchAnalysis(
  jobId: string,
  signal?: AbortSignal
): Promise<AnalysisPayload> {
  return getJson<AnalysisPayload>(`/bills/${jobId}/analysis`, signal);
}

export function getDocumentsPage(signal?: AbortSignal): Promise<DocumentListPayload> {
  return getJson<DocumentListPayload>('/bills', signal);
}

export interface ChatPayload {
  session_id: string;
  reply: string;
  scope_decision: 'answered' | 'out_of_scope' | 'insufficient_context' | 'rejected';
  suggested_followups: string[];
  grounded_on_job_id: string | null;
}

/**
 * Ask the local electricity assistant.
 *
 * The backend decides scope; a refusal or an "I don't know" comes back as a
 * normal reply with a `scope_decision`, so the UI never has to guess.
 */
export async function sendChatMessage(body: {
  message: string;
  job_id?: string | null;
  session_id?: string | null;
}): Promise<ChatPayload> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/assistant/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      'Could not reach the local analysis service. Is the backend running?',
      'backend_unreachable'
    );
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), 'request_failed', response.status);
  }
  return (await response.json()) as ChatPayload;
}

export interface StreamHandlers {
  onStatus: (status: JobStatusPayload) => void;
  onError: (error: ApiError) => void;
}

const POLL_INTERVAL_MS = 400;

/**
 * Follow a job to completion.
 *
 * Server-sent events are the fast path, but a proxy or a dropped connection
 * can leave an EventSource permanently silent. A poll timer runs alongside it
 * and is the authoritative signal: whichever reports a terminal status first
 * wins, and the stream is torn down either way.
 */
export function followJob(
  jobId: string,
  handlers: StreamHandlers,
  signal?: AbortSignal
): () => void {
  let finished = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let source: EventSource | undefined;

  const stop = () => {
    if (finished) return;
    finished = true;
    if (timer) clearTimeout(timer);
    source?.close();
  };

  if (signal) {
    if (signal.aborted) return stop;
    signal.addEventListener('abort', stop, { once: true });
  }

  const deliver = (payload: JobStatusPayload) => {
    if (finished) return;
    handlers.onStatus(payload);
    if (payload.status === 'completed' || payload.status === 'failed') stop();
  };

  const poll = async () => {
    if (finished) return;
    try {
      deliver(await fetchJobStatus(jobId));
    } catch (error) {
      if (error instanceof ApiError) {
        handlers.onError(error);
        stop();
        return;
      }
    }
    if (!finished) timer = setTimeout(poll, POLL_INTERVAL_MS);
  };

  try {
    source = new EventSource(`${API_BASE}/bills/${jobId}/events`);
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as JobStatusPayload;
        if (payload?.status) deliver(payload);
      } catch {
        // A malformed frame is not fatal; the poll timer covers us.
      }
    };
    source.onerror = () => {
      // EventSource retries on its own. The poll timer is what keeps the UI
      // moving, so a stream error is deliberately not surfaced as a failure.
      source?.close();
      source = undefined;
    };
  } catch {
    source = undefined;
  }

  void poll();
  return stop;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, { cache: 'no-store' });
    return response.ok;
  } catch {
    return false;
  }
}
