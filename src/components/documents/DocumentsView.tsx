'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { BillDocument, DocumentStatus } from '@/types/document';
import { documentService } from '@/services/documentService';
import { orDash } from '@/lib/format';
import { FileText, Eye, RefreshCw, Upload, AlertCircle } from 'lucide-react';

interface DocumentsViewProps {
  onViewBillDetails: () => void;
  onUploadNewBill: () => void;
}

const STATUS_STYLES: Record<DocumentStatus, { chip: string; dot: string }> = {
  Analysed: {
    chip: 'bg-emerald-50 text-emerald-700 border-emerald-200/60',
    dot: 'bg-emerald-500',
  },
  Processing: {
    chip: 'bg-amber-50 text-amber-700 border-amber-200/60',
    dot: 'bg-amber-500',
  },
  Failed: {
    chip: 'bg-rose-50 text-rose-700 border-rose-200/60',
    dot: 'bg-rose-500',
  },
};

export const DocumentsView: React.FC<DocumentsViewProps> = ({
  onViewBillDetails,
  onUploadNewBill,
}) => {
  const [documents, setDocuments] = useState<BillDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setDocuments(await documentService.getDocuments());
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load documents.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6 font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-900">
            Document Repository
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Bills uploaded to this machine and what was read out of each one.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start">
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="px-4 py-2 border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50 text-slate-700 text-xs font-semibold rounded-full cursor-pointer inline-flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={onUploadNewBill}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-full shadow-md shadow-emerald-600/20 cursor-pointer inline-flex items-center gap-1.5"
          >
            <Upload className="w-3.5 h-3.5" />
            Upload New Bill
          </button>
        </div>
      </div>

      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            Loading document records...
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <AlertCircle className="w-10 h-10 text-rose-300 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-slate-700">{error}</h3>
            <p className="text-xs text-slate-400 mt-1">
              Start the local backend, then refresh.
            </p>
          </div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-slate-700">No documents yet</h3>
            <p className="text-xs text-slate-400 mt-1">
              Upload a bill and it will be stored and listed here.
            </p>
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
                {documents.map((doc) => {
                  const style = STATUS_STYLES[doc.status];
                  return (
                    <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-slate-900">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100">
                            <FileText className="w-4 h-4 stroke-[2]" />
                          </div>
                          <div className="min-w-0">
                            <div className="truncate max-w-xs">{doc.fileName}</div>
                            <div className="text-[11px] font-medium text-slate-400">
                              {doc.fileSize}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-700 font-semibold">
                        {orDash(doc.provider)}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 font-medium">
                        {orDash(doc.billingPeriod)}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-slate-900">{doc.amount}</div>
                        <div className="text-[11px] text-slate-400">{doc.units}</div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          title={doc.error ?? undefined}
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border font-bold text-[11px] ${style.chip}`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                          {doc.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">{doc.uploadedAt}</td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={onViewBillDetails}
                          title="View details of the analysis on screen"
                          className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg cursor-pointer inline-flex"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {!loading && !error && documents.length > 0 && (
        <p className="text-[11px] text-slate-400">
          Files are kept on this machine only. Remove them from{' '}
          <span className="font-mono text-slate-500">backend/data/uploads</span> when
          you no longer need them.
        </p>
      )}
    </div>
  );
};
