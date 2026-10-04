# AirGuard Agent - n8n Workflow Automation

This directory contains the n8n automation workflow that connects **AirGuard Agent** to external notification gateways (SMS, WhatsApp, caregiver alerts, smart home HEPA switches).

## Architectural Principle: Deterministic Human Approval Gate

Even inside n8n, AirGuard enforces strict zero-trust safety:
1. **Webhook Reception**: n8n listens on `/webhook/airguard-approved-alert`.
2. **Approval Verification Gate**: The workflow inspects `body.status === 'APPROVED'`. If an unapproved or pending action is received, the workflow drops it and returns HTTP 403 `Security Guard Violation`.
3. **Payload Formatting**: Formats clinical alerts with patient context, recommended action, and emergency non-diagnostic disclaimers.
4. **Gateway Dispatch**: Relays to SMS (Twilio) or WhatsApp Cloud API.
5. **Audit Confirmation**: Responds to AirGuard with an execution receipt (`dispatched_at`, `status: DISPATCHED`).

---

## Quick Setup Instructions

### 1. Run n8n locally
Using npm / npx:
```bash
npx n8n
```
Or via Docker:
```bash
docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n
```

### 2. Import Workflow
1. Open n8n in your browser at `http://localhost:5678`.
2. Click **Workflows** -> **Import from File**.
3. Select `n8n/airguard_workflow.json`.
4. Click **Publish** / **Activate**.

### 3. Connect AirGuard
In your `.env` file (or environment variables):
```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/airguard-approved-alert
```

---

## Testing the Webhook

### Test 1: Approved Action (Allowed)
```bash
curl -X POST http://localhost:5678/webhook/airguard-approved-alert \
  -H "Content-Type: application/json" \
  -d '{
    "action_id": 105,
    "user_id": 1,
    "status": "APPROVED",
    "recipient": "Alex Rivera (+1555019900)",
    "channel": "sms",
    "message": "AirGuard Advisory: Reschedule evening outdoor cardio to 06:30-08:30 AM clean air window.",
    "reasoning": "Open-Meteo forecast indicates PM2.5 spike to 142 µg/m³ at 18:00.",
    "timestamp": "2026-10-04T12:00:00Z"
  }'
```
**Expected Response:** HTTP 200 `{ "success": true, "status": "DISPATCHED", ... }`

### Test 2: Unapproved Action (Blocked by Safety Rail)
```bash
curl -X POST http://localhost:5678/webhook/airguard-approved-alert \
  -H "Content-Type: application/json" \
  -d '{
    "action_id": 106,
    "user_id": 1,
    "status": "PENDING",
    "recipient": "Caregiver",
    "channel": "sms",
    "message": "Unapproved alert attempt"
  }'
```
**Expected Response:** HTTP 403 `{ "success": false, "error": "Security Guard Violation: Action was not approved by human patient" }`
