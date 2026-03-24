# Runbook

## NBFC Outage

**Symptoms**: High ERROR/TIMEOUT rate in `dedupe_logs`, alerts on NBFC error rate metric.

**Actions**:
1. Check NBFC status page / partner SLA channel.
2. Verify `NBFC_X_BASE_URL` and `NBFC_X_API_KEY` are correct.
3. If outage is confirmed, temporarily update `nbfc_priority` config to skip or deprioritise the affected NBFC:
   ```bash
   # Via API (once config admin endpoint is added)
   # Or directly in DB:
   UPDATE config_versions SET nbfc_config = '{"nbfc_priority": ["NBFC_B", "NBFC_C"]}' WHERE status = 'published';
   ```
4. Monitor DLQ for stalled dedupe tasks. Replay when NBFC recovers:
   ```bash
   celery -A app.workers.celery_app.celery_app inspect active
   ```

---

## Partner (Comm) Outage

**Symptoms**: High failure rate in `communication_logs`, partner health check alerts.

**Actions**:
1. Check partner status.
2. The adapter's transport retry (Tenacity, 3 attempts) will handle transient failures.
3. For sustained outage: update comm_sequence config to replace the failing partner.
4. Replay failed sends via `run_dedupe_task` / `start_journey_task` after recovery.

---

## Queue Backlog

**Symptoms**: Celery queue depth > threshold, lead processing lag.

**Actions**:
1. Scale up workers: `docker compose scale worker=8`
2. Check per-NBFC QPS limits – reduce `nbfc_default_qps` if being rate-limited.
3. Monitor DLQ (`celery -A ... inspect reserved`).

---

## DLQ Replay

```bash
# List DLQ tasks
celery -A app.workers.celery_app.celery_app inspect reserved

# Retry a specific task
celery -A app.workers.celery_app.celery_app call loce.run_dedupe --args='["<lead_id>"]'
```

---

## Webhook Replay

Each incoming webhook raw payload is stored in `event_logs.payload_ref`. To replay:
```sql
SELECT payload_ref FROM event_logs WHERE event_type = 'comm.failed' AND timestamp > NOW() - INTERVAL '1 day';
```
Re-POST the payload to `/webhooks/{channel}` with appropriate headers.

---

## PII Data Request (GDPR/DPDPA)

1. Look up lead by `phone_hash` or `email_hash` (never expose raw hash to requester).
2. Use `app.utils.encryption.decrypt()` to retrieve plaintext PII.
3. Export all associated `dedupe_logs`, `communication_logs`, `event_logs`.
4. For deletion: set `phone_e164 = NULL`, `email = NULL`, retain hashes for audit.

---

## Security Incident – Compromised Webhook Secret

1. Rotate the affected `WEBHOOK_HMAC_SECRET_<partner>` immediately.
2. Update the env var in all deployments and restart API pods.
3. Notify the partner to update their signing secret.
4. Review `event_logs` for unexpected entries from that partner.
