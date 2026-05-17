# Retrosynthesis Search

A distributed system for finding synthetic routes to complex molecules from simpler, commercially available precursors.

## Architecture

```
Client (SMILES input)
    ↓
POST /api/search
    ↓
┌─────────────────────┐          ┌──────────────────┐
│   Backend API       │          │   Microservice   │
│   :8000             │ ──────→  │   :8001          │
│                     │ ←──────  │                  │
│  • Persistence      │ callback │  • Route search  │
│  • Status polling   │          │  • Batch POSTs   │
└──────────┬──────────┘          └──────────────────┘
           ↓
    ┌──────────────┐
    │  PostgreSQL  │
    │  :5432       │
    └──────────────┘
```

**Flow:** Client submits a SMILES string → backend creates a search record and notifies the microservice → microservice processes routes and POSTs batches back via callback → client polls for status, then fetches results.

## Stack

- **Backend / Microservice**: Python 3.11, FastAPI, Uvicorn
- **Database**: PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic
- **HTTP**: httpx (async)
- **Tooling**: ruff, mypy (strict), pytest

## Quickstart

```bash
# Start all services (Postgres, backend, microservice)
make up

# View logs
make logs

# Stop
make down
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/search` | Submit a SMILES string, returns `search_id` |
| `GET` | `/api/search/{id}/status` | Poll search status (`pending` / `in_progress` / `completed` / `failed`) |
| `GET` | `/api/search/{id}/results` | Fetch routes; accepts optional `?min_score=0.8` |

## Development

```bash
# Install dev dependencies
make install

# Lint and type-check
make lint
make typecheck

# Run tests
make test

# Full CI pipeline (lint + typecheck + test)
make ci
```

## Integration Testing

```bash
cd scripts
python mock_client.py "CCO" --backend-url http://localhost:8000

# With score filtering
python mock_client.py "CCO" --min-score 0.8 --timeout 60
```

## Environment Variables

**Backend** (required):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `MICROSERVICE_URL` | URL of the microservice |
| `BACKEND_URL` | Callback base URL (default: `http://backend:8000`) |

**Microservice** (optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `BATCH_SIZE` | `1` | Routes per callback batch |
| `BATCH_DELAY_SECONDS` | `0.5` | Simulated processing delay |
