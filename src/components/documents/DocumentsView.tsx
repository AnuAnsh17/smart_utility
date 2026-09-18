'use client';

import React, { useEffect, useState } from 'react';
import { BillDocument } from '@/types/document';
import { documentService } from '@/services/documentService';
import { FileText, Eye, Trash2, RefreshCw, Upload } from 'lucide-react';

interface DocumentsViewProps {
  onViewBillDetails: () => void;
  onUploadNewBill: () => void;
}

export const DocumentsView: React.FC<DocumentsViewProps> = ({
  onViewBillDetails,
  onUploadNewBill,
}) => {
  const [documents, setDocuments] = useState<BillDocument[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    documentService.getDocuments().then((docs) => {
      setDocuments(docs);
      setLoading(false);
    });
  }, []);

  const handleDelete = (id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  return (
    <div className="space-y-6 font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-900">
            Document Repository
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            View previously uploaded electricity bills and OCR analysis records.
          </p>
        </div>

        <button
          type="button"
          onClick={onUploadNewBill}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-full shadow-md shadow-emerald-600/20 cursor-pointer inline-flex items-center gap-1.5 self-start"
        >
          <Upload className="w-3.5 h-3.5" />
          Upload New Bill
        </button>
      </div>

      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            Loading document records...
          </div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-slate-700">No documents found</h3>
            <p className="text-xs text-slate-400 mt-1">Upload a bill to get started.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200/80 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-4">File Name</th>
                  <th className="py-3.5 px-4">Provider</th>
                  <th className="py-3.5 px-4">Period</th>
                  <th className="py-3.5 px-4">Units / Amount</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Uploaded</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100">
                        <FileText className="w-4 h-4 stroke-[2]" />
                      </div>
                      <span className="truncate max-w-xs">{doc.fileName}</span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-700 font-semibold">{doc.provider}</td>
                    <td className="py-3.5 px-4 text-slate-600 font-medium">{doc.billingPeriod}</td>
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{doc.amount}</div>
                      <div className="text-[11px] text-slate-400">{doc.units}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60 font-bold text-[11px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        {doc.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">{doc.uploadedAt}</td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={onViewBillDetails}
                          title="View Details"
                          className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg cursor-pointer"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          title="Delete Document"
                          className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
