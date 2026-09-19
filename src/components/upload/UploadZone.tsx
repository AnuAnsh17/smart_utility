'use client';

import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  Plus,
  X,
} from 'lucide-react';
import { UploadedBillFile } from '@/types/bill';

/** How many bills one batch may carry. */
export const MAX_BATCH_FILES = 10;

interface UploadZoneProps {
  onFilesSelect: (files: UploadedBillFile[]) => void;
  onUseSample: () => void;
  onStartAnalysis: () => void;
  selectedFiles: UploadedBillFile[];
  onClearFiles: () => void;
  onRemoveFile: (id: string) => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFilesSelect,
  onUseSample,
  onStartAnalysis,
  selectedFiles,
  onClearFiles,
  onRemoveFile,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);

  const ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'webp'];
  const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10MB per file

  /**
   * Sort an incoming selection into files we can send and reasons we cannot.
   *
   * Rejections are collected rather than thrown, so one bad file in a batch of
   * ten does not discard the other nine. Duplicates are keyed on name+size and
   * files already in the batch are counted against the cap, which means a
   * second drop tops the batch up instead of replacing it.
   */
  const validateFiles = (incoming: File[], existing: UploadedBillFile[]) => {
    const accepted: UploadedBillFile[] = [];
    const rejected: string[] = [];
    const known = new Set(existing.map((file) => `${file.name}:${file.size}`));
    let queued = existing.length;
    let overflowed = 0;

    incoming.forEach((file, index) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';

      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        rejected.push(`${file.name} — unsupported format .${ext}`);
        return;
      }

      if (file.size > MAX_SIZE_BYTES) {
        rejected.push(
          `${file.name} — too large (${(file.size / (1024 * 1024)).toFixed(1)}MB, max 10MB)`
        );
        return;
      }

      const key = `${file.name}:${file.size}`;
      if (known.has(key)) {
        rejected.push(`${file.name} — already in the batch`);
        return;
      }

      if (queued >= MAX_BATCH_FILES) {
        overflowed += 1;
        return;
      }

      known.add(key);
      queued += 1;
      accepted.push({
        // The index keeps ids unique when a batch is picked in one tick, which
        // a bare Date.now() does not.
        id: `file-${Date.now()}-${index}`,
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified,
        isSample: false,
        // Carried through to the upload call. Without this the browser File is
        // dropped here and the backend has nothing to read.
        rawFile: file,
      });
    });

    if (overflowed > 0) {
      rejected.push(
        `${overflowed} more file${overflowed > 1 ? 's' : ''} not added — ${MAX_BATCH_FILES} bills per batch`
      );
    }

    return { accepted, rejected };
  };

  const addFiles = (incoming: File[]) => {
    const { accepted, rejected } = validateFiles(incoming, selectedFiles);
    setProblems(rejected);
    if (accepted.length > 0) {
      onFilesSelect([...selectedFiles, ...accepted]);
    }
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
    const dropped = e.dataTransfer.files;
    if (dropped && dropped.length > 0) {
      addFiles(Array.from(dropped));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files;
    if (picked && picked.length > 0) {
      addFiles(Array.from(picked));
    }
    // Reset so removing a file and picking the same one again still fires.
    e.target.value = '';
  };

  const fileCount = selectedFiles.length;
  const totalBytes = selectedFiles.reduce((sum, file) => sum + file.size, 0);

  return (
    <div className="w-full max-w-xl mx-auto">
      {/* Always mounted, so both the empty state and the preview card can open it. */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.jpg,.jpeg,.png,.webp"
        multiple
        className="hidden"
      />

      <AnimatePresence mode="wait">
        {fileCount === 0 ? (
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
            {/* Cloud Icon Badge */}
            <div className="mx-auto w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-500 shadow-sm mb-5 group-hover:scale-105 transition-transform duration-300">
              <UploadCloud className="w-8 h-8 stroke-[1.8]" />
            </div>

            <h3 className="text-lg font-bold text-slate-900 mb-1">
              Drag and drop your electricity bills here
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
              Supports PDF, JPG, PNG, WEBP (Max 10MB each &bull; up to {MAX_BATCH_FILES} bills)
            </p>

            {/* Error Banner */}
            <ErrorBanner problems={problems} />

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
          /* Selected Files Preview Card */
          <motion.div
            key="file-selected"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            className={`rounded-3xl border bg-white p-8 text-center shadow-xl shadow-slate-900/5 backdrop-blur-sm transition-all duration-300 ${
              isDragging ? 'border-emerald-500 ring-4 ring-emerald-500/10' : 'border-slate-200'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-600 mx-auto mb-4">
              <FileText className="w-7 h-7 stroke-[1.8]" />
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100/60 text-emerald-800 text-[12px] font-medium mb-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              {fileCount > 1
                ? `${fileCount} bills validated`
                : selectedFiles[0].isSample
                ? 'Sample Bill Selected'
                : 'File Validated'}
            </div>

            <h3 className="text-base font-bold text-slate-900 mb-1">
              {fileCount > 1 ? `${fileCount} bills ready` : selectedFiles[0].name}
            </h3>
            <p className="text-xs text-slate-400 mb-5">
              {(totalBytes / (1024 * 1024)).toFixed(2)} MB total &bull; analysed one by one
            </p>

            {/* The batch itself. Each row can be dropped before the run starts. */}
            <div className="max-h-60 overflow-y-auto pr-1 space-y-1.5 text-left mb-5">
              {selectedFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-2.5 rounded-xl border border-slate-200/80 bg-slate-50/60 px-3 py-2"
                >
                  <FileText className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-[12px] font-semibold text-slate-800 truncate">
                      {file.name}
                    </div>
                    <div className="text-[11px] text-slate-400">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => onRemoveFile(file.id)}
                    aria-label={`Remove ${file.name}`}
                    className="shrink-0 w-6 h-6 rounded-full text-slate-400 hover:text-rose-600 hover:bg-rose-50 flex items-center justify-center transition-colors cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>

            <ErrorBanner problems={problems} />

            <div className="flex flex-wrap items-center justify-center gap-2.5">
              <button
                type="button"
                onClick={onClearFiles}
                className="px-4 py-2.5 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-medium transition-colors cursor-pointer inline-flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Clear
              </button>

              {fileCount < MAX_BATCH_FILES && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2.5 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-medium transition-colors cursor-pointer inline-flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add more
                </button>
              )}

              <button
                type="button"
                onClick={onStartAnalysis}
                className="px-7 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-full shadow-lg shadow-emerald-600/25 hover:shadow-xl transition-all duration-200 cursor-pointer inline-flex items-center gap-2 group"
              >
                {fileCount > 1 ? `Analyse ${fileCount} bills` : 'Analyse my bill'}
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/** Rejections are listed, not summarised — the user needs to know which file. */
const ErrorBanner: React.FC<{ problems: string[] }> = ({ problems }) => {
  if (problems.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      className="mb-5 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2 text-left"
    >
      <AlertCircle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
      <ul className="space-y-0.5 min-w-0">
        {problems.map((problem) => (
          <li key={problem} className="break-words">
            {problem}
          </li>
        ))}
      </ul>
    </motion.div>
  );
};
