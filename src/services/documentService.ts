/**
 * Isolated Document Service for Knowledge Handover Platform.
 * 
 * BACKEND INTEGRATION NOTE:
 * When connecting to the FastAPI backend, set USE_MOCK = false in apiClient.ts or configure
 * VITE_API_URL. The endpoints mirror standard REST contracts:
 * - GET    /api/v1/documents             -> List all documents with filters
 * - GET    /api/v1/documents/{id}        -> Get document details, logs, and extracted text
 * - POST   /api/v1/documents/upload      -> Multipart/form-data upload
 * - POST   /api/v1/documents/{id}/retry  -> Trigger re-processing pipeline
 * - DELETE /api/v1/documents/{id}        -> Delete document & vector embeddings
 */

import { apiClient, ApiResponse } from './apiClient';
import {
  KnowledgeSourceDocument,
  SupportedFileFormat,
  ProcessingStatus,
  ProcessingStepLog,
} from '../types/document';
import { mockKnowledgeSources } from '../data/mockKnowledgeSources';
import { mockCurrentUser } from '../data/mockData';
import { formatFileSize } from '../utils/formatters';

const STORAGE_KEY = 'kh_knowledge_sources_store';

function loadSourcesFromStorage(): KnowledgeSourceDocument[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(mockKnowledgeSources));
      return [...mockKnowledgeSources];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : [...mockKnowledgeSources];
  } catch {
    return [...mockKnowledgeSources];
  }
}

function saveSourcesToStorage(sources: KnowledgeSourceDocument[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sources));
  } catch (err) {
    console.warn('Failed to persist knowledge sources:', err);
  }
}

class DocumentService {
  /**
   * Fetch all knowledge sources
   */
  async getAll(): Promise<ApiResponse<KnowledgeSourceDocument[]>> {
    return apiClient.executeMock(() => {
      return loadSourcesFromStorage();
    });
  }

  /**
   * Fetch single document by ID
   */
  async getById(id: string): Promise<ApiResponse<KnowledgeSourceDocument | undefined>> {
    return apiClient.executeMock(() => {
      const docs = loadSourcesFromStorage();
      return docs.find((d) => d.id === id);
    });
  }

  /**
   * Upload and process a new document through the AI extraction pipeline:
   * uploaded -> extracting_text -> chunking_content -> indexing -> ready
   */
  async uploadFile(
    file: File,
    projectId: string = 'proj-1',
    projectKey: string = 'PAY-V2',
    onProgressUpdate?: (doc: KnowledgeSourceDocument) => void
  ): Promise<ApiResponse<KnowledgeSourceDocument>> {
    return apiClient.executeMock(async () => {
      // 1. Validation: File extension check
      const ext = file.name.split('.').pop()?.toLowerCase() as SupportedFileFormat;
      const validExtensions: SupportedFileFormat[] = ['pdf', 'docx', 'txt', 'md'];

      if (!validExtensions.includes(ext)) {
        throw new Error(
          `Unsupported file format ".${ext}". Only PDF, DOCX, TXT, and Markdown files are supported.`
        );
      }

      // 2. Validation: Max size check (25 MB)
      const MAX_SIZE_BYTES = 25 * 1024 * 1024;
      if (file.size > MAX_SIZE_BYTES) {
        throw new Error(
          `File size (${formatFileSize(file.size)}) exceeds the maximum allowed limit of 25MB.`
        );
      }

      // Initial Document State: "uploaded"
      // (Note: We explicitly DO NOT claim files are AI-analyzed when uploaded)
      const nowStr = new Date().toISOString();
      const initialDoc: KnowledgeSourceDocument = {
        id: `src-doc-${Date.now()}-${Math.random().toString(36).substring(7)}`,
        fileName: file.name,
        fileFormat: ext,
        fileSize: file.size,
        fileSizeBytesFormatted: formatFileSize(file.size),
        uploadedAt: nowStr,
        uploadedBy: mockCurrentUser,
        projectId,
        projectKey,
        processingStatus: 'uploaded',
        processingProgress: 15,
        pageCount: ext === 'pdf' ? Math.max(1, Math.round(file.size / 150000)) : undefined,
        chunkCount: 0,
        wordCount: Math.round(file.size / 6),
        extractedTextPreview: `[Ingesting raw ${ext.toUpperCase()} stream for ${file.name}...]`,
        tags: [ext.toUpperCase(), 'Uploaded'],
        processingLogs: [
          {
            id: `log-init-${Date.now()}`,
            stage: 'uploaded',
            label: 'File uploaded and integrity validated',
            status: 'completed',
            timestamp: new Date().toLocaleTimeString(),
            detail: `Received ${formatFileSize(file.size)} archive. Enqueued for OCR and text extraction.`,
          },
          {
            id: `log-extract-${Date.now()}`,
            stage: 'extracting_text',
            label: 'Text and AST Extraction',
            status: 'pending',
            timestamp: 'Pending',
          },
          {
            id: `log-chunk-${Date.now()}`,
            stage: 'chunking_content',
            label: 'Semantic Content Chunking',
            status: 'pending',
            timestamp: 'Pending',
          },
          {
            id: `log-index-${Date.now()}`,
            stage: 'indexing',
            label: 'Dense Vector Embeddings & Lexical Index',
            status: 'pending',
            timestamp: 'Pending',
          },
          {
            id: `log-ready-${Date.now()}`,
            stage: 'ready',
            label: 'Ready for AI continuity analysis',
            status: 'pending',
            timestamp: 'Pending',
          },
        ],
      };

      // Add to store
      const docs = loadSourcesFromStorage();
      docs.unshift(initialDoc);
      saveSourcesToStorage(docs);
      onProgressUpdate?.(initialDoc);

      // Trigger asynchronous pipeline transitions in background simulation
      this.simulatePipelineExecution(initialDoc.id, onProgressUpdate);

      return initialDoc;
    });
  }

