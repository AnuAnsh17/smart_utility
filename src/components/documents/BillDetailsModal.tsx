'use client';

import React from 'react';
import { BillData } from '@/types/bill';
import { X, FileText } from 'lucide-react';
import { orDash, formatAmount } from '@/lib/format';

interface BillDetailsModalProps {
  bill: BillData;
  onClose: () => void;
}

export const BillDetailsModal: React.FC<BillDetailsModalProps> = ({ bill, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs font-sans">
      <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200">
        {/* Header */}
        <div className="p-5 md:p-6 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200/60 flex items-center justify-center">
              <FileText className="w-5 h-5 stroke-[2]" />
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-slate-900">Extracted Bill Details</h3>
              <p className="text-xs text-slate-400">{bill.fileName} • {orDash(bill.provider)}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-full cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6">
          {/* Section 1: Bill Information */}
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Bill & Consumer Info
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[11px] font-semibold text-slate-400 block">Consumer No</span>
                <span className="text-xs font-bold text-slate-900">{orDash(bill.consumerNumber)}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[11px] font-semibold text-slate-400 block">Billing Period</span>
                <span className="text-xs font-bold text-slate-900">{orDash(bill.billingPeriod)}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[11px] font-semibold text-slate-400 block">Tariff Category</span>
                <span className="text-xs font-bold text-slate-900">{orDash(bill.tariffCategory)}</span>
              </div>
            </div>
          </div>

          {/* Section 2: Meter Reading */}
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Meter Reading & Consumption
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100">
                <span className="text-[11px] font-semibold text-emerald-800 block">Units Consumed</span>
                <span className="text-sm font-extrabold text-emerald-900">
                  {bill.unitsConsumed != null ? `${bill.unitsConsumed} ${bill.unitLabel}` : '—'}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[11px] font-semibold text-slate-400 block">Previous Reading</span>
                <span className="text-xs font-bold text-slate-900">{orDash(bill.previousReading)}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[11px] font-semibold text-slate-400 block">Current Reading</span>
                <span className="text-xs font-bold text-slate-900">{orDash(bill.currentReading)}</span>
              </div>
            </div>
          </div>

          {/* Section 3: Amount Payable */}
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Amount Payable
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-2 font-extrabold text-sm text-slate-900 bg-slate-50 px-3 rounded-lg">
                <span>Total Net Payable</span>
                <span className="text-emerald-700">
                  {formatAmount(bill.currencySymbol, bill.totalAmount)}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                The tariff components (energy, fixed/demand, duty) are recorded in the tariff
                table for this bill. They are not itemised here because the bill document itself
                does not break them out.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
