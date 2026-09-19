import { BillDocument, DocumentStatus } from '../types/document';
import { formatAmount } from '../lib/format';
import { getDocumentsPage } from './apiClient';

const STATUS_MAP: Record<string, DocumentStatus> = {
  completed: 'Analysed',
  processing: 'Processing',
  queued: 'Processing',
  failed: 'Failed',
};

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return '—';
  return parsed.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * The local document library.
 *
 * Rows come from the backend's own record of what was uploaded and what was
 * read out of it. Anything the extractor missed stays blank rather than being
 * filled in with a plausible-looking value.
 */
export class DocumentService {
  async getDocuments(): Promise<BillDocument[]> {
    const payload = await getDocumentsPage();

    return payload.documents.map((doc) => ({
      id: doc.id,
      jobId: doc.job_id,
      fileName: doc.file_name,
      provider: doc.provider,
      billingPeriod: doc.billing_period,
      status: STATUS_MAP[doc.status] ?? 'Processing',
      uploadedAt: formatDate(doc.uploaded_at),
      amount:
        doc.amount == null ? '—' : formatAmount(doc.currency_symbol || '₹', doc.amount),
      units:
        doc.units == null
          ? '—'
          : `${doc.units.toLocaleString('en-IN')} ${doc.unit_label || 'kWh'}`,
      fileSize: formatBytes(doc.size_bytes),
      error: doc.error_message ?? null,
    }));
  }
}

export const documentService = new DocumentService();
