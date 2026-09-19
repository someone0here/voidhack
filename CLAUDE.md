# CLAUDE.md

## Current Phase
Phase 1: Project Scaffolding & Foundation (Scaffolding complete; baseline tooling, Docker network, and configs established).

## Project Overview
An AI-powered cyber fraud correlator tailored for law enforcement and financial intelligence investigators. The platform ingests fragmented, heterogeneous investigation artifacts (telecom CDR/IPDR dumps, bank transaction/UPI statement sheets, raw email headers, and Android extraction/forensic logs), parses and normalizes disparate records, automatically correlates shared entities across cases, scores operational fraud risk, and produces an exportable, court-ready one-page investigative brief.

## Tech Stack
- **Backend**:
  - Python 3.11+
  - FastAPI (REST API framework)
  - Uvicorn (ASGI server)
  - SQLModel (ORM combining SQLAlchemy + Pydantic)
  - Pandas (Data ingestion, tabular manipulation, normalization)
  - NetworkX (Graph-based entity linkage and network analysis)
  - ReportLab (Automated one-page PDF investigative brief generation)
  - Python-Multipart (Streaming artifact uploads)
  - Ruff & Black (Linting & formatting)
  - Pytest (Unit and integration testing)
- **Frontend**:
  - Vite (Build tool & dev server)
  - React 18+ (UI library)
  - TypeScript (Language, strict mode enabled)
  - Tailwind CSS (Utility-first styling system)
  - ESLint & Prettier (Strict linting & code formatting)

## Design Language
The user interface pairs Apple fluid-interaction principles—subtle spring physics, tactile direct-manipulation gestures, translucent blurred surfaces (`backdrop-blur`), crisp micro-typography, and seamless transitions—with a skeuomorphic field-dossier visual skin reminiscent of classified evidentiary briefs and tactical operational binders. High-density evidentiary data cards mimic physical folder inserts with stamped classification markers, subtle paper textures, and hairline border dividers. The visual palette centers on tactical canvas dark `#0F172A` (Canvas Ground), classified dossier slate `#1E293B` (Surface Card), evidentiary border `#334155` (Hairline Divider), forensic amber `#F59E0B` (Suspect Linkage / Medium Threat), alert crimson `#EF4444` (Critical Risk / High Threat), intelligence cyan `#06B6D4` (Verified Anchor / Telecom Node), stark readout `#F8FAFC` (Primary Text), and dossier metadata `#94A3B8` (Secondary Telemetry).

## Folder Structure
```
/
├── backend/                  # Python/FastAPI service
│   ├── app/                  # Application package (API routes, core logic, models)
│   ├── tests/                # Pytest test suites
│   ├── Dockerfile            # Container definition for backend service
│   ├── pyproject.toml        # Dependencies, ruff, black, and pytest configuration
│   └── README.md             # Backend-specific instructions & venv setup
├── frontend/                 # React/TypeScript/Vite app
│   ├── src/                  # Application source (components, hooks, styles)
│   ├── public/               # Static assets
│   ├── Dockerfile            # Container definition for frontend service
│   ├── package.json          # Node dependencies and scripts
│   ├── tsconfig.json         # Strict TypeScript configuration
│   ├── tsconfig.node.json    # TypeScript node/tooling configuration
│   ├── vite.config.ts        # Vite configuration
│   ├── tailwind.config.ts    # Tailwind CSS design system tokens
│   ├── postcss.config.js     # PostCSS plugins
│   ├── .eslintrc.json        # ESLint strict linting rules
│   └── .prettierrc           # Prettier code formatting rules
├── docs/
│   └── architecture.md       # Living architecture doc, keep updated each phase
├── CLAUDE.md                 # Persistent project context & conventions
├── docker-compose.yml        # Local dev: both services + shared network
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
└── README.md                 # Project introduction and local setup guide
```

## Coding Conventions
- **Python**:
  - Formatting & Linting: Ruff for linting and import sorting, Black for consistent formatting (88 character line limit).
  - Type Hinting: All function signatures, inputs, and returns must have explicit type hints (`typing` / built-in generics).
  - Testing: Pytest for unit and integration tests. Place tests under `backend/tests/`.
  - Architecture: Separation of concerns across schemas/models, services/parsers, and routers.
- **TypeScript & React**:
  - Strict Mode: Always enabled (`strict: true`, `noImplicitAny: true`, `strictNullChecks: true`).
  - Strict Typing: Zero tolerance for `any`; use strict interfaces, type unions, or `unknown` with runtime type guards.
  - Linting & Formatting: ESLint with TypeScript rules and Prettier for automated formatting.
  - Component Architecture: Small, single-responsibility functional components with typed props.
