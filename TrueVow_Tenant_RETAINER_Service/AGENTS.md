# TrueVow_RETAINER_Service — Agent Rules

# Agent Onboarding Preamble
# Drop this into any service's AGENTS.md to wire it into the ecosystem.
# The agent reads this on startup and becomes ecosystem-aware.

## WRITEBACK PROTOCOL (MANDATORY)

**You report to the TrueVow CTO Orchestrator.** Every session you work on this service, you MUST write back your learnings to the shared memory vault. Services without recent activity are flagged as STALE. Do not let this service go stale.

**Format for all writebacks:** "<service>: <specific action taken> | <result/outcome> | <what you learned> | <next step or blocker>"

### Start of Session — Activate Service
```
python ../TrueVow_Shared_Orchestration/orchestrator.py sync-memory
python ../TrueVow_Shared_Orchestration/orchestrator.py scan-services
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin start "SaaS Admin: <specific task> | resuming from <previous state> | goal: <what success looks like>"
```

### During Work — Log Learnings
```
python ../TrueVow_Shared_Orchestration/memory.py remember <category> "<title>" "<content>" --importance N
```
Categories: architecture, pattern, decision, dependency, convention, bug, context, todo, relationship
Importance: 10 = critical blocker, 8 = important decision, 5 = observation

### End of Session — Writeback Results
```
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin done "RETAINER : <what was accomplished> | outcome: <result> | learned: <key insight> | next: <what remains>" --status DONE
python ../TrueVow_Shared_Orchestration/orchestrator.py push-memory
```

### If Blocked — Alert Immediately
```
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin blocked "RETAINER: <specific blocker> | attempted: <what you tried> | need: <what will unblock>"
```

### Before Any Work — Route the Task
```
python ../TrueVow_Shared_Orchestration/orchestrator.py dispatch "<user's request>"
```

### Security & Research
- Scan new skills: `skillspector scan <path> --no-llm`
- Web research: `agent-reach doctor` for status

**Reminder:** Services go STALE after 24h without agent activity. Write back to prove this one is alive. The CTO dashboard refreshes every scan.

---

## Service-Specific Rules

> Add service-specific rules below. The ecosystem preamble above is auto-generated
> and wires this agent into the TrueVow Agent Ecosystem.

## Cross-Service Webhook Contracts

### WebhookSignature v1.0 (Frozen)

Implementation: `app/security/webhook_signature.py`
Golden fixtures: `tests/test_webhook_signature.py`

**RETAINER verifies** (receives from INTAKE):
- `POST /api/v1/retainer/webhooks/candidate-submitted`

**RETAINER signs** (sends to SaaS Admin):
- `POST /api/v1/matters/activate`

**Canonical signing string:** `{timestamp_ms}:{UPPERCASE_METHOD}:{path}:{body_sha256}`

**Key IDs:** `tv-primary` (default), `tv-secondary` (rotation)

**Env vars:** `TRUEVOW_WEBHOOK_KEY_ID`, `TRUEVOW_WEBHOOK_SECRET`

**Legacy migration:** Bearer/API-Key auth still accepted with deprecation warning
(logged as `LEGACY_AUTH`). **Cutoff: 2026-09-01.** After this date, all legacy tokens
are rejected (410 Gone). Configure via `LEGACY_WEBHOOK_AUTH_CUTOFF` env var.

**Canonical paths (exact, no trailing slash, no query string):**
- INTAKE → RETAINER: `/api/v1/retainer/webhooks/candidate-submitted`
- RETAINER → SaaS Admin: `/api/v1/matters/activate`

**Contract source of truth:** `shared-libraries/lib/contracts/index.ts`
**Golden fixtures:** `shared-libraries/tests/security/webhook-signature.test.ts`

### EventEnvelope v1.0.1

All outbox events use schema_version `1.0.1`.
Implementation: `packages/retainer-contracts/retainer_contracts/envelope.py`

### Idempotency

Webhook receiver enforces event idempotency via `event_id` in inbound payloads.
Duplicate events return previous result; conflicting events are rejected.
Implementation: `app/models/retainer.py` → `RetainerIdempotencyKey`
