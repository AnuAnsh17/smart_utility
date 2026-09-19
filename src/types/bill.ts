export interface UploadedBillFile {
  id: string;
  name: string;
  size: number;
  type: string;
  lastModified?: number;
  isSample?: boolean;
  /**
   * The original browser File, held in memory only until the upload completes.
   * It is never serialised into state that reaches the dashboard.
   */
  rawFile?: File;
}

/**
 * A field is nullable whenever the backend refuses to guess. A bill that did
 * not state its previous reading comes back as `null` — not as 0, not as an
 * estimate — so the UI renders a dash rather than a fabricated number.
 */
export interface BillData {
  id: string;
  fileName: string;
  provider: string | null; // e.g. "Tata Power", "MSEDCL", "Adani Electricity"
  consumerNumber: string | null;
  billingPeriod: string | null; // e.g. "Oct 2024"
  billDate: string | null;
  dueDate: string | null;
  previousReading: number | null;
  currentReading: number | null;
  unitsConsumed: number | null; // e.g. 352 kWh
  unitLabel: string;
  totalAmount: number | null; // e.g. 2430
  currencySymbol: string; // e.g. "₹"
  language: string; // e.g. "English / Marathi"
  meterType: string | null; // e.g. "Smart Digital Single Phase"
  tariffCategory: string | null; // e.g. "LT-1 Residential"
}
