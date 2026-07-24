# Platform Map

> Source of truth (re-derive from these; do not hand-maintain counts):
> - Registered services + live git state: `python TrueVow_Shared_Orchestration/orchestrator.py scan-services` and `config.yaml`
> - Trust domains: `shared-libraries/auth-client/src/domain-config.ts`
> - Owners + ports: `TrueVow_Knowledge_Orchestrator/DEVELOPERS.md`

## Trust domains (Clerk 3-app architecture)
| Domain | Clerk App | Trust | Core rule | Services |
|---|---|---|---|---|
| **PLATFORM_OPERATORS** | App 1 | HIGH | internal only; NOT firm-scoped; never casually touch tenant PHI; audit every privileged action | SaaS Admin, Internal Ops, Customer Success CORE, Financial Management, Billing |
| **SALES_SUPPORT** | App 2 | MEDIUM (LLM zone) | PII redacted **before** any LLM prompt; no direct tenant DB; response/rate caps | Sales Ops, First-Line Support\* |
| **TENANTS** | App 3 | EXTERNAL | tenant isolation absolute (query firm-scope + API validation + Supabase RLS) | INTAKE, Customer Portal, TRACE, SETTLE, LEVERAGE, VERIFY |

## Services (owner / port / status)
| Service | Domain | Owner | Port | Status | One-liner |
|---|---|---|---|---|---|
| SaaS Administration | App1 | ghous-isb | 3001 | active | tenant mgmt + **MDM system of record** |
| Internal Ops | App1 | yasha | 3006 | active | back-office: tasks/HR/payroll/RevOps |
| Customer Success CORE | App1 | ghous-isb | 3012 | active | CSM health/onboarding/renewal (**LLM-free**) |
| Financial Management | App1 | yasha | 3011 | active | double-entry accounting + treasury |
| Billing | App1 | ghaus-fsd | 3016 | active | subscriptions/invoicing/payments (TELR+Stripe) |
| Sales Ops | App2 | sania | 3056 | active | lead-gen CRM (**LLM zone**) |
| First-Line Support | App2 | ghous-isb | 3007 | **ARCHIVED → Chatwoot** | historical only |
| INTAKE (Tenant Application) | App3 | ghaus-fsd | 3022 | active | multi-bridge AI voice intake |
| Customer Portal | App3 | yasha | 3031 | active | attorney dashboard (frontend-only) |
| TRACE | App3 | yasha | 3036 | active | medical-records chronology engine + demand package |
| SETTLE | App3 | yasha | 8002 | active | settlement range estimator |
| LEVERAGE (ex-DRAFT) | App3 | yasha | 3036 (shared, hidden in portal) | retired-ui | zero-knowledge compliance validation (sidebar hidden, TRACE now primary) |
| VERIFY | App3 | yasha | — | **not git-init'd** (see note) | blockchain certificate verification |
| Platform Analytics | — | yasha | 3071 | active | pipeline dashboards (SigNoz) |
| TWIML SoftPhone | — | yasha | — | not a git repo | voice softphone app |
| CONNECT | App3 | — | — | **ARCHIVED** | decommissioned |
| Dialogflow Intake | — | — | — | **DEAD** | do not touch |

\*First-Line Support: operations moved to self-hosted **Chatwoot** (port 3007). The repo is preserved for reference only.

## Standard stack
Python 3.11 + **FastAPI** + async **SQLAlchemy** + **Alembic**; **Supabase** Postgres (+ Storage); **Next.js/TypeScript** frontends; **Fly.io** hosting; **Clerk** auth (3-domain, see `domain-config.ts` + `shared-libraries/auth-client`); **OpenTelemetry → SigNoz + Sentry** observability. Each service has `docs/00-Planning/<Service>-Agent-Coding-Instructions.md`.

## Known infra gaps (as of curation)
- **VERIFY** now has an initial git commit; confirm it's registered in `config.yaml` and pushed.
- **TWIML SoftPhone**, **Platform Analytics** — verify git-init / source backup status.

_Curated 2026-07-10._
