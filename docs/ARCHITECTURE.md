# Architecture

## Overview

LOCE is a horizontally scalable, event-driven system built on FastAPI + Celery + PostgreSQL + Redis.

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    LOCE System                          │
                    │                                                         │
 CSV/API/S3 ──────► │  FastAPI App                                            │
                    │  ├── /leads/upload  ──► Celery Queue ──► Dedupe Worker │
                    │  ├── /leads/{id}                         ├── NBFC_A    │
                    │  ├── /batches/{id}                       ├── NBFC_B    │
                    │  ├── /webhooks/*   ──► Event Processor   └── NBFC_C    │
                    │  └── /analytics/*                                       │
                    │                                                         │
                    │  PostgreSQL (transactional + event store)               │
                    │  Redis (Celery broker + distributed state)              │
                    └─────────────────────────────────────────────────────────┘
```

## Components

### 1. Lead Upload Service
- Accepts CSV via `POST /leads/upload`
- Computes SHA-256 checksum, creates `Batch` record
- Defers row-level processing to Celery worker
- Returns `batch_id` + `job_id` immediately (202 Accepted)

### 2. Dedupe Orchestrator (LangGraph)
- Implements waterfall pattern via `DedupeState` graph
- Calls NBFC adapters sequentially per `nbfc_priority` config
- Stops at first PASS; exhausts list → FAIL
- Logs every attempt in `dedupe_logs` with idempotency key

### 3. NBFC Adapter Framework
- Abstract `BaseNBFCAdapter` with retry (Tenacity) and rate-limiting (token bucket)
- Concrete implementations: `NBFCAAdapter`, `NBFCBAdapter`, `NBFCCAdapter`
- Registry pattern: `get_nbfc_adapter(nbfc_id)` resolves at runtime

### 4. Lead Qualification Engine
- On PASS: updates `lead.status = qualified`, enqueues journey start
- On all FAIL: marks `lead.status = rejected`

### 5. Communication Orchestrator (LangGraph)
- `JourneyState` graph executes steps from configured `comm_sequence`
- Per-step: try each partner in order until success
- Updates `journey_instances.current_step_index` and `state`

### 6. Communication Partner Adapters
- Abstract `BaseCommAdapter` with transport retry
- Registry: `get_comm_adapter(channel, partner)`
- Implementations: MSG91 (SMS), Karix (WhatsApp), SendGrid (Email), Exotel (IVR)

### 7. Event & Webhook Processor
- Normalises partner webhook payloads to internal `comm.*` event types
- HMAC-SHA256 signature verification per partner
- Idempotent: dedupe on `(partner, partner_message_id, event_type)`
- Stores events in append-only `event_logs` table

### 8. Timer Worker
- Polls `journey_instances` for overdue `next_action_at`
- Dispatches `advance_journey_task` to Celery

### 9. Configuration Engine
- `ConfigVersion` model with `draft → published → archived` lifecycle
- `ConfigManagerService` for CRUD, publish, rollback
- Configs pinned to batches via `config_version_id`

### 10. Analytics
- Funnel report: upload → dedupe → sends → events
- NBFC performance: PASS/FAIL/ERROR per NBFC
- Channel performance: sends/delivered/read/clicked per channel+partner

## Data Flow

```
CSV Upload
  → Batch (pending)
  → Celery: process_batch_task
    → per Lead: run_dedupe_task
      → LangGraph dedupe waterfall
        PASS → lead.status=qualified → start_journey_task
          → JourneyService.start_journey
            → LangGraph journey step execution
              → CommunicationLog (requested → accepted/failed)
        FAIL → lead.status=rejected

Partner Webhook
  → POST /webhooks/{channel}
  → EventProcessorService
    → HMAC verify
    → Normalise event type
    → Idempotency check
    → EventLog (append-only)
    → Update CommunicationLog.status
```

## Security

- PII hashed (SHA-256) in `phone_hash`, `email_hash` columns
- PII encrypted at rest using Fernet (AES-128-CBC) with key derived from `APP_SECRET_KEY`
- Secrets managed via environment variables; production should use AWS KMS / HashiCorp Vault
- Webhook HMAC-SHA256 verification per partner
- Non-root Docker user

## Scalability

- All async I/O (FastAPI + asyncpg + asyncio)
- Celery workers autoscale independently
- Per-NBFC token bucket rate limiter
- Idempotency keys on all external effects (dedupe, sends, webhooks)
- Append-only event store for analytics; mutable `lead.status` as projection
