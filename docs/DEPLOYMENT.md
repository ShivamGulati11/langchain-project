# Deployment Guide

## Prerequisites

- Docker & Docker Compose 2.x
- Python 3.11+ (for local development)
- PostgreSQL 15+ (managed or Docker)
- Redis 7+ (managed or Docker)

---

## Quick Start (Docker Compose)

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env and set real secrets

# 2. Start all services
cd docker
docker compose up -d

# 3. Verify
curl http://localhost:8000/health
```

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis URL for distributed state |
| `CELERY_BROKER_URL` | Redis URL for Celery broker |
| `APP_SECRET_KEY` | Secret for JWT and PII encryption – **must be long and random** |
| `WEBHOOK_HMAC_SECRET_*` | Per-partner HMAC secrets |
| `NBFC_*_API_KEY` | NBFC API credentials |
| `MSG91_AUTH_KEY`, etc. | Communication partner credentials |

---

## Database Migrations

```bash
# Run all pending migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1
```

---

## Running Workers

```bash
# Celery worker
celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=4

# Timer worker (separate process)
python -m app.workers.timer_worker
```

---

## Production Recommendations

1. **Secrets**: Use AWS KMS or HashiCorp Vault instead of plain env vars
2. **Database**: Use a managed PostgreSQL service with connection pooling (PgBouncer)
3. **Queue**: Replace Redis with Amazon SQS or Apache Kafka for >10M leads/day
4. **Scaling**: Deploy API and workers as separate Kubernetes deployments with HPA
5. **Observability**: Connect OTEL exporter to Jaeger/Tempo; use Prometheus + Grafana
6. **TLS**: Terminate at load balancer; enforce mTLS for internal service communication
7. **DLQ**: Configure Celery DLQ → alert on queue depth
