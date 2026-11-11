import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UploadCloud,
  FileText,
  FileCode,
  FileSpreadsheet,
  File,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RefreshCw,
  Trash2,
  ExternalLink,
  Sparkles,
  ChevronRight,
  HardDrive,
  FolderGit2,
  X,
  AlertCircle,
  MoreVertical,
  Check,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/common/Card';
import { Input } from '../../components/common/Input';
import { Dropdown } from '../../components/common/Dropdown';
import { DocumentDetailsDrawer } from '../../components/documents/DocumentDetailsDrawer';
import { documentService } from '../../services/documentService';
import { KnowledgeSourceDocument, ProcessingStatus, SupportedFileFormat, UploadQueueItem } from '../../types/document';
import { formatDate, formatFileSize } from '../../utils/formatters';
import { useToast } from '../../hooks/useToast';
import { mockProjects } from '../../data/mockData';

export const DocumentsPage: React.FC = () => {
  const { success, error: toastError, warning, info } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [documents, setDocuments] = useState<KnowledgeSourceDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters & Search
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'processing' | 'ready' | 'failed'>('all');
  const [projectFilter, setProjectFilter] = useState<string>('all');

  // Drag and drop state
  const [isDragOver, setIsDragOver] = useState(false);

  // Active Upload queue
  const [uploadQueue, setUploadQueue] = useState<UploadQueueItem[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Selected document for details drawer
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeSourceDocument | null>(null);

  // Load documents from service
  const loadDocuments = async () => {
    setIsLoading(true);
    const res = await documentService.getAll();
    if (res.data) {
      setDocuments(res.data);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  // Filter documents
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const matchesSearch =
        doc.fileName.toLowerCase().includes(search.toLowerCase()) ||
        doc.projectKey.toLowerCase().includes(search.toLowerCase()) ||
        doc.uploadedBy.name.toLowerCase().includes(search.toLowerCase()) ||
        doc.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()));

      const matchesStatus =
        statusFilter === 'all'
          ? true
          : statusFilter === 'ready'
          ? doc.processingStatus === 'ready'
          : statusFilter === 'failed'
          ? doc.processingStatus === 'failed'
          : ['uploaded', 'extracting_text', 'chunking_content', 'indexing'].includes(doc.processingStatus);

      const matchesProject =
        projectFilter === 'all'
          ? true
          : doc.projectKey.toLowerCase() === projectFilter.toLowerCase();

      return matchesSearch && matchesStatus && matchesProject;
    });
  }, [documents, search, statusFilter, projectFilter]);

  // Handle incoming files from drop or browse
  const handleFilesSelected = async (fileList: FileList | File[]) => {
    setUploadError(null);
    const files = Array.from(fileList);
    if (files.length === 0) return;

    const allowedFormats = ['pdf', 'docx', 'txt', 'md'];

    for (const file of files) {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';

      // Validate format
      if (!allowedFormats.includes(ext)) {
        setUploadError(`Unsupported format "${file.name}". Supported: PDF, DOCX, TXT, MD.`);
        toastError('Invalid File Format', `"${file.name}" is not supported.`);
        continue;
      }

      // Validate size (25MB)
      if (file.size > 25 * 1024 * 1024) {
        setUploadError(`"${file.name}" exceeds maximum allowed file size of 25MB.`);
        toastError('File Too Large', `"${file.name}" exceeds 25MB limit.`);
        continue;
      }

      const queueItem: UploadQueueItem = {
        id: `upload-${Date.now()}-${Math.random().toString(36).substring(7)}`,
        file,
        name: file.name,
        size: file.size,
        format: ext as SupportedFileFormat,
        progress: 10,
        status: 'uploading',
      };

      setUploadQueue((prev) => [queueItem, ...prev]);

      try {
        // Enqueue through isolated document service
        const res = await documentService.uploadFile(
          file,
          'proj-1',
          'PAY-V2',
          (updatedDoc) => {
            // Live update document state in list and drawer
            setDocuments((prevDocs) => {
              const idx = prevDocs.findIndex((d) => d.id === updatedDoc.id);
              if (idx === -1) return [updatedDoc, ...prevDocs];
              const copy = [...prevDocs];
              copy[idx] = updatedDoc;
              return copy;
            });

            setSelectedDoc((current) => (current?.id === updatedDoc.id ? updatedDoc : current));
          }
        );

        if (res.data) {
          // Update queue item
          setUploadQueue((prev) =>
            prev.map((q) =>
              q.id === queueItem.id
                ? { ...q, progress: 100, status: 'completed' }
                : q
            )
          );

          success('File Uploaded', `"${file.name}" enqueued for OCR & text extraction.`);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Upload failed';
        setUploadQueue((prev) =>
          prev.map((q) =>
            q.id === queueItem.id
              ? { ...q, status: 'error', errorMessage: msg }
              : q
          )
        );
        toastError('Upload Error', msg);
      }
    }

    // Clear input
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files) {
      handleFilesSelected(e.dataTransfer.files);
    }
  };

  const handleDelete = async (id: string) => {
    await documentService.deleteDocument(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    success('Document Deleted', 'Knowledge source and embeddings removed.');
  };

  const handleReprocess = async (id: string) => {
    const res = await documentService.reprocessDocument(id, (updatedDoc) => {
      setDocuments((prevDocs) =>
        prevDocs.map((d) => (d.id === updatedDoc.id ? updatedDoc : d))
      );
      setSelectedDoc((current) => (current?.id === updatedDoc.id ? updatedDoc : current));
    });

    if (res.data) {
      info('Re-processing Enqueued', `Extraction restarted for ${res.data.fileName}.`);
    }
  };

  const getFormatIcon = (fmt: string) => {
    switch (fmt) {
      case 'pdf':
        return <FileText className="h-4 w-4 text-rose-400" />;
      case 'docx':
        return <FileSpreadsheet className="h-4 w-4 text-blue-400" />;
      case 'md':
        return <FileCode className="h-4 w-4 text-purple-400" />;
      default:
        return <File className="h-4 w-4 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: ProcessingStatus) => {
    switch (status) {
      case 'ready':
        return <Badge variant="success" size="sm" dot>Ready for analysis</Badge>;
      case 'indexing':
        return <Badge variant="ai" size="sm" dot>Indexing...</Badge>;
      case 'chunking_content':
        return <Badge variant="accent" size="sm" dot>Chunking content...</Badge>;
      case 'extracting_text':
        return <Badge variant="warning" size="sm" dot>Extracting text...</Badge>;
      case 'uploaded':
        return <Badge variant="neutral" size="sm" dot>Uploaded</Badge>;
      case 'failed':
        return <Badge variant="danger" size="sm" dot>Failed</Badge>;
    }
  };

  // Processing counts
  const readyCount = documents.filter((d) => d.processingStatus === 'ready').length;
  const processingCount = documents.filter((d) =>
    ['uploaded', 'extracting_text', 'chunking_content', 'indexing'].includes(d.processingStatus)
  ).length;
  const failedCount = documents.filter((d) => d.processingStatus === 'failed').length;

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* 1. PAGE HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-brand-400 uppercase tracking-wider font-mono">
              Knowledge Ingestion
            </span>
            <Badge variant="ai" size="sm">
              Vector Pipeline
            </Badge>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1">
            Knowledge Sources
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Bring your project knowledge together in one place.
          </p>
        </div>

        {/* Header Metric Badges */}
        <div className="flex items-center gap-2.5">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs flex items-center gap-2">
            <span className="text-slate-400">Total:</span>
            <span className="font-mono font-bold text-white">{documents.length}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs flex items-center gap-2">
            <span className="text-emerald-400">Ready:</span>
            <span className="font-mono font-bold text-emerald-300">{readyCount}</span>
          </div>
          {processingCount > 0 && (
            <div className="px-3 py-1.5 rounded-lg bg-brand-500/10 border border-brand-500/20 text-xs flex items-center gap-2">
              <span className="text-brand-400">Processing:</span>
              <span className="font-mono font-bold text-brand-300">{processingCount}</span>
            </div>
          )}
          {failedCount > 0 && (
            <div className="px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs flex items-center gap-2">
              <span className="text-rose-400">Failed:</span>
              <span className="font-mono font-bold text-rose-300">{failedCount}</span>
            </div>
          )}
        </div>
      </div>

      {/* 2. UPLOAD AREA (Drag & Drop Zone) */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative rounded-2xl border-2 border-dashed p-6 sm:p-8 text-center transition-all duration-200 ${
          isDragOver
            ? 'border-brand-500 bg-brand-500/10 shadow-glow'
            : 'border-slate-800 hover:border-slate-700 bg-[#0F172A]/70'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md"
          onChange={(e) => e.target.files && handleFilesSelected(e.target.files)}
          className="hidden"
        />

        <div className="max-w-md mx-auto space-y-3">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-brand-600/30 to-purple-600/30 border border-brand-500/30 text-brand-300 flex items-center justify-center mx-auto shadow-sm">
            <UploadCloud className="h-6 w-6" />
          </div>

          <div>
            <h3 className="text-sm font-semibold text-white">
              Drag and drop project documents here, or{' '}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="text-brand-400 hover:text-brand-300 underline underline-offset-2 font-semibold"
              >
                browse files
              </button>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Supports <strong className="text-slate-300">PDF</strong>, <strong className="text-slate-300">DOCX</strong>, <strong className="text-slate-300">TXT</strong>, and <strong className="text-slate-300">Markdown</strong> files up to 25MB each.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2 pt-1 text-[11px] text-slate-500">
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">.PDF (OCR extracted)</span>
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">.DOCX (Word runbooks)</span>
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">.MD (Architecture decisions)</span>
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">.TXT (Config manifests)</span>
          </div>
        </div>

        {uploadError && (
          <div className="mt-4 max-w-md mx-auto p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{uploadError}</span>
            </div>
            <button onClick={() => setUploadError(null)} className="text-rose-400 hover:text-rose-200">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Upload Progress Queue Cards */}
      {uploadQueue.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Recent Upload Tasks ({uploadQueue.length})</span>
            <button
              onClick={() => setUploadQueue([])}
              className="text-[11px] text-slate-500 hover:text-slate-300"
            >
              Clear Completed
            </button>
          </div>

          <div className="space-y-2">
            {uploadQueue.map((item) => (
              <div
                key={item.id}
                className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {getFormatIcon(item.format)}
                  <div className="truncate">
                    <div className="font-semibold text-white truncate">{item.name}</div>
                    <div className="text-[11px] text-slate-500 font-mono">
                      {formatFileSize(item.size)}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {item.status === 'uploading' && (
                    <div className="flex items-center gap-2 text-brand-400 text-[11px]">
                      <div className="h-3.5 w-3.5 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
                      <span>Enqueuing...</span>
                    </div>
                  )}

                  {item.status === 'completed' && (
                    <span className="text-emerald-400 text-[11px] font-semibold flex items-center gap-1">
                      <Check className="h-3.5 w-3.5" /> Enqueued
                    </span>
                  )}

                  {item.status === 'error' && (
                    <span className="text-rose-400 text-[11px] font-semibold flex items-center gap-1">
                      <AlertCircle className="h-3.5 w-3.5" /> Failed
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3 & 6. FILTERS AND DOCUMENT LIBRARY */}
      <div className="space-y-4">
        {/* Controls Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Search */}
          <div className="flex-1 max-w-md">
            <Input
              placeholder="Search documents by name, author, workspace, or keyword..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              leftIcon={<Search className="h-3.5 w-3.5" />}
              className="h-9 text-xs"
            />
          </div>

          {/* Status Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 p-0.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
              {[
                { id: 'all', label: 'All Documents' },
                { id: 'processing', label: 'Processing' },
                { id: 'ready', label: 'Ready' },
                { id: 'failed', label: 'Failed' },
              ].map((st) => (
                <button
                  key={st.id}
                  onClick={() => setStatusFilter(st.id as any)}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                    statusFilter === st.id
                      ? 'bg-slate-800 text-white font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {st.label}
                </button>
              ))}
            </div>

            {/* Project Filter */}
            <select
              value={projectFilter}
              onChange={(e) => setProjectFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none cursor-pointer"
            >
              <option value="all">All Projects</option>
              {mockProjects.map((p) => (
                <option key={p.id} value={p.key}>
                  {p.key} ({p.title.substring(0, 18)}...)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 7. EMPTY STATE */}
        {filteredDocuments.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-[#0F172A] border border-slate-800 space-y-4">
            <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-brand-600/20 to-purple-600/20 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto shadow-sm">
              <FileText className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-white">No knowledge sources found</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                {search || statusFilter !== 'all' || projectFilter !== 'all'
                  ? 'No documents matched your active search or filters.'
                  : 'Start by uploading runbooks, architecture decision records (ADRs), or credentials guides.'}
              </p>
            </div>
            <div className="flex items-center justify-center gap-3 pt-2">
              {(search || statusFilter !== 'all' || projectFilter !== 'all') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearch('');
                    setStatusFilter('all');
                    setProjectFilter('all');
                  }}
                  className="text-xs"
                >
                  Reset Filters
                </Button>
              )}
              <Button
                variant="primary"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                leftIcon={<UploadCloud className="h-4 w-4" />}
                className="text-xs"
              >
                Upload Documents
              </Button>
            </div>
          </div>
        ) : (
          /* DOCUMENT LIBRARY TABLE */
          <div className="overflow-hidden rounded-xl border border-slate-800 bg-[#0F172A]">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
                    <th className="px-5 py-3.5">File Name & Format</th>
                    <th className="px-5 py-3.5">Workspace</th>
                    <th className="px-5 py-3.5">Uploaded By</th>
                    <th className="px-5 py-3.5">Upload Date</th>
                    <th className="px-5 py-3.5">File Size</th>
                    <th className="px-5 py-3.5">Processing Status</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {filteredDocuments.map((doc) => (
                    <tr
                      key={doc.id}
                      onClick={() => setSelectedDoc(doc)}
                      className="hover:bg-slate-800/40 transition-colors cursor-pointer group"
                    >
                      {/* Name & Icon */}
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center shrink-0 group-hover:border-slate-700">
                            {getFormatIcon(doc.fileFormat)}
                          </div>
                          <div className="min-w-0">
                            <div className="font-semibold text-white group-hover:text-brand-300 transition-colors truncate max-w-xs sm:max-w-sm">
                              {doc.fileName}
                            </div>
                            <div className="text-[10px] text-slate-500 uppercase font-mono mt-0.5">
                              {doc.fileFormat} File {doc.pageCount ? `· ${doc.pageCount} Pages` : ''}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Workspace Key */}
                      <td className="px-5 py-4">
                        <span className="font-mono text-xs font-bold text-brand-400">
                          {doc.projectKey}
                        </span>
                      </td>

                      {/* Uploaded By */}
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <img
                            src={doc.uploadedBy.avatarUrl}
                            alt={doc.uploadedBy.name}
                            className="h-5 w-5 rounded-full object-cover"
                          />
                          <span className="text-slate-200 text-xs">{doc.uploadedBy.name}</span>
                        </div>
                      </td>

                      {/* Date */}
                      <td className="px-5 py-4 text-slate-400 font-mono text-[11px]">
                        {formatDate(doc.uploadedAt)}
                      </td>

                      {/* Size */}
                      <td className="px-5 py-4 font-mono text-slate-300 text-[11px]">
                        {doc.fileSizeBytesFormatted}
                      </td>

                      {/* Status */}
                      <td className="px-5 py-4">
                        <div className="space-y-1">
                          {getStatusBadge(doc.processingStatus)}
                          {doc.processingStatus !== 'ready' && doc.processingStatus !== 'failed' && (
                            <div className="w-20 bg-slate-800 h-1 rounded-full overflow-hidden mt-1">
                              <div
                                className="bg-brand-500 h-full rounded-full transition-all duration-300"
                                style={{ width: `${doc.processingProgress}%` }}
                              />
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="px-5 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <Dropdown
                          trigger={
                            <button
                              type="button"
                              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                            >
                              <MoreVertical className="h-4 w-4" />
                            </button>
                          }
                          items={[
                            {
                              id: 'view',
                              label: 'View Details & Preview',
                              icon: <FileText className="h-3.5 w-3.5" />,
                              onClick: () => setSelectedDoc(doc),
                            },
                            {
                              id: 'reprocess',
                              label: 'Re-process File',
                              icon: <RefreshCw className="h-3.5 w-3.5" />,
                              onClick: () => handleReprocess(doc.id),
                            },
                            {
                              id: 'div',
                              label: '',
                              divider: true,
                            },
                            {
                              id: 'delete',
                              label: 'Delete Document',
                              danger: true,
                              icon: <Trash2 className="h-3.5 w-3.5" />,
                              onClick: () => handleDelete(doc.id),
                            },
                          ]}
                          align="right"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* 5. DOCUMENT DETAILS DRAWER */}
      <DocumentDetailsDrawer
        document={selectedDoc}
        isOpen={Boolean(selectedDoc)}
        onClose={() => setSelectedDoc(null)}
        onDelete={handleDelete}
        onReprocess={handleReprocess}
      />
    </div>
  );
};
