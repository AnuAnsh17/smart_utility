import { BillDocument } from '../types/document';

const MOCK_DOCUMENTS: BillDocument[] = [
  {
    id: 'doc-1',
    fileName: 'electricity_bill_october.pdf',
    provider: 'Tata Power',
    billingPeriod: 'Oct 2024',
    status: 'Analysed',
    uploadedAt: '18 Sep 2026',
    amount: '₹2,430',
    units: '352 kWh',
    fileSize: '1.2 MB'
  },
  {
    id: 'doc-2',
    fileName: 'electricity_bill_september.pdf',
    provider: 'Tata Power',
    billingPeriod: 'Sep 2024',
    status: 'Analysed',
    uploadedAt: '05 Sep 2026',
    amount: '₹2,310',
    units: '330 kWh',
    fileSize: '1.1 MB'
  },
  {
    id: 'doc-3',
    fileName: 'electricity_bill_august.pdf',
    provider: 'Tata Power',
    billingPeriod: 'Aug 2024',
    status: 'Analysed',
    uploadedAt: '02 Aug 2026',
    amount: '₹2,660',
    units: '380 kWh',
    fileSize: '1.4 MB'
  }
];

export class DocumentService {
  async getDocuments(): Promise<BillDocument[]> {
    return MOCK_DOCUMENTS;
  }
}

export const documentService = new DocumentService();
