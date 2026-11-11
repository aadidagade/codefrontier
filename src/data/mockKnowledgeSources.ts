import { KnowledgeSourceDocument, ProcessingStepLog } from '../types/document';
import { mockUsers } from './mockData';

export const mockKnowledgeSources: KnowledgeSourceDocument[] = [
  {
    id: 'src-doc-1',
    fileName: 'ADR-014_Zero_Downtime_Circuit_Breaker.pdf',
    fileFormat: 'pdf',
    fileSize: 1887436, // ~1.8 MB
    fileSizeBytesFormatted: '1.8 MB',
    uploadedAt: '2026-11-06T14:20:00Z',
    uploadedBy: mockUsers[0], // Elena Rostova
    projectId: 'proj-1',
    projectKey: 'PAY-V2',
    processingStatus: 'ready',
    processingProgress: 100,
    pageCount: 14,
    chunkCount: 28,
    wordCount: 4820,
    extractedTextPreview: `# ADR-014: Zero-downtime PSP Circuit Breaker Implementation

## Status
Accepted and verified in production staging.

## Context
High-throughput payment gateway routing with zero-downtime failover across Stripe, Adyen, and regional processors. Under peak transactions (50,000 requests/second), upstream payment service provider latency degradation causes cascade connection starvation in our API gateway pool.

## Decision
We decouple provider failover from client-layer retries by implementing dynamic circuit breakers inside Envoy sidecars, synced through a cluster-replicated Redis state store with 50ms TTL heartbeat checks.

## Gotchas & Operational Mitigations
1. PSP webhook signature rotates every 90 days. KMS automated rotation lambda must be invoked with staging alias.
2. Redis circuit breaker trip threshold is configured at 8% error rate over a 10-second rolling sliding window.
3. Fallback routing will bypass Stripe UK directly to Adyen EU without customer re-authentication.`,
    tags: ['Architecture', 'ADR', 'Envoy', 'Payments'],
    processingLogs: [
      {
        id: 'log-1',
        stage: 'uploaded',
        label: 'File uploaded and signature verified',
        status: 'completed',
        timestamp: '2026-11-06 14:20:05',
        detail: 'SHA-256 integrity hash: 8f9b2...e1a',
      },
      {
        id: 'log-2',
        stage: 'extracting_text',
        label: 'PDF Optical Text Extraction',
        status: 'completed',
        timestamp: '2026-11-06 14:20:12',
        detail: '14 pages parsed with OCR confidence 99.4%',
      },
      {
        id: 'log-3',
        stage: 'chunking_content',
        label: 'Semantic Markdown Chunking',
        status: 'completed',
        timestamp: '2026-11-06 14:20:18',
        detail: 'Generated 28 semantic chunks (512 tokens with 64 token overlap)',
      },
      {
        id: 'log-4',
        stage: 'indexing',
        label: 'Dense Vector Embedding & Metadata Indexing',
        status: 'completed',
        timestamp: '2026-11-06 14:20:25',
        detail: 'Vectors stored in Qdrant namespace: pay-v2-knowledge',
      },
      {
        id: 'log-5',
        stage: 'ready',
        label: 'Indexed and ready for handover synthesis',
        status: 'completed',
        timestamp: '2026-11-06 14:20:30',
        detail: 'Available for AI continuity queries and evidence citation',
      },
    ],
  },
  {
    id: 'src-doc-2',
    fileName: 'Payment_Settlement_Runbook_3AM_Escalation.docx',
    fileFormat: 'docx',
    fileSize: 3355443, // ~3.2 MB
    fileSizeBytesFormatted: '3.2 MB',
    uploadedAt: '2026-11-08T09:15:00Z',
    uploadedBy: mockUsers[1], // David Chen
    projectId: 'proj-1',
    projectKey: 'PAY-V2',
    processingStatus: 'ready',
    processingProgress: 100,
    pageCount: 22,
    chunkCount: 42,
    wordCount: 7150,
    extractedTextPreview: `# Payment Settlement Runbook & Emergency Drain Protocol

## Primary Escalation Tree
- On-Call Level 1: Core Payments PagerDuty Schedule
- Primary Incident Commander: Elena Rostova (@elena.rostova)
- Secondary On-Call: David Chen (@david.chen)
- Bridge Channel: #incident-payments-sev1

## Automated Batch Failure Protocol (HTTP 502 / Socket Timeout)
If batch reconciliation with Barclays Clearing House hangs for more than 180 seconds:
\`\`\`bash
# 1. Connect to payments bastion
ssh bastion-staging.payments.internal

# 2. Check Kafka lag on settlement topic
kafka-consumer-groups --bootstrap-server kafka:9092 --describe --group settlement-worker-v2

# 3. Trigger emergency partition drain
kubectl exec -it deployment/settlement-drain-worker -n payments -- ./drain --force-flush --batch-window=15m
\`\`\`

## Shadow Crons Warning
Three background batch reconciliation cron jobs run at 02:30 UTC directly on the staging shell. Check cron profiles in /etc/cron.d/reconcile-daily.`,
    tags: ['Runbook', 'Settlements', 'OnCall', 'IncidentOps'],
    processingLogs: [
      {
        id: 'log-21',
        stage: 'uploaded',
        label: 'File uploaded',
        status: 'completed',
        timestamp: '2026-11-08 09:15:01',
        detail: 'Received 3.2 MB DOCX archive',
      },
      {
        id: 'log-22',
        stage: 'extracting_text',
        label: 'DOCX XML AST Extraction',
        status: 'completed',
        timestamp: '2026-11-08 09:15:06',
        detail: 'Extracted 22 pages, 14 code blocks, 3 tables',
      },
      {
        id: 'log-23',
        stage: 'chunking_content',
        label: 'Semantic chunking by operational sections',
        status: 'completed',
        timestamp: '2026-11-08 09:15:11',
        detail: '42 chunks generated',
      },
      {
        id: 'log-24',
        stage: 'indexing',
        label: 'Vector embeddings created',
        status: 'completed',
        timestamp: '2026-11-08 09:15:17',
        detail: 'Indexed with hybrid BM25 lexical keywords',
      },
      {
        id: 'log-25',
        stage: 'ready',
        label: 'Ready for analysis',
        status: 'completed',
        timestamp: '2026-11-08 09:15:20',
        detail: 'Runbook verified and cited in handover checklist',
      },
    ],
  },
  {
    id: 'src-doc-3',
    fileName: 'Production_Infrastructure_Secrets_Audit.md',
    fileFormat: 'md',
    fileSize: 491520, // ~480 KB
    fileSizeBytesFormatted: '480 KB',
    uploadedAt: '2026-11-09T22:10:00Z',
    uploadedBy: mockUsers[2], // Sarah Jenkins
    projectId: 'proj-1',
    projectKey: 'PAY-V2',
    processingStatus: 'chunking_content',
    processingProgress: 55,
    pageCount: 6,
    chunkCount: 12,
    wordCount: 2100,
    extractedTextPreview: `# Production Infrastructure Secrets & KMS Vault Audit

## Vault Architecture
All production credentials rotate under HashiCorp Vault cluster \`vault.internal.techfrontier.io\` integrated with AWS KMS Envelope Encryption.

### Outgoing Lead Key Handover Matrix:
- Stripe Production Secret Key: \`secret/data/payments/stripe/live\`
- Adyen Merchant Account Credentials: \`secret/data/payments/adyen/emea\`
- Barclays Corporate BACS Certificate: \`secret/data/payments/banking/barclays-2026\`

### Notice:
Do not commit raw API keys to repository. Use 1Password CLI \`op read op://Vault/Stripe/secret_key\` during local integration tests.`,
    tags: ['Security', 'Vault', 'Secrets', 'KMS'],
    processingLogs: [
      {
        id: 'log-31',
        stage: 'uploaded',
        label: 'File uploaded',
        status: 'completed',
        timestamp: '2026-11-09 22:10:02',
        detail: 'Markdown source parsed',
      },
      {
        id: 'log-32',
        stage: 'extracting_text',
        label: 'Syntax parsing and secret redaction',
        status: 'completed',
        timestamp: '2026-11-09 22:10:08',
        detail: 'Identified 8 vault paths and 3 rotation schedules',
      },
      {
        id: 'log-33',
        stage: 'chunking_content',
        label: 'Chunking content for vector graph...',
        status: 'in_progress',
        timestamp: '2026-11-09 22:10:14',
        detail: 'Splitting secrets audit into secure contextual passages (55%)',
      },
      {
        id: 'log-34',
        stage: 'indexing',
        label: 'Pending embedding generation',
        status: 'pending',
        timestamp: 'Pending',
      },
      {
        id: 'log-35',
        stage: 'ready',
        label: 'Pending readiness',
        status: 'pending',
        timestamp: 'Pending',
      },
    ],
  },
  {
    id: 'src-doc-4',
    fileName: 'Kafka_Partitioning_and_DeadLetter_Config.txt',
    fileFormat: 'txt',
    fileSize: 143360, // ~140 KB
    fileSizeBytesFormatted: '140 KB',
    uploadedAt: '2026-11-09T22:25:00Z',
    uploadedBy: mockUsers[3], // Marcus Vance
    projectId: 'proj-5',
    projectKey: 'STREAM-CORE',
    processingStatus: 'extracting_text',
    processingProgress: 30,
    pageCount: 3,
    chunkCount: 0,
    wordCount: 890,
    extractedTextPreview: `[EVENT-STREAMING CONFIGURATION SPECIFICATION]
Topic Name: telemetry.events.raw.v1
Partition Count: 48
Replication Factor: 3
Cleanup Policy: delete
Retention Bytes: 536870912000 (500GB)
Compression: zstd
Idempotent Producer Config: acks=all, enable.idempotence=true, max.in.flight.requests.per.connection=5
Dead Letter Queue: telemetry.events.dlq.v1
DLQ Retention: 14 days with manual re-drive scripts in /scripts/redrive-dlq.py`,
    tags: ['Kafka', 'Streaming', 'Protobuf'],
    processingLogs: [
      {
        id: 'log-41',
        stage: 'uploaded',
        label: 'File uploaded',
        status: 'completed',
        timestamp: '2026-11-09 22:25:02',
        detail: 'Raw text configuration received',
      },
      {
        id: 'log-42',
        stage: 'extracting_text',
        label: 'Tokenizing config keys & environment variables...',
        status: 'in_progress',
        timestamp: '2026-11-09 22:25:07',
        detail: 'Extracting partition schemes and Kafka parameters (30%)',
      },
      {
        id: 'log-43',
        stage: 'chunking_content',
        label: 'Pending content chunking',
        status: 'pending',
        timestamp: 'Pending',
      },
      {
        id: 'log-44',
        stage: 'indexing',
        label: 'Pending vector indexing',
        status: 'pending',
        timestamp: 'Pending',
      },
      {
        id: 'log-45',
        stage: 'ready',
        label: 'Pending readiness',
        status: 'pending',
        timestamp: 'Pending',
      },
    ],
  },
  {
    id: 'src-doc-5',
    fileName: 'Legacy_Auth0_SAML_Federation_Mapping.pdf',
    fileFormat: 'pdf',
    fileSize: 13002342, // ~12.4 MB
    fileSizeBytesFormatted: '12.4 MB',
    uploadedAt: '2026-11-08T18:40:00Z',
    uploadedBy: mockUsers[4], // Kavita Patel
    projectId: 'proj-2',
    projectKey: 'AUTH-ZERO',
    processingStatus: 'failed',
    processingProgress: 15,
    pageCount: 64,
    chunkCount: 0,
    wordCount: 0,
    errorMessage: 'PDF extraction parser failed: Corrupt cross-reference table stream at offset 0x48f2.',
    extractedTextPreview: 'Error: Text extraction was aborted due to binary stream corruption.',
    tags: ['Auth0', 'SAML', 'Legacy'],
    processingLogs: [
      {
        id: 'log-51',
        stage: 'uploaded',
        label: 'File uploaded',
        status: 'completed',
        timestamp: '2026-11-08 18:40:01',
        detail: '12.4 MB binary received',
      },
      {
        id: 'log-52',
        stage: 'extracting_text',
        label: 'PDF Cross-reference Stream Parsing',
        status: 'failed',
        timestamp: '2026-11-08 18:40:15',
        detail: 'Corrupt cross-reference table stream at offset 0x48f2. Text extraction halted.',
      },
      {
        id: 'log-53',
        stage: 'failed',
        label: 'Processing failed',
        status: 'failed',
        timestamp: '2026-11-08 18:40:16',
        detail: 'User intervention required: re-export file or upload plain text/markdown version.',
      },
    ],
  },
  {
    id: 'src-doc-6',
    fileName: 'ClickHouse_Vector_Ingestion_Benchmarks.md',
    fileFormat: 'md',
    fileSize: 870400, // ~850 KB
    fileSizeBytesFormatted: '850 KB',
    uploadedAt: '2026-11-09T20:15:00Z',
    uploadedBy: mockUsers[1], // David Chen
    projectId: 'proj-3',
    projectKey: 'DATA-LAKE',
    processingStatus: 'indexing',
    processingProgress: 82,
    pageCount: 8,
    chunkCount: 18,
    wordCount: 3420,
    extractedTextPreview: `# ClickHouse Vector Ingestion Benchmarks & Partition Schemes

## Ingestion Throughput
Benchmarked on 3x c6i.4xlarge AWS instances with NVMe storage:
- Average Ingestion: 124,000 events/second
- p99 Latency: 18.4ms
- Compression Ratio: 4.8x using LZ4

## Partition Key Strategy
PARTITION BY toYYYYMM(event_time)
ORDER BY (project_id, event_type, event_time)
SETTINGS index_granularity = 8192

## Memory & Vector Indexes
Vector embeddings are indexed using Annoy tree indexes configured with 100 trees and angular distance metrics.`,
    tags: ['ClickHouse', 'DataLake', 'Performance', 'Benchmarks'],
    processingLogs: [
      {
        id: 'log-61',
        stage: 'uploaded',
        label: 'File uploaded',
        status: 'completed',
        timestamp: '2026-11-09 20:15:02',
      },
      {
        id: 'log-62',
        stage: 'extracting_text',
        label: 'Markdown AST extracted',
        status: 'completed',
        timestamp: '2026-11-09 20:15:08',
      },
      {
        id: 'log-63',
        stage: 'chunking_content',
        label: '18 semantic chunks created',
        status: 'completed',
        timestamp: '2026-11-09 20:15:15',
      },
      {
        id: 'log-64',
        stage: 'indexing',
        label: 'Generating dense vector embeddings & Qdrant points...',
        status: 'in_progress',
        timestamp: '2026-11-09 20:15:24',
        detail: 'Embedding 18 chunks with text-embedding-3-small (82%)',
      },
      {
        id: 'log-65',
        stage: 'ready',
        label: 'Pending readiness',
        status: 'pending',
        timestamp: 'Pending',
      },
    ],
  },
];
