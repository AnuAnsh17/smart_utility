export type DocumentStatus = 'Analysed' | 'Processing' | 'Failed';

export interface BillDocument {
  id: string;
  /** Null for a document that never got a job row. */
  jobId: string | null;
  fileName: string;
  /** Null when the reader could not find a provider on the document. */
  provider: string | null;
  billingPeriod: string | null;
  status: DocumentStatus;
  uploadedAt: string;
  /** Pre-formatted with the bill's own currency symbol, or '—'. */
  amount: string;
  /** Pre-formatted with the bill's own unit label, or '—'. */
  units: string;
  fileSize: string;
  /** Set when the job failed, so the row can explain itself. */
  error: string | null;
}
