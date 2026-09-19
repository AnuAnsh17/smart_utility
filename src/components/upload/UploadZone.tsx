'use client';

import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, ArrowRight, RefreshCw } from 'lucide-react';
import { UploadedBillFile } from '@/types/bill';

interface UploadZoneProps {
  onFileSelect: (file: UploadedBillFile) => void;
  onUseSample: () => void;
  onStartAnalysis: () => void;
  selectedFile: UploadedBillFile | null;
  onClearFile: () => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFileSelect,
  onUseSample,
  onStartAnalysis,
  selectedFile,
  onClearFile,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'webp'];
  const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

  const validateAndProcessFile = (file: File) => {
    setErrorMessage(null);
    const ext = file.name.split('.').pop()?.toLowerCase() || '';

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setErrorMessage(`Unsupported format .${ext}. Please upload a PDF, JPG, PNG, or WEBP file.`);
      return;
    }

    if (file.size > MAX_SIZE_BYTES) {
      setErrorMessage(`File is too large (${(file.size / (1024 * 1024)).toFixed(1)}MB). Maximum allowed size is 10MB.`);
      return;
    }

    const uploadedBill: UploadedBillFile = {
      id: `file-${Date.now()}`,
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified,
      isSample: false,
      // Carried through to the upload call. Without this the browser File is
      // dropped here and the backend has nothing to read.
      rawFile: file,
    };

    onFileSelect(uploadedBill);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndProcessFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndProcessFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto">
      <AnimatePresence mode="wait">
        {!selectedFile ? (
          <motion.div
            key="upload-prompt"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`relative rounded-3xl border-2 transition-all duration-300 bg-white/95 p-8 md:p-10 text-center shadow-lg shadow-emerald-950/5 backdrop-blur-sm ${
              isDragging
                ? 'border-emerald-500 bg-emerald-50/50 ring-4 ring-emerald-500/10'
                : 'border-dashed border-slate-200 hover:border-emerald-400/80 hover:shadow-xl'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              className="hidden"
            />

            {/* Cloud Icon Badge */}
            <div className="mx-auto w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-500 shadow-sm mb-5 group-hover:scale-105 transition-transform duration-300">
              <UploadCloud className="w-8 h-8 stroke-[1.8]" />
            </div>

            <h3 className="text-lg font-bold text-slate-900 mb-1">
              Drag and drop your electricity bill here
            </h3>
            <p className="text-xs font-medium text-slate-400 mb-5">or</p>

            {/* Primary Browse Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white text-sm font-semibold rounded-full shadow-md shadow-emerald-600/20 hover:shadow-lg hover:shadow-emerald-600/30 transition-all duration-200 cursor-pointer inline-flex items-center gap-2"
            >
              Browse Files
            </button>

            <p className="text-[12px] text-slate-400 mt-4 mb-6">
              Supports PDF, JPG, PNG, WEBP (Max 10MB)
            </p>

            {/* Error Banner */}
            {errorMessage && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mb-6 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2 text-left"
              >
                <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                <span>{errorMessage}</span>
              </motion.div>
            )}

            {/* Divider */}
            <div className="relative my-6 flex items-center justify-center">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-100" />
              </div>
              <span className="relative bg-white px-3 text-[12px] font-medium text-slate-400">
                or try a sample bill
              </span>
            </div>

            {/* Secondary Sample Bill Button */}
            <button
              type="button"
              onClick={onUseSample}
              className="px-5 py-2 rounded-full border border-blue-200 bg-blue-50/50 hover:bg-blue-100/70 text-blue-600 text-xs font-semibold hover:border-blue-300 transition-all duration-200 cursor-pointer shadow-sm inline-flex items-center gap-2"
            >
              Use a Sample Bill
            </button>
          </motion.div>
        ) : (
          /* Selected File Preview Card */
          <motion.div
            key="file-selected"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            className="rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-xl shadow-slate-900/5 backdrop-blur-sm"
          >
            <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-600 mx-auto mb-4">
              <FileText className="w-7 h-7 stroke-[1.8]" />
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100/60 text-emerald-800 text-[12px] font-medium mb-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              {selectedFile.isSample ? 'Sample Bill Selected' : 'File Validated'}
            </div>

            <h3 className="text-base font-bold text-slate-900 mb-1 truncate max-w-md mx-auto">
              {selectedFile.name}
            </h3>
            <p className="text-xs text-slate-400 mb-6">
              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to analyse
            </p>

            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={onClearFile}
                className="px-4 py-2.5 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-medium transition-colors cursor-pointer inline-flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Change File
              </button>

              <button
                type="button"
                onClick={onStartAnalysis}
                className="px-7 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-full shadow-lg shadow-emerald-600/25 hover:shadow-xl transition-all duration-200 cursor-pointer inline-flex items-center gap-2 group"
              >
                Analyse my bill
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
