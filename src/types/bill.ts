export interface UploadedBillFile {
  id: string;
  name: string;
  size: number;
  type: string;
  lastModified?: number;
  isSample?: boolean;
}

export interface BillData {
  id: string;
  fileName: string;
  provider: string; // e.g. "Tata Power", "MSEDCL", "Adani Electricity"
  consumerNumber: string;
  billingPeriod: string; // e.g. "Oct 2024"
  billDate: string;
  dueDate: string;
  previousReading: number;
  currentReading: number;
  unitsConsumed: number; // e.g. 352 kWh
  unitLabel: string;
  totalAmount: number; // e.g. 2430
  currencySymbol: string; // e.g. "₹"
  language: string; // e.g. "English / Marathi"
  meterType: string; // e.g. "Smart Digital Single Phase"
  tariffCategory: string; // e.g. "LT-1 Residential"
}
