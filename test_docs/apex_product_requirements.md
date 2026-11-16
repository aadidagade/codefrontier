# Apex Multi-Currency Engine Product Requirements (PRD)

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
