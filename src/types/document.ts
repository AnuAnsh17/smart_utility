export type DocumentStatus = 'Analysed' | 'Processing' | 'Failed';

export interface BillDocument {
  id: string;
  fileName: string;
  provider: string;
  billingPeriod: string;
  status: DocumentStatus;
  uploadedAt: string;
  amount: string;
  units: string;
  fileSize: string;
}
