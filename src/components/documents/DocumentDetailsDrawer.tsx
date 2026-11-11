import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  FileText,
  Calendar,
  User as UserIcon,
  FolderGit2,
  HardDrive,
  Copy,
  Check,
  RefreshCw,
  Trash2,
  AlertTriangle,
  Sparkles,
  Layers,
  FileCode,
  ShieldCheck,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import { KnowledgeSourceDocument, ProcessingStatus } from '../../types/document';
import { formatDate } from '../../utils/formatters';
import { useToast } from '../../hooks/useToast';

export interface DocumentDetailsDrawerProps {
  document: KnowledgeSourceDocument | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete: (id: string) => void;
  onReprocess: (id: string) => void;
}

export const DocumentDetailsDrawer: React.FC<DocumentDetailsDrawerProps> = ({
  document,
  isOpen,
  onClose,
  onDelete,
  onReprocess,
}) => {
  const { success } = useToast();
  const [copied, setCopied] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  if (!document) return null;

  const handleCopyText = () => {
    if (document.extractedTextPreview) {
      navigator.clipboard.writeText(document.extractedTextPreview);
      setCopied(true);
      success('Copied to Clipboard', 'Extracted text preview copied.');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getFormatBadge = (fmt: string) => {
    switch (fmt) {
      case 'pdf':
        return <Badge variant="danger" size="sm">PDF</Badge>;
      case 'docx':
        return <Badge variant="accent" size="sm">DOCX</Badge>;
      case 'md':
        return <Badge variant="ai" size="sm">MARKDOWN</Badge>;
      case 'txt':
        return <Badge variant="neutral" size="sm">TXT</Badge>;
      default:
        return <Badge variant="default" size="sm">{fmt.toUpperCase()}</Badge>;
    }
  };

  const getStatusBadge = (status: ProcessingStatus) => {
    switch (status) {
      case 'ready':
        return <Badge variant="success" size="sm" dot>Ready for Analysis</Badge>;
      case 'indexing':
        return <Badge variant="ai" size="sm" dot>Indexing Content</Badge>;
      case 'chunking_content':
        return <Badge variant="accent" size="sm" dot>Chunking Content</Badge>;
      case 'extracting_text':
        return <Badge variant="warning" size="sm" dot>Extracting Text</Badge>;
      case 'uploaded':
        return <Badge variant="neutral" size="sm" dot>Uploaded</Badge>;
      case 'failed':
        return <Badge variant="danger" size="sm" dot>Processing Failed</Badge>;
    }
  };

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm"
              onClick={onClose}
            />

            {/* Slide-over Drawer */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 300 }}
              className="relative w-full max-w-xl h-full bg-[#0B101D] border-l border-slate-800 shadow-2xl flex flex-col z-10 overflow-hidden text-slate-100"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Drawer Header */}
              <div className="p-5 border-b border-slate-800/80 bg-[#080C14] flex items-start justify-between gap-4">
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2">
                    {getFormatBadge(document.fileFormat)}
                    <span className="font-mono text-xs font-semibold text-brand-400">
                      {document.projectKey}
                    </span>
                    {getStatusBadge(document.processingStatus)}
                  </div>
                  <h2 className="text-base font-bold text-white tracking-tight truncate">
                    {document.fileName}
                  </h2>
                </div>

                <button
                  onClick={onClose}
                  className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Drawer Scrollable Body */}
              <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs">
                {/* Error Banner if Failed */}
                {document.processingStatus === 'failed' && (
                  <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 space-y-2">
                    <div className="flex items-center gap-2 font-semibold text-rose-200">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Document Extraction Error</span>
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      {document.errorMessage || 'Unknown error occurred while parsing the document AST.'}
                    </p>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => onReprocess(document.id)}
                      leftIcon={<RefreshCw className="h-3 w-3" />}
                      className="text-xs h-7 mt-1"
                    >
                      Retry Extraction Pipeline
                    </Button>
                  </div>
                )}

                {/* Progress Overview */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-medium">Pipeline Progress</span>
                    <span className="font-mono font-bold text-white">
                      {document.processingProgress}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        document.processingStatus === 'failed'
                          ? 'bg-rose-500'
                          : document.processingStatus === 'ready'
                          ? 'bg-emerald-400'
                          : 'bg-brand-500'
                      }`}
                      style={{ width: `${document.processingProgress}%` }}
                    />
                  </div>
                </div>

                {/* File Metadata Grid */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                  <h3 className="font-semibold text-white flex items-center gap-1.5 text-xs">
                    <HardDrive className="h-3.5 w-3.5 text-brand-400" />
                    <span>File Metadata</span>
                  </h3>

                  <div className="grid grid-cols-2 gap-3 text-slate-400">
                    <div>
                      <span className="block text-[11px] text-slate-500">File Size</span>
                      <span className="text-slate-200 font-mono font-medium">
                        {document.fileSizeBytesFormatted}
                      </span>
                    </div>

                    <div>
                      <span className="block text-[11px] text-slate-500">Upload Date</span>
                      <span className="text-slate-200 font-medium">
                        {formatDate(document.uploadedAt)}
                      </span>
                    </div>

                    <div>
                      <span className="block text-[11px] text-slate-500">Uploaded By</span>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <img
                          src={document.uploadedBy.avatarUrl}
                          alt={document.uploadedBy.name}
                          className="h-4 w-4 rounded-full object-cover"
                        />
                        <span className="text-slate-200 font-medium">{document.uploadedBy.name}</span>
                      </div>
                    </div>

                    <div>
                      <span className="block text-[11px] text-slate-500">Project Workspace</span>
                      <span className="font-mono font-semibold text-brand-300">
                        {document.projectKey}
                      </span>
                    </div>

                    {document.pageCount && (
                      <div>
                        <span className="block text-[11px] text-slate-500">Page Count</span>
                        <span className="text-slate-200 font-mono font-medium">
                          {document.pageCount} Pages
                        </span>
                      </div>
                    )}

                    {document.chunkCount !== undefined && (
                      <div>
                        <span className="block text-[11px] text-slate-500">Semantic Chunks</span>
                        <span className="text-slate-200 font-mono font-medium">
                          {document.chunkCount} Chunks
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Extracted Text Preview */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-white flex items-center gap-1.5 text-xs">
                      <FileCode className="h-3.5 w-3.5 text-indigo-400" />
                      <span>Extracted Content Preview</span>
                    </h3>
                    <button
                      type="button"
                      onClick={handleCopyText}
                      className="text-brand-400 hover:text-brand-300 inline-flex items-center gap-1 text-[11px] font-medium"
                    >
                      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      <span>{copied ? 'Copied' : 'Copy Text'}</span>
                    </button>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-[11px] leading-relaxed text-slate-300 max-h-64 overflow-y-auto whitespace-pre-wrap select-text">
                    {document.extractedTextPreview || 'No extracted text available yet.'}
                  </div>
                </div>

                {/* Processing History / Audit Logs */}
                <div className="space-y-2.5">
                  <h3 className="font-semibold text-white flex items-center gap-1.5 text-xs">
                    <Clock className="h-3.5 w-3.5 text-amber-400" />
                    <span>Processing Pipeline History</span>
                  </h3>

                  <div className="space-y-2 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
                    {document.processingLogs.map((log) => (
                      <div key={log.id} className="flex items-start gap-2.5 text-xs">
                        <div className="mt-0.5 shrink-0">
                          {log.status === 'completed' ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                          ) : log.status === 'in_progress' ? (
                            <div className="h-4 w-4 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
                          ) : log.status === 'failed' ? (
                            <AlertCircle className="h-4 w-4 text-rose-400" />
                          ) : (
                            <div className="h-4 w-4 rounded-full border border-slate-700 bg-slate-800" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-slate-200">{log.label}</span>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {log.timestamp}
                            </span>
                          </div>
                          {log.detail && (
                            <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                              {log.detail}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Drawer Footer Actions */}
              <div className="p-4 border-t border-slate-800 bg-[#080C14] flex items-center justify-between">
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => setIsDeleteModalOpen(true)}
                  leftIcon={<Trash2 className="h-3.5 w-3.5" />}
                  className="text-xs"
                >
                  Delete Document
                </Button>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onReprocess(document.id)}
                    leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
                    className="text-xs"
                  >
                    Re-Process
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={onClose}
                    className="text-xs"
                  >
                    Close
                  </Button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Confirm Document Deletion"
        description="Are you sure you want to remove this knowledge source and purge its embeddings?"
        footer={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsDeleteModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => {
                onDelete(document.id);
                setIsDeleteModalOpen(false);
                onClose();
              }}
            >
              Confirm Delete
            </Button>
          </>
        }
      >
        <p className="text-xs text-slate-300 leading-relaxed">
          This action will permanently delete <strong className="text-white">{document.fileName}</strong>, its semantic chunk vectors, and any associated AI continuity references from workspace <strong className="font-mono text-brand-400">{document.projectKey}</strong>.
        </p>
      </Modal>
    </>
  );
};