  /**
   * Simulates the multi-step background processing lifecycle:
   * extracting_text (35%) -> chunking_content (65%) -> indexing (85%) -> ready (100%)
   */
  private async simulatePipelineExecution(
    docId: string,
    onProgressUpdate?: (doc: KnowledgeSourceDocument) => void
  ) {
    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    // STAGE 2: extracting_text (1.5s)
    await delay(1500);
    let docs = loadSourcesFromStorage();
    let doc = docs.find((d) => d.id === docId);
    if (!doc) return;

    doc.processingStatus = 'extracting_text';
    doc.processingProgress = 35;
    doc.processingLogs[1] = {
      ...doc.processingLogs[1],
      status: 'in_progress',
      timestamp: new Date().toLocaleTimeString(),
      detail: `Parsing ${doc.fileFormat.toUpperCase()} structure and extracting headers, tables, and code snippets...`,
    };
    saveSourcesToStorage(docs);
    onProgressUpdate?.({ ...doc });

    // STAGE 3: chunking_content (1.8s)
    await delay(1800);
    docs = loadSourcesFromStorage();
    doc = docs.find((d) => d.id === docId);
    if (!doc) return;

    doc.processingStatus = 'chunking_content';
    doc.processingProgress = 65;
    const estChunks = Math.max(4, Math.round(doc.fileSize / 80000));
    doc.chunkCount = estChunks;
    doc.processingLogs[1].status = 'completed';
    doc.processingLogs[2] = {
      ...doc.processingLogs[2],
      status: 'in_progress',
      timestamp: new Date().toLocaleTimeString(),
      detail: `Partitioned document into ${estChunks} semantic sections (512 token chunks with 64 overlap).`,
    };
    saveSourcesToStorage(docs);
    onProgressUpdate?.({ ...doc });

    // STAGE 4: indexing (2.0s)
    await delay(2000);
    docs = loadSourcesFromStorage();
    doc = docs.find((d) => d.id === docId);
    if (!doc) return;

    doc.processingStatus = 'indexing';
    doc.processingProgress = 85;
    doc.processingLogs[2].status = 'completed';
    doc.processingLogs[3] = {
      ...doc.processingLogs[3],
      status: 'in_progress',
      timestamp: new Date().toLocaleTimeString(),
      detail: `Generating high-dimensional embeddings and indexing into vector database namespace (${doc.projectKey.toLowerCase()})...`,
    };
    saveSourcesToStorage(docs);
    onProgressUpdate?.({ ...doc });

    // STAGE 5: ready (1.5s)
    await delay(1500);
    docs = loadSourcesFromStorage();
    doc = docs.find((d) => d.id === docId);
    if (!doc) return;

    doc.processingStatus = 'ready';
    doc.processingProgress = 100;
    doc.extractedTextPreview = `# ${doc.fileName.replace(/\.[^/.]+$/, '').replace(/_/g, ' ')}\n\n## Abstract\nSuccessfully ingested and indexed source knowledge for project ${doc.projectKey}. Content has been partitioned into ${doc.chunkCount} searchable semantic chunks and linked to the repository continuity graph.\n\n## Key Architectural Points\n- Complete document structure parsed and validated.\n- All security parameters and operational commands verified for evidence cross-referencing.\n- Ready for AI handover synthesis and automated gap detection queries.`;
    doc.processingLogs[3].status = 'completed';
    doc.processingLogs[4] = {
      ...doc.processingLogs[4],
      status: 'completed',
      timestamp: new Date().toLocaleTimeString(),
      detail: 'Indexing complete. Document is now fully ready for knowledge continuity analysis.',
    };
    saveSourcesToStorage(docs);
    onProgressUpdate?.({ ...doc });
  }

  /**
   * Re-process a failed or pending document
   */
  async reprocessDocument(
    id: string,
    onProgressUpdate?: (doc: KnowledgeSourceDocument) => void
  ): Promise<ApiResponse<KnowledgeSourceDocument>> {
    return apiClient.executeMock(() => {
      const docs = loadSourcesFromStorage();
      const doc = docs.find((d) => d.id === id);
      if (!doc) throw new Error('Document not found');

      doc.processingStatus = 'extracting_text';
      doc.processingProgress = 25;
      doc.errorMessage = undefined;
      doc.processingLogs = [
        {
          id: `log-retry-${Date.now()}`,
          stage: 'extracting_text',
          label: 'Manual re-processing triggered',
          status: 'in_progress',
          timestamp: new Date().toLocaleTimeString(),
          detail: 'Pipeline restarted with fallback text extraction engines.',
        },
      ];

      saveSourcesToStorage(docs);
      this.simulatePipelineExecution(doc.id, onProgressUpdate);

      return doc;
    });
  }

  /**
   * Delete a document and its embeddings
   */
  async deleteDocument(id: string): Promise<ApiResponse<boolean>> {
    return apiClient.executeMock(() => {
      const docs = loadSourcesFromStorage();
      const filtered = docs.filter((d) => d.id !== id);
      saveSourcesToStorage(filtered);
      return true;
    });
  }
}

export const documentService = new DocumentService();
