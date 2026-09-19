# Backend Service: Cyber Fraud Correlator

FastAPI backend service responsible for artifact parsing, correlation graph modeling, scoring heuristics, and brief generation.

## Prerequisites
- Python 3.11+
- pip

## Virtual Environment Setup

Always use an isolated virtual environment to manage dependencies locally:

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python3.11 -m venv .venv

# 3. Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# 4. Upgrade pip and install package with dev dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

## Running Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Linting & Testing
```bash
# Format with black
black app tests

# Lint with ruff
ruff check app tests

# Run test suite
pytest
```
