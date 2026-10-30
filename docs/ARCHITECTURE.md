# FDRSetu System Architecture & Technical Specifications

**FDRSetu – Intelligent Security Deposit and Fixed Deposit Receipt Management System**  
**Category:** Software | **Theme:** Smart Automation | **Target Client:** AICTE (All India Council for Technical Education)

---

## 1. High-Level System Architecture

FDRSetu is architected as an enterprise-grade digital portal following a strictly decoupled, modular architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT PRESENTATION TIER                        │
│   React 18 + Vite SPA | Tailwind CSS (Ocean Blue #006699) | Recharts   │
│   Public Portal  |  Institution Workspace  |  AICTE Scrutiny & Audit   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ HTTPS / REST (JSON)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        API & BUSINESS LOGIC TIER                       │
│                        FastAPI (Python 3.14 / 3.11)                    │
│                                                                        │
│  ┌───────────────┐ ┌────────────────┐ ┌──────────────────────────────┐ │
│  │ Auth & RBAC   │ │ FDR Lifecycle  │ │ Intelligent Verification     │ │
│  │ (JWT, Bcrypt) │ │ (14 States)    │ │ Engine (12 Rules)            │ │
│  └───────────────┘ └────────────────┘ └──────────────────────────────┘ │
│  ┌───────────────┐ ┌────────────────┐ ┌──────────────────────────────┐ │
│  │ OCR Pipeline  │ │ Scrutiny &     │ │ Audit Logging &              │ │
│  │ (PaddleOCR)   │ │ Release Queue  │ │ Scheduled Escalation Engine  │ │
│  └───────────────┘ └────────────────┘ └──────────────────────────────┘ │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
┌──────────────────────────────────────┐ ┌──────────────────────────────┐
│            PERSISTENCE TIER          │ │         STORAGE TIER         │
│         PostgreSQL Database          │ │  Secure File Vault & Temp    │
│  (SQLAlchemy 2.0 + Alembic Schema)   │ │  (MIME-validated, Isolated)  │
└──────────────────────────────────────┘ └──────────────────────────────┘
```

---

## 2. 5 Distinct Role-Based Access Control (RBAC) Actors

1. **Institution Admin (`ROLE_INSTITUTION_ADMIN`)**:
   - Manages own institution profile and submissions.
   - Uploads FDRs, reviews OCR-extracted draft fields, and corrects discrepancies.
   - Submits renewal requests and release/refund applications.
   - Strictly isolated to own institution records.

2. **AICTE Scrutiny Officer (`ROLE_SCRUTINY_OFFICER`)**:
   - Accesses scrutiny queues and assigned institution FDR dossiers.
   - Compares raw uploaded instruments with extracted OCR fields and verification reports.
   - Raises discrepancies, records observations, or requests additional documentation.
   - Recommends approval or rejection.

3. **AICTE Approving Authority (`ROLE_APPROVING_AUTHORITY`)**:
   - Reviews scrutiny officer recommendations and document audit trails.
   - Grants final approval/rejection for FDR activations, renewals, and release/refund requests.
   - Records statutory remarks.

4. **System Administrator (`ROLE_SYSTEM_ADMIN`)**:
   - Manages system users, institution onboarding, and RBAC roles.
   - Configures verification rule parameters and reminder notification schedules.
   - Inspects operational system logs and global performance metrics.

5. **Auditor (`ROLE_AUDITOR`)**:
   - Enforces regulatory governance with read-only access to all transactions.
   - Reviews historical verification scores, approval histories, and immutable audit logs.
   - Generates official compliance audit reports.

---

## 3. Database Schema Blueprint (17 Core Tables)

1. `users`: Credentials, status, and role bindings.
2. `roles`: Role definitions and permission scopes.
3. `institutions`: Profile details, AICTE permanent IDs, contact officers.
4. `institution_users`: Multi-tenant user-institution mapping.
5. `fdr_records`: Comprehensive financial attributes, dates, and lifecycle states.
6. `fdr_documents`: Uploaded instruments, file hashes, storage paths.
7. `ocr_extractions`: Raw extracted text, normalized values, and field confidence scores.
8. `verification_rules`: Configurable validation engine rules and severity levels.
9. `verification_results`: Execution outputs, flagged anomalies, and evidence references.
10. `scrutiny_records`: Scrutiny notes, observations, and recommendation history.
11. `renewal_requests`: Renewal workflows, replacement FDR links, and validity chains.
12. `release_requests`: Refund/release petitions, justification, and approval tracks.
13. `approval_records`: Official sign-offs and statutory remarks.
14. `notifications`: In-app and scheduled alert records with read receipts.
15. `audit_logs`: Append-only immutable trail with user, action, entity, and diffs.
16. `bank_directory`: Master catalog of recognized banks, branches, and IFSC codes.
17. `system_settings`: System parameters, reminder intervals (90/60/30/15/7 days).

---

## 4. Phase 1 Implementation Summary

- **Backend Foundation**: FastAPI application instance initialized with CORS middleware, lifespan events, and structured error handling.
- **Database Engine**: SQLAlchemy ORM integrated with PostgreSQL connection support (`psycopg3`), Alembic migrations configured, and graceful local development fallback.
- **Health-Check API**: `GET /api/v1/health` providing live telemetry of API status, database verification, storage directory writeability, and server time.
- **Frontend Foundation**: React + Vite single-page application configured with Tailwind CSS (Government Ocean Blue design palette `#006699`), responsive layout, and Axios API client.
- **End-to-End Connectivity**: Tested and validated full-stack communication with real-time diagnostics display.
