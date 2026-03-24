# Lead Orchestration & Communication Engine (LOCE)

A highly configurable, scalable orchestration system built with **FastAPI + LangChain/LangGraph + Celery + PostgreSQL + Redis** to process millions of leads via batch and streaming ingestion, perform multi-NBFC dedupe routing (waterfall), trigger multi-channel communication workflows, and enable end-to-end funnel tracking.

---

## Quick Start

```bash
# 1. Clone & configure
cp .env.example .env
# Edit .env with your credentials

# 2. Start everything via Docker Compose
cd docker
docker compose up -d

# 3. Health check
curl http://localhost:8000/health
# → {"status": "ok", "service": "loce"}

# 4. Upload leads (CSV)
curl -X POST http://localhost:8000/leads/upload \
  -F "file=@leads.csv"
```

Interactive API docs: http://localhost:8000/docs

---

## Project Structure

```
langchain-project/
├── app/
│   ├── main.py                      # FastAPI app entry point
│   ├── config.py                    # Settings (pydantic-settings)
│   ├── database.py                  # Async SQLAlchemy session
│   ├── models/                      # SQLAlchemy ORM models
│   ├── schemas/                     # Pydantic request/response schemas
│   ├── api/                         # FastAPI routers (leads, batches, webhooks, analytics)
│   ├── services/                    # Business logic layer
│   ├── orchestration/               # LangChain/LangGraph graphs
│   ├── integrations/
│   │   ├── nbfc/                    # NBFC adapter framework (A, B, C)
│   │   └── communication/           # Partner adapters (MSG91, Karix, SendGrid, Exotel)
│   ├── workers/                     # Celery tasks + timer worker
│   └── utils/                       # Phone normalizer, rate limiter, encryption, etc.
├── alembic/                         # Database migrations
├── tests/                           # Pytest test suite
├── docs/                            # API, Architecture, Deployment, Runbook
├── docker/                          # Dockerfile + docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── .env.example
```

---

## Core Features (Phase P0)

| Feature | Status |
|---|---|
| CSV / API / S3 lead ingestion | ✅ |
| Schema validation & E.164 normalization | ✅ |
| Batch tracking with checksum & row counts | ✅ |
| NBFC dedupe waterfall (LangGraph) | ✅ |
| Lead qualification & status routing | ✅ |
| Multi-channel comm orchestration (LangGraph) | ✅ |
| Partner adapters: MSG91, Karix, SendGrid, Exotel | ✅ |
| Webhook ingestion with HMAC verification | ✅ |
| Idempotent event processing | ✅ |
| Per-NBFC token-bucket rate limiter | ✅ |
| Config versioning (draft → publish → rollback) | ✅ |
| Funnel analytics API | ✅ |
| Celery async workers + timer worker | ✅ |
| PII encryption at rest (Fernet) | ✅ |
| Alembic migrations | ✅ |
| Docker + docker-compose | ✅ |
| Structured logging (structlog) | ✅ |
| OpenTelemetry tracing hooks | ✅ |
| Prometheus metrics | ✅ |

---

## Running Tests

```bash
pip install -r requirements.txt
pip install aiosqlite  # SQLite async driver for tests
pytest tests/ -v
```

---

## Documentation

- [API Reference](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Runbook](docs/RUNBOOK.md)

---

## Technology Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.111 + Uvicorn |
| Orchestration | LangChain 0.2 + LangGraph 0.1 |
| Queue | Celery 5.4 + Redis 7 |
| Database | PostgreSQL 15 + SQLAlchemy 2 (async) |
| Migrations | Alembic 1.13 |
| Observability | structlog + OpenTelemetry + Prometheus |
| Containerization | Docker + Docker Compose |

