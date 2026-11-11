import { User } from './common';

export type DocumentType =
  | 'architecture_decision'
  | 'runbook'
  | 'api_spec'
  | 'incident_postmortem'
  | 'credentials_guide'
  | 'slack_export';

export type SupportedFileFormat = 'pdf' | 'docx' | 'txt' | 'md';

export type ProcessingStatus =
  | 'uploaded'
  | 'extracting_text'
  | 'chunking_content'
  | 'indexing'
  | 'ready'
  | 'failed';

export interface DocumentEvidenceLink {
  id: string;
  sourceType: 'github_pr' | 'jira_ticket' | 'slack_thread' | 'confluence' | 'figma';
  externalUrl: string;
  excerpt: string;
  author: string;
  timestamp: string;
}

export interface ProcessingStepLog {
  id: string;
  stage: ProcessingStatus;
  label: string;
  status: 'completed' | 'in_progress' | 'failed' | 'pending';
  timestamp: string;
  detail?: string;
}

export interface KnowledgeSourceDocument {
  id: string;
  fileName: string;
  fileFormat: SupportedFileFormat;
  fileSize: number; // bytes
  fileSizeBytesFormatted: string;
  uploadedAt: string;
  uploadedBy: User;
  projectId: string;
  projectKey: string;
  processingStatus: ProcessingStatus;
  processingProgress: number; // 0 - 100
  pageCount?: number;
  chunkCount?: number;
  wordCount?: number;
  extractedTextPreview?: string;
  fullContent?: string;
  processingLogs: ProcessingStepLog[];
  errorMessage?: string;
  tags: string[];
}

export interface KnowledgeDocument {
  id: string;
  projectId: string;
  title: string;
  type: DocumentType;
  excerpt: string;
  content: string;
  author: User;
  updatedAt: string;
  verificationStatus: 'verified' | 'unverified' | 'conflicting';
  confidenceScore: number; // 0 - 100
  evidenceLinks: DocumentEvidenceLink[];
  tags: string[];
}

export interface UploadQueueItem {
  id: string;
  file: File;
  name: string;
  size: number;
  format: SupportedFileFormat;
  progress: number;
  status: 'validating' | 'uploading' | 'processing' | 'completed' | 'error';
  errorMessage?: string;
}
