import os
import pymupdf  # PyMuPDF
import docx

os.makedirs("test_docs", exist_ok=True)

# 1. Create PDF using PyMuPDF
doc_pdf = pymupdf.open()
page1 = doc_pdf.new_page(width=595, height=842)
text1 = """APEX SETTLEMENT ENGINE ARCHITECTURE SPECIFICATION
Document ID: DOC-APEX-001 | Version: 2.1 | Classification: Internal Engineering

1. EXECUTIVE OVERVIEW
Project Apex is a high-throughput distributed multi-currency financial settlement engine.
The core system processes cross-border settlement transactions with a baseline sustained throughput of 5,000 TPS.
All communication strictly adheres to the ISO 20022 wire messaging format (pacs.008 and camt.053).

2. NETWORK & SECURITY ARCHITECTURE
All ingress network endpoints enforce TLS 1.3 encryption on port 443 with mutual TLS authentication.
Internal microservices communicate via gRPC over zero-trust service meshes.

3. PERSISTENCE & STORAGE
Primary persistence layer is PostgreSQL 16 with the pgvector extension for real-time semantic search.
Transactions are partitioned across 16 database shards with automated failover.

4. TARGET MILESTONES & LEADERSHIP
Production Launch Target Deadline: October 15, 2026.
API Gateway Component Lead: Marcus Vance.
Security Penetration Testing Audit: August 30, 2026.
"""
page1.insert_text((50, 60), text1, fontsize=11)

page2 = doc_pdf.new_page(width=595, height=842)
text2 = """APEX SETTLEMENT ENGINE ARCHITECTURE SPECIFICATION (PAGE 2)

5. DISASTER RECOVERY & COMPLIANCE
Target Recovery Point Objective (RPO): < 5 seconds.
Target Recovery Time Objective (RTO): < 60 seconds.
Disaster Recovery Failover Runbook Ownership: [UNASSIGNED / TBD].
SOC2 Type II Compliance Audit Deadline: November 15, 2026.

6. OUTGOING TRANSITION DIRECTIVES
The outgoing engineering team has completed core consensus logic and ingress validation.
Incoming team leads must execute end-to-end load validation prior to launch.
"""
page2.insert_text((50, 60), text2, fontsize=11)
doc_pdf.save("test_docs/apex_settlement_architecture.pdf")
doc_pdf.close()
print("Created test_docs/apex_settlement_architecture.pdf")

# 2. Create DOCX using python-docx
doc_docx = docx.Document()
doc_docx.add_heading("Apex Architecture Decision Record (ADR-014)", 0)
p1 = doc_docx.add_paragraph()
p1.add_run("Title: Primary Database Persistence & Event Stream Engine\n").bold = True
p1.add_run("Status: APPROVED and Superseding all earlier ADR proposals.\n")
p1.add_run("Context: Prior iterations evaluated Apache Cassandra 4.0 for horizontal scale. However, ADR-014 establishes PostgreSQL 16 with pgvector extension to achieve ACID compliance and unified relational plus vector retrieval.\n")

doc_docx.add_heading("Event Bus Infrastructure", level=1)
p2 = doc_docx.add_paragraph()
p2.add_run("The central message bus is Apache Kafka 3.6 running as a 3-broker cluster with SASL/SCRAM authentication. Alternative serverless queuing proposals (AWS SQS/SNS) have been dismissed due to sub-millisecond latency requirements.")

doc_docx.add_heading("Decommissioning Directives", level=1)
p3 = doc_docx.add_paragraph()
p3.add_run("Legacy Apache Cassandra 4.0 clusters and manual Chef deployment runbooks are deprecated and scheduled for decommissioning in Sprint 14.")

doc_docx.save("test_docs/apex_migration_guide.docx")
print("Created test_docs/apex_migration_guide.docx")

# 3. Create TXT runbook
runbook_content = """APEX OPERATIONAL RUNBOOK & SPRINT HANDOVER NOTES
==================================================
Project: Apex Multi-Currency Settlement Engine
Classification: Confidential - Engineering Handover

1. OPERATIONAL READINESS CHECKS
- Health endpoint: https://internal.apex-pay.io/api/v1/health
- Kafka cluster quorum verification: 3 active brokers, min.insync.replicas=2.
- PostgreSQL replica lag monitoring: alert if replica lag > 150ms.

2. PENDING TASKS ASSIGNED FOR CONTINUITY
- TASK-001: Verify payment gateway ingress mutual TLS authentication and cipher suites.
  Owner: Elena Rostova (Incoming Engineer) | Priority: High | Status: NOT_STARTED
- TASK-002: Run database index health audit on settlement_transactions table partitions.
  Owner: Elena Rostova (Incoming Engineer) | Priority: Medium | Status: NOT_STARTED

3. CONFLICTING STATEMENT & SCHEDULE ALIGNMENT
- Production Launch Target Deadline: December 1, 2026 (Partner banking gateway integration postponed by 45 days).
- API Gateway Component Lead: Elena Rostova.
- Database On-Call Primary Rotation Lead: [UNASSIGNED / TBD].
"""
with open("test_docs/apex_operational_runbook.txt", "w", encoding="utf-8") as f:
    f.write(runbook_content)
print("Created test_docs/apex_operational_runbook.txt")

# 4. Create Markdown PRD
prd_content = """# Apex Multi-Currency Engine Product Requirements (PRD)

**Project Identifier:** APEX-SETTLE  
**Document Author:** Sarah Chen (Lead Architect)  
**Target Milestone:** Version 2.0 Production Release  

## 1. Product Scope & Functional Objectives
Apex enables real-time cross-border settlements between four primary currencies:
- United States Dollar (USD)
- Euro (EUR)
- British Pound Sterling (GBP)
- Japanese Yen (JPY)

The system must handle currency conversion spreads with zero drift and sub-second transaction finality.

## 2. Technical Stack Specifications
- **Application Engine:** Python FastAPI with asynchronous SQLAlchemy 2.0.
- **Persistence Store:** PostgreSQL 16 with pgvector extension.
- **Message Broker:** Apache Kafka 3.6 distributed event streaming.
- **Frontend SPA:** React 19 + TypeScript + Vite.

## 3. Critical Deadlines & Compliance Mandates
- Production Launch Target: **October 15, 2026** (Original PRD baseline).
- Security Penetration Testing Audit: **August 30, 2026**.
- SOC2 Type II Final Compliance Audit: **November 15, 2026**.

## 4. Key Risks & External Dependencies
- Risk 1: Legacy banking partners still utilize SWIFT MT103 formats; ISO 20022 translation layer may incur transformation overhead.
- Risk 2: Foreign exchange volatility buffers require dynamic margin recalculation during peak trading sessions.
- Blocker: Missing disaster recovery ownership assignment must be resolved before production approval.
"""
with open("test_docs/apex_product_requirements.md", "w", encoding="utf-8") as f:
    f.write(prd_content)
print("Created test_docs/apex_product_requirements.md")
