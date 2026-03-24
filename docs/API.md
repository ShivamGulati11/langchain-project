# API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

Currently unauthenticated for internal/dev use. Production deployments should add JWT Bearer authentication.

---

## Leads

### POST /leads/upload
Upload a CSV file for batch ingestion.

**Request:** `multipart/form-data`
- `file` (required): CSV file with headers: `phone`, `email`, `first_name`, `last_name`, `external_ref`, `consent_given`
- `config_version_id` (optional): UUID of a published ConfigVersion

**Response 202:**
```json
{
  "batch_id": "uuid",
  "job_id": "job-uuid",
  "message": "Batch ingestion accepted"
}
```

### POST /leads/
Create a single lead via HTTP API.

**Request body:**
```json
{
  "phone_e164": "+919876543210",
  "email": "user@example.com",
  "first_name": "Rahul",
  "last_name": "Sharma",
  "consent_given": true
}
```

**Response 201:** Full `LeadRead` object.

### GET /leads/{lead_id}
Retrieve lead profile with current status.

**Response 200:** Full `LeadRead` object.
**Response 404:** Lead not found.

---

## Batches

### GET /batches/{batch_id}
Return batch progress, row counts, and error artifact link.

**Response 200:** Full `BatchRead` object.

---

## Webhooks

All webhook endpoints accept `POST` with a JSON body. The `X-Partner` header identifies the sender (e.g., `msg91`, `karix`, `sendgrid`). HMAC-SHA256 signature should be provided via `X-Signature` header.

### POST /webhooks/sms
### POST /webhooks/whatsapp
### POST /webhooks/email
### POST /webhooks/ivr

**Response 200:** `{"status": "accepted"}`

---

## Analytics

### GET /analytics/funnel
Returns funnel counts at each stage. Optional `batch_id` filter.

```json
{
  "total_leads": 10000,
  "qualified": 7500,
  "rejected": 2500,
  "comm_sends": 6000,
  "delivered": 5000,
  "engaged": 1200
}
```

### GET /analytics/nbfc-performance
Returns PASS/FAIL/ERROR counts per NBFC.

### GET /analytics/channel-performance
Returns send/delivered/read/clicked counts per channel + partner combination.

---

## Health

### GET /health
```json
{"status": "ok", "service": "loce"}
```
