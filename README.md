# Cyber Fraud Correlator

An AI-powered cyber fraud correlator tailored for law enforcement and financial intelligence investigators. The system ingests fragmented investigation artifacts (telecom CDR/IPDR dumps, bank/UPI transaction spreadsheets, raw email headers, and Android forensic logs), normalizes disparate formats, links cross-case entities through a unified graph network, scores operational fraud risk, and synthesizes a court-ready one-page investigative brief.

## Prerequisites
- **Docker & Docker Compose**: v2.20+ (recommended for containerized local development)
- **Node.js**: v20.0+ and `npm` v10+ (for local frontend development)
- **Python**: v3.11+ (for local backend development)

---

## Getting Started

### Option 1: Quickstart with Docker Compose (Recommended)

Run both the backend and frontend services inside a shared bridge network with live code-reloading:

```bash
# 1. Clone repository and initialize environment file
cp .env.example .env

# 2. Build and start containers
docker compose up --build

# 3. Access applications:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - Interactive API Docs: http://localhost:8000/docs
```

---

### Option 2: Local Native Development

#### 1. Backend Service (FastAPI)

```bash
# Navigate to backend folder
cd backend

# Create and activate a Python 3.11 virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with development tooling
pip install --upgrade pip
pip install -e ".[dev]"

# Start FastAPI development server with hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend check commands:
```bash
ruff check app tests
black --check app tests
pytest
```

#### 2. Frontend Service (React + Vite + TypeScript)

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Run Vite development server
npm run dev
```

Frontend check commands:
```bash
npm run lint
npm run build
```

---

## Monorepo Architecture

```
/
├── backend/                  # Python/FastAPI service
├── frontend/                 # React/TypeScript/Vite app
├── docs/
│   └── architecture.md       # Living architecture doc, keep updated each phase
├── CLAUDE.md                 # Persistent project context & conventions
├── docker-compose.yml        # Local dev: both services + shared network
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
└── README.md                 # Project introduction and getting started
```
