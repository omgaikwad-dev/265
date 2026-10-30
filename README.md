# FDRSetu – Intelligent Security Deposit and FDR Management System

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![TailwindCSS](https://img.shields.io/badge/Styling-Tailwind%20CSS-38B2AC.svg?style=flat&logo=tailwind-css)](https://tailwindcss.com)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791.svg?style=flat&logo=postgresql)](https://www.postgresql.org)
[![Python](https://img.shields.io/badge/Python-3.11%20%2F%203.14-3776AB.svg?style=flat&logo=python)](https://python.org)

**FDRSetu** is a centralized digital governance portal designed for the **All India Council for Technical Education (AICTE)** to streamline the complete lifecycle of institutional Fixed Deposit Receipts (FDRs) and security deposits.

---

## Key Capabilities

- **Digital FDR Ingestion & Secure Storage**: Single-source-of-truth document vault with cryptographic checksums and MIME validation.
- **AI-Powered OCR Extraction**: Automated extraction of bank names, branch locations, IFSC codes, FDR numbers, principal deposit amounts, and maturity dates using **PaddleOCR** with confidence scoring.
- **Intelligent Verification Engine**: 12 automated validation rules detecting duplicates, IFSC irregularities, date mismatches, and cross-document inconsistencies.
- **Multi-Tier Scrutiny & Approval Workflow**: Scrutiny officers record observations, flag discrepancies, and submit structured recommendations to competent approving authorities.
- **Automated Lifecycle Expiry Alerts**: Real-time maturity tracking with automated multi-cadence reminders (90, 60, 30, 15, and 7 days prior to expiry).
- **5-Role Access Control**: Strictly enforced boundaries between Institution Admins, Scrutiny Officers, Approving Authorities, System Administrators, and Auditors.
- **Tamper-Evident Audit Trail**: Complete immutable logging of all statutory actions, verification updates, and status transitions.

---

## Technology Stack

- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, Axios, Recharts, React Hook Form, Zod.
- **Backend**: Python, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, Bcrypt, PyJWT.
- **Database**: PostgreSQL (with psycopg3 connector).
- **OCR Engine**: PaddleOCR, PyMuPDF, OpenCV.
- **Testing**: Pytest, FastAPI TestClient, Vitest.
- **Containerization**: Docker, Docker Compose.

---

## Directory Structure

```
aicte-securedeposit/
│
├── frontend/                     # React 18 + Vite frontend
│   ├── src/
│   │   ├── components/           # Reusable UI components
│   │   ├── layouts/              # Institution, Admin & Auditor layouts
│   │   ├── pages/                # Application views
│   │   ├── features/             # Feature-specific components
│   │   ├── services/             # Axios API client & endpoints
│   │   ├── hooks/                # Custom React hooks
│   │   ├── context/              # Auth & global context
│   │   ├── utils/                # Helper utilities
│   │   ├── App.jsx               # Main application component
│   │   ├── main.jsx              # Application bootstrap
│   │   └── index.css             # Tailwind base & custom styles
│   ├── index.html
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── package.json
│
├── backend/                      # FastAPI Python REST backend
│   ├── app/
│   │   ├── api/                  # Versioned API routes (v1)
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/    # Feature endpoints (health, auth, etc.)
│   │   │   │   └── api.py        # Central API v1 router
│   │   ├── core/                 # Config, security, and database engine
│   │   ├── models/               # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/              # Pydantic v2 request/response schemas
│   │   ├── services/             # Business logic layer
│   │   ├── repositories/         # Database persistence operations
│   │   ├── middleware/           # CORS, timing, and security headers
│   │   ├── permissions/          # Role-based authorization guards
│   │   ├── ocr/                  # Document intelligence & PaddleOCR
│   │   ├── verification/         # 12-rule automated validation engine
│   │   ├── lifecycle/            # State transitions & maturity monitors
│   │   ├── notifications/        # Background scheduler & email alerts
│   │   ├── audit/                # Immutable audit logger
│   │   └── main.py               # Application entrypoint & lifespan
│   ├── migrations/               # Alembic database migrations
│   ├── tests/                    # Automated Pytest suite
│   ├── Dockerfile
│   └── requirements.txt
│
├── storage/                      # Secure file vault
│   ├── uploads/                  # Submitted FDR instruments
│   └── temp/                     # OCR intermediate files
│
├── docs/                         # Architecture & design specifications
│   └── ARCHITECTURE.md
├── docker-compose.yml            # Multi-container local orchestration
├── .env.example                  # Environment configuration template
├── .gitignore
└── README.md
```

---

## Quickstart: Local Development

### 1. Backend Setup
```bash
cd backend

# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at:
- Swagger UI: `http://localhost:8000/api/v1/docs`
- Health Endpoint: `http://localhost:8000/api/v1/health`

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
Frontend Portal will be available at: `http://localhost:5173`

---

## Running Automated Tests

```bash
cd backend
.\venv\Scripts\pytest -v tests/
```

---

## Docker Deployment

To launch the complete stack (PostgreSQL database + FastAPI backend + React frontend):

```bash
docker-compose up --build -d
```
- Frontend UI: `http://localhost:5173`
- Backend API: `http://localhost:8000/api/v1/docs`
- PostgreSQL: `localhost:5432`
