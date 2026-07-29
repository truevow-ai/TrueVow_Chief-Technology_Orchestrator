# TrueVow RETAINER Product Architecture and Build Specification

**Version:** 1.0

**Status:** Implementation-ready greenfield specification

**Date:** July 29, 2026

**Initial production scope:** California plaintiff personal-injury contingency engagements

**Primary users:** Intake coordinator / firm staff, responsible attorney, firm administrator, prospective client

**Normative sources:** TrueVow Plaintiff Law Firm Operations Ontology v1.0; TrueVow Ontology Registry v1.0; California RETAINER Compliance & Decision Map v1.0; deployed shared platform contracts reported July 29, 2026.

> RETAINER is a firm-governed engagement workflow. The firm exercises legal authority; TrueVow executes authorized administrative work and preserves evidence.

## Document control and source-of-truth order

| Priority | Source | What it controls |

| --- | --- | --- |

| 1 | TrueVow Ontology Registry | Canonical IDs, authority classes, actors, entities, states, events, invariants, metrics, envelope and transition contract |

| 2 | Versioned shared contracts package / SaaS Admin reference data | Executable shared schemas, policy and authority reference data |

| 3 | This RETAINER specification and companion registries | Product behavior, product extensions, API/data/workflow contracts |

| 4 | Implementation code | Must conform to the sources above; code does not redefine the ontology |

| 5 | UI labels and projections | May vary without changing canonical meaning |



When sources conflict, implementation must fail CI until the contract is normalized. No repository may silently choose its own interpretation.

## Executive decisions

- RETAINER is the missing greenfield product; INTAKE, SaaS Admin, TRACE, and SETTLE continue their ontology refactors independently.

- RETAINER owns Firm-Approved Representation -> Completed Engagement and Activation Conditions. It does not decide representation.

- SaaS Admin remains authoritative for tenants, users, roles, attorney verification, jurisdiction profiles, policies, template approvals, entitlements, and integration settings.

- RETAINER integrates with other products through versioned commands/events/APIs; it never reads or writes another product database.

- The shared WorkflowRuntime loads RETAINER registries; RETAINER does not fork a second state-machine framework.

- California v1 requires named-attorney representation approval, conflict clearance, legal-question handling, and matter activation authority.

- No AI component may appear in the authority path. Optional AI assistance remains disabled in v1 except separately governed source-linked drafts for firm review.

- DocuSeal may be the initial e-sign adapter, but RETAINER remains provider-neutral.

- Redis may support locks, rate limits, and queues; canonical state remains in PostgreSQL/event storage.

- All material actions are tenant-scoped, policy-versioned, authority-gated, idempotent, and auditable.



## Immediate contract normalization gate

The deployed reports contain three event-envelope counts: 15, 17, and 18. The ontology YAML contains 17 listed required fields while its rules require schema versioning. RETAINER v1 therefore requires an 18-field EventEnvelope v1.0.1: the 17 ontology fields plus `schema_version`. The ontology/contracts package must be patched before cross-repository release.

| Contract issue | Normative RETAINER decision | Required action |

| --- | --- | --- |

| Event envelope | 18 required fields including schema_version | Publish JSON Schema; run contract tests in every repository |

| Authority classes | Six classes: SYS_ADMIN, FIRM_POLICY, STAFF_AUTH, ATTY_AUTH, CLIENT_AUTH, PROHIBITED | Do not collapse STAFF_AUTH into FIRM_POLICY |

| Event counts | Ontology events marked canonical; seeded/product events marked extension | Add canonical flag, owner and schema version |

| Runtime duplication | Shared contracts centralized; runtime implementations may remain local | Publish versioned truevow-contracts package |

| Matter creation ownership | Canonical activation command/API owns creation; RETAINER cannot insert directly | Name service owner and lock contract |



## Contents

1. Product mandate and boundaries

2. Current platform baseline

3. Users, authority and permissions

4. Customer and staff journeys

5. Functional scope and requirements

6. Experience architecture and screens

7. Domain and data architecture

8. Workflow/state-machine architecture

9. Event and command architecture

10. Service and deployment architecture

11. API contracts

12. Cross-product integration contracts

13. Templates, documents, consent and signatures

14. Communications and reminders

15. Security, privacy, retention and audit

16. Reliability, observability and operations

17. Testing and quality gates

18. Repository structure and coding standards

19. Build sequence and coding-agent work packages

20. Acceptance criteria and launch gates

21. Appendices and companion build pack



# 1. Product Mandate and Boundaries

## 1.1 Product statement

RETAINER turns a firm-approved prospective engagement into a completed, evidence-backed engagement workflow and an authorized matter activation. It automates administrative execution after the law firm supplies the required authority.

```text
Firm-reviewable Matter Candidate
        |
        v
Attorney representation decision
        |
        v
Conflict review and clearance
        |
        v
Approved package generation
        |
        v
Delivery, review, questions and signatures
        |
        v
Completed-copy delivery
        |
        v
Attorney-authorized matter activation
        |
        v
TRACE case-production handoff
```


## 1.2 Owned transition

| Input business state | Output business state | Success event |

| --- | --- | --- |

| Firm-approved representation pending engagement conditions | Completed engagement and activated Matter | matter.activated |



## 1.3 In scope for California v1

- Direct tenant-firm prospects supplied by INTAKE or authorized staff entry.

- California plaintiff personal-injury contingency agreements using tenant-attorney-approved templates.

- Attorney representation decision and responsible-attorney assignment.

- Deterministic tenant-scoped conflict search plus named-attorney clearance/hold.

- Template resolution, merge validation, package generation, preview, locking and delivery.

- Electronic transaction consent, secure portal review, questions, signatures and completed-copy delivery.

- Firm-configured email reminders; SMS remains separately gated by consent and configuration.

- Activation checklist, named-attorney activation authorization, canonical Matter activation and TRACE handoff.

- Complete audit, export, retention, legal hold and reconciliation support.



## 1.4 Explicitly out of scope

- TrueVow deciding whether to accept or reject representation.

- Automatic conflict clearance, waiver, or legal analysis.

- AI-generated legal explanations, fee negotiation, clause drafting or authority decisions.

- A cross-firm lead marketplace or TrueVow lawyer-referral network.

- Medical-malpractice, workers-compensation, hourly, flat-fee, joint-representation or translated-authoritative agreements in v1.

- Percentage-of-fee, percentage-of-recovery, or per-signed-client commercial pricing.

- Direct database coupling to INTAKE, SaaS Admin, TRACE or SETTLE.

- Case production, medical records, demand drafting, settlement decision, liens or disbursement.



## 1.5 Product principles

1. Authority before automation.

2. Business state before UI status.

3. Policy over hard-coded tenant behavior.

4. Immutable evidence over mutable logs.

5. Deterministic execution in the authority path.

6. Fail closed when authority, policy, tenant, document, consent or jurisdiction evidence is missing.

7. One canonical record owner; projections are rebuildable.

8. Provider-neutral adapters.

9. No cross-tenant data use.

10. Every exception becomes an explicit review task.



# 2. Current Platform Baseline

## 2.1 Deployed foundation supplied to RETAINER

| Foundation | Reported implementation | RETAINER dependency |

| --- | --- | --- |

| Ontology reference data | Authority actions, event catalog, state models, invariants, actors and entities seeded/queryable | Import IDs and validate startup compatibility |

| Authority Gate | AUTH-001 through AUTH-020 plus platform extensions; fail closed | Use for every reserved/material command |

| WorkflowRuntime | Shared registry-driven deterministic runtime | Load RETAINER state/transition/event registries |

| Event Store / Audit Store | Append-only, tenant-scoped, idempotent business events | Emit normalized envelope; preserve replayability |

| Policy Registry | Versioned firm policies and jurisdiction profiles | Resolve immutable snapshots per action |

| Consent Ledger | Append-only consent lifecycle | Electronic delivery, e-sign, SMS and revocation |

| Document Service | Immutable versions, SHA-256 hashes and signature evidence | Generate/lock/deliver package documents |

| Communication Service | Multi-channel send/receive, evidence and reminders | Transactional engagement communications |

| Integration Hub | Tenant-scoped integrations and sync tracking | E-sign, mail/SMS, matter activation, TRACE handoff |

| Tenant & Identity Core | Tenant isolation, role checks, attorney verification | Authentication and authorization source |



## 2.2 Foundation compatibility checks at startup

- Ontology registry version is supported.

- All six authority classes exist.

- Required canonical entities and events exist.

- EventEnvelope schema hash matches the shared package.

- WorkflowRuntime transition contract version is compatible.

- SaaS Admin reports effective jurisdiction and tenant-policy versions.

- Document, communication, consent, audit and integration adapters pass health checks.



## 2.3 RETAINER-owned versus shared records

| Record/capability | Canonical owner | RETAINER behavior |

| --- | --- | --- |

| Tenant, User, Role, Attorney verification | SaaS Admin / Shared Platform | Read via contract; cache as projection only |

| Matter Candidate and intake facts | INTAKE | Consume immutable handoff; do not mutate |

| Representation Decision | RETAINER | Create/version/emit events |

| Conflict Search/Candidate/Review | RETAINER | Create/version/emit events |

| Template approval and jurisdiction policy | SaaS Admin / Shared Platform | Resolve approved version |

| Engagement Workflow/Package/Question/Activation Checklist | RETAINER | Canonical aggregate ownership |

| Document Version, Communication, Consent, Audit Event | Shared Platform | Call shared service; store references |

| Matter and Responsible Attorney Assignment | Canonical Matter owner / Shared Business Core | Request activation; receive result |

| TRACE case-production context | TRACE | Emit/forward matter.activated manifest |

| SETTLE records | SETTLE | No direct v1 dependency |



# 3. Users, Authority and Permissions

## 3.1 Primary user roles

| Role | Primary RETAINER responsibilities | Reserved boundary |

| --- | --- | --- |

| Intake Coordinator / Staff | Prepare review, complete facts, initiate searches, prepare package, follow up | Cannot approve representation or clear conflict |

| Responsible Attorney | Approve/decline representation, define scope, clear/hold conflicts, answer legal questions, authorize activation | Cannot delegate reserved authority to software |

| Firm Administrator | Configure users, templates, policies, channels, integrations, entitlements | Administrative role does not create licensure |

| Prospective Client | Consent, review, ask questions, sign/decline, control communication choices | Cannot authorize firm legal judgment |

| Authorized Representative | Act within verified scope for another person | Authority never inferred solely from relationship |

| TrueVow Support | Technical assistance under just-in-time controlled access | No legal advice; no unrestricted tenant access |

| Automation / AI Actor | Execute deterministic administrative actions or produce nonauthoritative drafts/signals | Cannot self-authorize or exercise professional/client authority |



## 3.2 Normative authority classes

| Class | Meaning | RETAINER examples |

| --- | --- | --- |

| SYS_ADMIN | Administrative execution allowed by platform design. | Hashing, objective preflight, event recording, completed-copy delivery after gates |

| FIRM_POLICY | Execution allowed only under an effective tenant-approved policy. | Template resolution, delivery under approved policy, reminder cadence |

| STAFF_AUTH | Named authorized staff member must decide or approve. | Prepare review, initiate search, correct administrative facts |

| ATTY_AUTH | Licensed/authorized attorney must decide or approve. | Approve representation, clear conflict, answer legal questions, authorize activation |

| CLIENT_AUTH | Client or verified representative must decide or consent. | Electronic consent, signature, decline, communication revocation |

| PROHIBITED | TrueVow must not perform this action. | Self-approval, automatic case acceptance, AI legal explanation, cross-tenant use |



## 3.3 Permission model

Authorization is the intersection of authenticated identity, active tenant membership, role assignment, authority class, action registry, jurisdiction profile, tenant policy, aggregate state, required evidence and feature entitlement. A role name alone is never sufficient.

```text
allow = identity_valid
    AND tenant_active
    AND membership_active
    AND action_registered
    AND authority_satisfied
    AND jurisdiction_effective
    AND policy_effective
    AND state_allows_command
    AND evidence_complete
    AND entitlement_enabled

otherwise: fail_closed + audit denial
```


## 3.4 Core action matrix

| Action | Staff | Attorney | Client | Platform | AI |

| --- | --- | --- | --- | --- | --- |

| Prepare candidate review | Allowed | Allowed | - | Assist | Draft only |

| Approve/decline representation | No | Required | - | Record only | Prohibited |

| Run conflict search | Allowed by policy | Allowed | - | Execute | No authority |

| Clear/hold conflict | No | Required | Consent only if separately needed | Record only | Prohibited |

| Resolve approved template | Prepare | Approve policy/template | - | Execute | Prohibited in v1 |

| Explain legal term | No | Required | Ask/receive | Route only | Prohibited |

| Sign client agreement | No | - | Required | Capture | Prohibited |

| Send reminders | Configure/monitor | Configure/monitor | May revoke | Execute | No discretion |

| Authorize activation | Prepare checklist | Required in CA v1 | - | Validate/execute | Prohibited |



# 4. Customer and Staff Journeys

## 4.1 Happy path

1. INTAKE emits a versioned candidate handoff.

2. Staff reviews candidate facts and assigns attorney review.

3. Attorney approves representation for defined scope.

4. RETAINER performs tenant-scoped conflict search.

5. Attorney clears conflict or records approved exception.

6. Policy Registry resolves the approved California contingency template.

7. Document Service generates and locks the package after preflight.

8. Firm policy authorizes delivery.

9. Prospect consents to electronic transaction and receives a retainable package.

10. Prospect reviews; logistical questions are handled; legal questions route to the attorney.

11. Required client and firm signatures are captured with evidence.

12. Fully executed duplicate copy is delivered.

13. Activation checklist passes; attorney authorizes activation.

14. Canonical Matter owner activates idempotently and emits matter.activated.

15. TRACE consumes the event and creates its source-linked case-production context.



## 4.2 Conflict-hold path

```text
ATTORNEY_APPROVAL_RECORDED
        -> CONFLICT_REVIEW_PENDING
        -> CONFLICT_HOLD
        -> attorney review / waiver process outside automation
        -> either PACKAGE_PREPARATION or DECLINED_OR_EXPIRED
```


## 4.3 Legal-question path

```text
CLIENT_REVIEW
   -> engagement.question_received
   -> classification: logistical | legal_or_uncertain
   -> logistical: approved static/process response
   -> legal_or_uncertain: engagement.question_escalated + attorney work item
   -> attributable attorney response
   -> return to CLIENT_REVIEW / SIGNATURE_PENDING
```


## 4.4 Expiration, decline and withdrawal

- Firm-policy expiration stops reminders, preserves package/evidence, and records engagement.expired.

- Client decline records attributable CLIENT_AUTH and suppresses further engagement reminders.

- Attorney withdrawal before activation records authority and terminates the workflow.

- Reissue always creates a new package/workflow version after current policy/template checks; stale signed bytes are never reused.



## 4.5 Recovery and reconciliation journey

- Provider callbacks are idempotent and correlated to ceremony/delivery IDs.

- Unknown matter-activation outcomes enter reconciliation; RETAINER never infers success from timeout.

- Conflicting duplicate events are quarantined and create a security/operations work item.

- Projection rebuild is supported from immutable events and referenced shared records.



# 5. Functional Scope and Requirements

This specification defines **91 testable requirements**. P0 items are required for pilot; P1 items may be completed during controlled pilot hardening but their architecture must be supported from the start.

## 5.1 INTAKE handoff

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-INT-001 | Consume candidate handoff | The system shall consume a versioned Matter Candidate handoff through an authenticated contract, never by reading INTAKE database tables. | P0 | SYS_ADMIN | Contract + integration test |

| RET-INT-002 | Idempotent candidate import | The same candidate handoff event shall produce one RETAINER candidate projection and no duplicate workflow. | P0 | SYS_ADMIN | Duplicate-event test |

| RET-INT-003 | Preserve source references | Imported facts shall retain source entity IDs, source event IDs, source versions, and provenance links. | P0 | SYS_ADMIN | Data lineage test |

| RET-INT-004 | No source mutation | RETAINER shall not update, delete, or reinterpret authoritative INTAKE records. | P0 | PROHIBITED | Permission + contract test |

| RET-INT-005 | Tenant validation | The candidate tenant shall be active or trial and shall match the authenticated tenant context. | P0 | SYS_ADMIN | Negative security test |

| RET-INT-006 | Candidate version conflict | A conflicting candidate version shall create a discrepancy work item instead of silently overwriting the current projection. | P0 | FIRM_POLICY | Version-conflict test |

| RET-INT-007 | Incomplete candidate routing | Missing required administrative data shall create a completion task and shall not create attorney approval. | P0 | FIRM_POLICY | State + authority test |

| RET-INT-008 | Candidate withdrawal | A withdrawn or suppressed candidate shall stop RETAINER outreach and move any active workflow to a governed terminal path. | P0 | CLIENT_AUTH / FIRM_POLICY | E2E withdrawal test |



## 5.2 Representation decision

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-REP-001 | Attorney-attributable decision | Acceptance, decline, or deferral shall identify the named attorney, scope, timestamp, authority record, and decision version. | P0 | ATTY_AUTH | Authority + audit test |

| RET-REP-002 | No automated acceptance | No score, AI output, qualification status, timer, or workflow completion shall create representation approval. | P0 | PROHIBITED | Prohibited transition test |

| RET-REP-003 | Staff preparation only | Authorized staff may prepare a review record but may not emit the attorney approval event. | P0 | STAFF_AUTH | Role matrix test |

| RET-REP-004 | Decision scope required | Approval shall define practice area, matter type, represented parties, excluded parties, and intended scope sufficient for template resolution. | P0 | ATTY_AUTH | Validation test |

| RET-REP-005 | Responsible attorney assignment | An approved workflow shall identify at least one responsible attorney before activation. | P0 | ATTY_AUTH | Invariant test |

| RET-REP-006 | Decline workflow | An attorney decline shall create an immutable decision record and may authorize a firm-approved nonengagement communication. | P0 | ATTY_AUTH / FIRM_POLICY | E2E decline test |

| RET-REP-007 | Deferral workflow | A deferred decision shall retain the candidate in a review state with a due date, reason category, and assigned owner. | P1 | ATTY_AUTH | Timer/escalation test |

| RET-REP-008 | Decision supersession | A later decision shall supersede rather than mutate the earlier decision and shall preserve the full history. | P0 | ATTY_AUTH | Append-only test |



## 5.3 Conflict workflow

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-CON-001 | Deterministic conflict search | The system shall run tenant-scoped deterministic searches over configured party and relationship sources. | P0 | FIRM_POLICY | Search-scope test |

| RET-CON-002 | Search evidence | Every conflict search shall record inputs, normalized forms, sources searched, algorithm version, and completion timestamp. | P0 | FIRM_POLICY | Audit completeness test |

| RET-CON-003 | Candidate not clearance | A possible match or no-match result shall never be represented as attorney conflict clearance. | P0 | PROHIBITED | Copy + state test |

| RET-CON-004 | Attorney clearance | Conflict clearance, waiver, or hold resolution shall be attributable to a named attorney. | P0 | ATTY_AUTH | Authority test |

| RET-CON-005 | Conflict hold | A material unresolved conflict candidate shall block package preparation and delivery. | P0 | ATTY_AUTH | Fail-closed test |

| RET-CON-006 | Party-change invalidation | Adding or materially changing a party shall invalidate current conflict clearance and require a new search or attorney confirmation. | P0 | FIRM_POLICY / ATTY_AUTH | Invalidation test |

| RET-CON-007 | Search scope configuration | SaaS Admin shall define the systems and datasets included in the tenant conflict search profile. | P1 | FIRM_POLICY | Configuration contract test |

| RET-CON-008 | Manual conflict record | The product shall support manual review notes, decision rationale references, and uploaded supporting records without forcing disclosure to the client portal. | P1 | ATTY_AUTH | Permission test |

| RET-CON-009 | No cross-tenant conflict pool | Conflict data shall never be pooled or searched across unrelated tenants. | P0 | PROHIBITED | Cross-tenant penetration test |

| RET-CON-010 | Reopen after hold | A conflict hold may be released only through a new attorney-attributable decision that identifies the cleared scope or approved exception. | P0 | ATTY_AUTH | Transition test |



## 5.4 Templates and packages

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-TPL-001 | Approved template only | The system shall generate engagement documents only from an effective tenant-attorney-approved template. | P0 | FIRM_POLICY | Policy resolution test |

| RET-TPL-002 | California v1 scope | The initial jurisdiction module shall support California plaintiff personal-injury contingency agreements and explicitly exclude medical malpractice, workers compensation, hourly, and flat-fee workflows. | P0 | FIRM_POLICY | Feature-flag test |

| RET-TPL-003 | Version-locked template | Template text, approval, effective period, merge schema, jurisdiction, matter type, and hash shall be immutable for a released version. | P0 | ATTY_AUTH | Mutation test |

| RET-TPL-004 | Deterministic template mapping | Template selection shall use an approved mapping of jurisdiction, practice area, fee type, and firm policy. | P0 | FIRM_POLICY | Decision-table test |

| RET-TPL-005 | No AI clause selection | AI shall not select, create, rewrite, remove, or reorder substantive legal clauses in v1. | P0 | PROHIBITED | Prohibited-action test |

| RET-TPL-006 | Merge-field provenance | Every populated merge field shall record its source, validation status, and value version. | P0 | SYS_ADMIN | Provenance test |

| RET-TPL-007 | Required-field preflight | Package generation shall fail closed when required merge fields, disclosures, approvals, or template mappings are absent. | P0 | FIRM_POLICY | Negative preflight test |

| RET-TPL-008 | Document immutability | Every generated, delivered, or signed document version shall have a stable document ID, version ID, SHA-256 hash, and immutable content. | P0 | SYS_ADMIN | Hash + mutation test |

| RET-TPL-009 | Package manifest | An Engagement Package shall contain a manifest of documents, disclosures, signer requirements, delivery rules, and hashes. | P0 | FIRM_POLICY | Manifest validation test |

| RET-TPL-010 | Attorney revision flow | Substantive edits shall create a draft version, diff, named attorney approval, and new effective version; they shall never alter a delivered package. | P1 | ATTY_AUTH | Versioning E2E test |

| RET-TPL-011 | Preview parity | The attorney preview shall render the exact bytes that will be delivered and signed. | P0 | FIRM_POLICY | Byte/hash parity test |

| RET-TPL-012 | Translation exclusion | Authoritative translated legal agreements shall remain disabled until a separately approved translation workflow exists. | P1 | PROHIBITED | Feature flag test |



## 5.5 Client portal and questions

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-PRT-001 | Secure portal access | The client portal shall use tenant-branded, time-bounded, revocable access with step-up verification for sensitive actions. | P0 | CLIENT_AUTH | Security E2E test |

| RET-PRT-002 | Firm identity | The portal shall identify the tenant law firm as the legal-services provider and TrueVow as technology where appropriate. | P0 | FIRM_POLICY | Content snapshot test |

| RET-PRT-003 | Electronic consent | Before electronic delivery/signature, the portal shall capture affirmative, attributable consent and preserve revocation history. | P0 | CLIENT_AUTH | Consent lifecycle test |

| RET-PRT-004 | Retainable documents | Delivered records shall be downloadable or otherwise retainable by the recipient. | P0 | SYS_ADMIN | Download test |

| RET-PRT-005 | Client review state | Opening the package may move the experience projection to review but shall not count as consent, signature, or legal acceptance. | P0 | CLIENT_AUTH | State semantics test |

| RET-PRT-006 | Logistical help only | Approved portal help may explain access, signing, upload, and scheduling; legal interpretation shall route to the firm. | P0 | FIRM_POLICY | Content + escalation test |

| RET-PRT-007 | Question capture | The client may submit a question linked to the package, document, page, or clause without changing the document state. | P1 | CLIENT_AUTH | Portal E2E test |

| RET-PRT-008 | Attorney response attribution | Responses to legal questions shall identify the responding firm actor and shall not be generated as TrueVow legal advice. | P0 | ATTY_AUTH | Authority test |

| RET-PRT-009 | Alternative channel | A firm-approved non-electronic or assisted process shall be available when electronic consent is declined or accessibility assistance is requested. | P1 | FIRM_POLICY | Fallback workflow test |

| RET-PRT-010 | Client stop/decline | The client may decline the package or request no further automated reminders, and the system shall record and honor that choice. | P0 | CLIENT_AUTH | Suppression test |



## 5.6 Signatures

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-SIG-001 | Signature ceremony | Each signing session shall bind a signer, authority/capacity, document version, authentication context, and intent event. | P0 | CLIENT_AUTH / ATTY_AUTH | Evidence package test |

| RET-SIG-002 | Client signature authority | The platform shall never sign for the client; representative capacity shall be explicitly verified where applicable. | P0 | PROHIBITED | Prohibited-action test |

| RET-SIG-003 | Firm signatory authority | A firm signature shall require a valid attorney or authorized firm-signatory role and an attributable signing action. | P0 | ATTY_AUTH | Role + evidence test |

| RET-SIG-004 | Evidence package | Signature evidence shall include signer identity, intent, authentication method, timestamp, IP/device evidence where enabled, document hash, provider reference, and ceremony ID. | P0 | CLIENT_AUTH / ATTY_AUTH | Schema validation test |

| RET-SIG-005 | No image-only evidence | A pasted signature image or typed name shall not be the sole evidence of execution. | P0 | PROHIBITED | Negative evidence test |

| RET-SIG-006 | Required signer completion | The package shall become fully executed only when every required signer and acknowledgment requirement for the locked manifest is complete. | P0 | SYS_ADMIN | Transition guard test |

| RET-SIG-007 | Signature invalidation | An invalidated signature shall preserve the original evidence, record the reason and authority, and block execution until corrected. | P0 | FIRM_POLICY / ATTY_AUTH | Invalidation E2E test |

| RET-SIG-008 | Signed-version immutability | A signed document shall never be edited in place; amendments shall use a new package or formal amendment workflow. | P0 | PROHIBITED | Mutation test |

| RET-SIG-009 | Completed-copy delivery | The system shall deliver the fully executed duplicate copy and preserve delivery evidence before activation. | P0 | SYS_ADMIN | Delivery gate test |

| RET-SIG-010 | Provider abstraction | DocuSeal may be the initial adapter, but RETAINER domain records shall remain provider-neutral and portable. | P1 | FIRM_POLICY | Adapter contract test |



## 5.7 Communications and reminders

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-COM-001 | Transactional email | The system shall send firm-branded transactional emails through the shared Communication Service using approved templates and sender identity. | P0 | FIRM_POLICY | Template + delivery test |

| RET-COM-002 | Consent-aware SMS | SMS reminders shall remain feature-gated and shall execute only with effective channel consent, opt-out handling, and tenant policy. | P1 | FIRM_POLICY / CLIENT_AUTH | Consent/suppression test |

| RET-COM-003 | No automated voice in v1 | Automated reminder calls shall be disabled in California v1 unless separately approved and configured. | P1 | PROHIBITED | Feature flag test |

| RET-COM-004 | Reminder cadence | Reminder timing, maximum attempts, quiet hours, expiration, and escalation shall come from an immutable tenant policy snapshot. | P0 | FIRM_POLICY | Timer policy test |

| RET-COM-005 | Stop on revocation | Relevant automated communication shall stop after revocation, decline, withdrawal, expiration, or suppression. | P0 | CLIENT_AUTH / FIRM_POLICY | Suppression race test |

| RET-COM-006 | Delivery evidence | Every outbound communication shall preserve sender, recipient, channel, content version, policy version, attempt, provider ID, and result. | P0 | SYS_ADMIN | Audit completeness test |

| RET-COM-007 | Escalate failures | Repeated delivery failure or unanswered legal question shall create a human work item with SLA and owner. | P1 | FIRM_POLICY | Escalation test |

| RET-COM-008 | No marketing contamination | Engagement communications shall not include unrelated marketing content or restart suppressed nurture sequences. | P0 | PROHIBITED | Content policy test |



## 5.8 Activation and TRACE handoff

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-ACT-001 | Activation checklist | Activation shall evaluate a versioned checklist containing representation, conflict, attorney, agreement, delivery, consent, signature, jurisdiction, tenant, and firm-defined conditions. | P0 | FIRM_POLICY | Checklist contract test |

| RET-ACT-002 | Named attorney activation | California v1 shall require a named-attorney activation authorization even after objective checks pass. | P0 | ATTY_AUTH | Authority test |

| RET-ACT-003 | No candidate shortcut | A Matter Candidate shall never become a Matter directly from qualification, document generation, or signature completion. | P0 | PROHIBITED | Prohibited transition test |

| RET-ACT-004 | Command, not database insert | RETAINER shall request matter creation through the canonical activation command/API and shall not write another product database. | P0 | SYS_ADMIN | Architecture test |

| RET-ACT-005 | Idempotent activation | Repeated activation commands with the same idempotency key and evidence set shall return the same result without duplicate Matters. | P0 | SYS_ADMIN | Retry test |

| RET-ACT-006 | Activation evidence manifest | The activation command shall include references to representation decision, conflict clearance, responsible attorney, package, signatures, completed-copy delivery, jurisdiction profile, and policy versions. | P0 | FIRM_POLICY / ATTY_AUTH | Schema test |

| RET-ACT-007 | Matter activated event | Successful activation shall emit canonical matter.activated using the normalized 18-field envelope. | P0 | FIRM_POLICY | Contract test |

| RET-ACT-008 | TRACE handoff | TRACE shall consume matter.activated idempotently with a tenant-scoped transfer manifest and source references. | P0 | SYS_ADMIN | Cross-product E2E test |

| RET-ACT-009 | Activation failure reconciliation | Unknown, timed-out, or partial activation results shall enter reconciliation; RETAINER shall not infer success. | P0 | SYS_ADMIN | Chaos/reconciliation test |

| RET-ACT-010 | Reissue workflow | Expired or invalidated packages shall require renewed authority, current template resolution, and a new immutable package version. | P1 | FIRM_POLICY | Reissue E2E test |



## 5.9 Administration and shared platform

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-ADM-001 | SaaS Admin owns governance | Tenant users, roles, attorney verification, jurisdiction profiles, approved templates, communication policies, reminder policies, and entitlements shall remain governed through SaaS Admin contracts. | P0 | FIRM_POLICY | Ownership test |

| RET-ADM-002 | Immutable policy snapshot | Each material action shall store the exact effective policy/configuration version used at execution. | P0 | FIRM_POLICY | Audit test |

| RET-ADM-003 | Feature entitlements | RETAINER capabilities shall be enforced server-side using tenant entitlements and jurisdiction feature flags. | P0 | FIRM_POLICY | Entitlement bypass test |

| RET-ADM-004 | Template administration separation | SaaS Admin may manage metadata and approvals; RETAINER shall resolve and use approved versions without owning tenant identity or licensure truth. | P0 | ATTY_AUTH / FIRM_POLICY | Boundary test |

| RET-ADM-005 | Platform extensions registered | Any product-specific actor, event, action, state, or metric shall be registered with canonical/extension classification and version. | P0 | SYS_ADMIN | Registry lint test |

| RET-ADM-006 | No duplicate shared services | RETAINER shall consume shared contracts and adapters rather than create divergent definitions of authority, consent, documents, communications, audit, or integration types. | P0 | SYS_ADMIN | Dependency/duplicate-symbol test |

| RET-ADM-007 | Support access controls | TrueVow support access shall be least-privilege, reason-bound, time-bound, tenant-visible where policy requires, and audited. | P1 | FIRM_POLICY | JIT access test |

| RET-ADM-008 | Export portability | The firm shall be able to export engagement records, documents, evidence manifests, and audit history under tenant policy. | P1 | FIRM_POLICY | Export integrity test |



## 5.10 Audit and event controls

| ID | Requirement | Normative statement | Priority | Authority | Verification |

| --- | --- | --- | --- | --- | --- |

| RET-AUD-001 | Normalized event envelope | Every material RETAINER event shall use the shared envelope with the ontology fields plus required schema_version. | P0 | SYS_ADMIN | JSON Schema test |

| RET-AUD-002 | Append-only audit | Business audit evidence shall be append-only, tenant-scoped, idempotent by event_id, and independent of diagnostic logs. | P0 | SYS_ADMIN | Mutation/idempotency test |

| RET-AUD-003 | Authority linkage | Material events shall identify authority class and authority record; absence shall fail closed where authority is required. | P0 | SYS_ADMIN | Negative contract test |

| RET-AUD-004 | Correlation and causation | Commands, events, work items, communications, and provider callbacks shall preserve correlation_id and causation_id. | P0 | SYS_ADMIN | Trace test |

| RET-AUD-005 | No secrets in payload | Event payloads shall exclude credentials, private keys, raw access tokens, and unnecessary confidential document content. | P0 | PROHIBITED | Payload scanner test |

| RET-AUD-006 | Audit completeness | The system shall achieve 100 percent audit completeness for material RETAINER transitions before pilot activation. | P0 | SYS_ADMIN | Metric test |

| RET-AUD-007 | Replayability | A workflow shall be reconstructable from immutable commands/events plus referenced policy and document versions without relying on mutable logs. | P0 | SYS_ADMIN | Replay test |



# 6. Experience Architecture and Screens

## 6.1 Staff and attorney application information architecture

| Area | Primary screens | Primary records/actions |

| --- | --- | --- |

| Review | Representation Review Queue; Candidate Review | Matter Candidate projection, decision preparation, attorney assignment |

| Conflicts | Conflict Search; Candidate Detail; Attorney Conflict Decision | Search scope, matches, supporting records, clearance/hold |

| Packages | Template Resolution; Package Builder; Exact Preview | Template/version, merge fields, preflight, manifest, hashes |

| Engagements | Engagement Monitor; Timeline; Delivery/Signature Status | Workflow state, tasks, communications, signatures, expiration |

| Questions | Question Inbox; Question Thread | Classification, escalation, attorney response, SLA |

| Activation | Activation Checklist; Authorization; Reconciliation | Required conditions, evidence, command/result, TRACE handoff |

| Administration link-outs | SaaS Admin deep links | Users, attorneys, templates, policies, channels, integrations, entitlements |



## 6.2 Client portal screens

1. Access verification and firm identity.

2. Electronic transaction consent and delivery preference.

3. Package overview and downloadable documents.

4. Document review with clause/page question capture.

5. Legal-question waiting state and firm response.

6. Signature ceremony and signer intent.

7. Completion confirmation and completed-copy download.

8. Decline / stop reminders / accessibility assistance.



## 6.3 Screen-level rules

- Each screen has one primary action and displays the current authoritative business state separately from delivery/job status.

- Buttons for reserved actions include the required authority and never appear based only on a generic admin role.

- Every legal-sensitive automated result is labeled as a search result, draft, flag or administrative check—not a legal conclusion.

- Errors state what is missing and create a safe recovery path; no UI bypasses server-side gates.

- The client surface is tenant-branded and never presents TrueVow as the law firm.



## 6.4 Queue definitions

| Queue | Entry condition | Exit condition | SLA owner |

| --- | --- | --- | --- |

| Attorney review | Candidate current and review requested | Approved, declined or deferred | Named attorney / team policy |

| Conflict review | Search complete or material party changed | Attorney clearance/hold decision | Named attorney |

| Package completion | Approval+clearance present; data incomplete | Preflight passes | Staff |

| Legal questions | Question legal or uncertain | Attributable attorney response | Named attorney |

| Delivery failures | Provider reports failure / no retainable delivery | Successful retry or human resolution | Staff |

| Signature exceptions | Invalid/expired/mismatched signature evidence | Corrected ceremony or terminated workflow | Staff + attorney as needed |

| Activation reconciliation | Unknown/partial activation result | Canonical result established | Platform operations |



# 7. Domain and Data Architecture

## 7.1 RETAINER aggregates

| Aggregate | Purpose | Root / key invariants |

| --- | --- | --- |

| RepresentationDecision | Attorney-attributable accept/decline/defer decision | Append-only versions; attorney authority; defined scope |

| ConflictReview | Searches, possible matches and attorney clearance/hold | Search != candidate != clearance; party-set version |

| EngagementWorkflow | Canonical lifecycle orchestration | Only WorkflowRuntime transitions state; fail closed |

| TemplateResolution | Resolved effective template and policy inputs | Approved/effective version; deterministic mapping |

| EngagementPackage | Locked package manifest and shared document references | Immutable after delivery; hash parity |

| EngagementQuestion | Prospect question and firm response workflow | Legal/uncertain escalates; attributable response |

| SignatureCoordination | Ceremonies, signer requirements and evidence references | Signer authority, intent, document hash |

| ActivationChecklist | Versioned required conditions and evidence | All mandatory items pass; attorney activation authority |



## 7.2 RETAINER operational tables

| Table | Key columns | Notes |

| --- | --- | --- |

| retainer_workflows | id, tenant_id, candidate_id, state, version, decision_id, conflict_review_id, package_id, activation_checklist_id | Aggregate root; optimistic concurrency |

| representation_decisions | id, tenant_id, candidate_id, outcome, scope_json, attorney_actor_id, authority_record_id, supersedes_id | Append-only decision versions |

| conflict_searches | id, tenant_id, candidate_id, party_set_version, algorithm_version, scope_json, status | Deterministic search evidence |

| conflict_candidates | id, tenant_id, search_id, matched_party_ref, match_basis_json, score_or_rule, disposition | Possible matches only |

| conflict_reviews | id, tenant_id, search_id, outcome, attorney_actor_id, authority_record_id, rationale_ref | Clear/hold/exception |

| template_resolutions | id, tenant_id, workflow_id, template_definition_id, template_version, policy_version_id, inputs_json | Immutable snapshot |

| engagement_packages | id, tenant_id, workflow_id, manifest_json, status, package_hash, generated_at, locked_at | References shared DocumentVersion IDs |

| package_documents | package_id, document_version_id, role, required, sequence, hash | Manifest join |

| engagement_questions | id, tenant_id, workflow_id, document_version_id, page_or_clause_ref, classification, state, assigned_actor_id | Question workflow |

| signature_ceremonies | id, tenant_id, package_id, provider_type, provider_ref, state, expires_at | Provider-neutral |

| signer_requirements | id, ceremony_id, party_role_id, signer_role, authority_scope, required | Expected signers |

| signature_evidence_refs | id, ceremony_id, signer_requirement_id, shared_signature_evidence_id, validity_state | Shared evidence reference |

| activation_checklists | id, tenant_id, workflow_id, policy_version_id, state, version | Checklist root |

| activation_checklist_items | id, checklist_id, control_id, required, result, evidence_refs_json, evaluated_at | Objective/authority gates |

| reminder_schedules | id, tenant_id, workflow_id, policy_version_id, next_due_at, max_attempts, state | No canonical state mutation |

| reminder_attempts | id, schedule_id, communication_id, attempt_no, result | Communication evidence |

| retainer_inbox_events | event_id, tenant_id, event_type, schema_version, received_at, processed_at, payload_hash, result | Inbox/idempotency |

| retainer_outbox_events | event_id, tenant_id, aggregate_id, event_type, schema_version, payload_json, published_at | Transactional outbox |

| retainer_idempotency_keys | tenant_id, key, command_type, request_hash, result_ref, expires_at | Command safety |

| retainer_projection_checkpoints | projection_name, tenant_id, last_event_position, rebuilt_at | Rebuildable views |



## 7.3 Shared references, not duplicated records

- Tenant, User, Actor, RoleAssignment, JurisdictionProfile, FirmPolicy, AuthorityRecord and Entitlement IDs.

- Person, Organization, PartyRole, ContactPoint and PersonalRepresentativeAuthority IDs.

- MatterCandidate, Inquiry, IntakeSession, IntakeResponse and ConsentRecord IDs.

- TemplateDefinition, Document, DocumentVersion, SignatureEvidence, Communication, Notification, AuditEvent and WorkItem IDs.

- Matter, RepresentationRelationship and ResponsibleAttorneyAssignment IDs after activation.



## 7.4 Data ownership and consistency

RETAINER stores references and immutable snapshots necessary to explain its own decisions. It does not duplicate mutable identity, policy, document bytes or Matter truth. Cross-service consistency uses commands/events, idempotency keys, outbox/inbox and reconciliation—not distributed database transactions.

## 7.5 Sensitivity and retention defaults

| Data class | Examples | Default controls |

| --- | --- | --- |

| PROSPECT_CONFIDENTIAL | Candidate facts, conflict data, questions | Tenant isolation, encryption, restricted roles, audit |

| CLIENT_CONFIDENTIAL | Executed package, signer evidence after activation | Same plus matter access policy |

| ATTORNEY_WORK_PRODUCT | Conflict rationale, internal review notes | Exclude from client portal; strict access |

| IDENTITY_AUTH | Access tokens, authentication evidence | Never in event payload; short retention where appropriate |

| OPERATIONAL_METADATA | State, task, delivery result | Tenant scoped; minimize embedded confidential text |



# 8. Workflow and State-Machine Architecture

## 8.1 Canonical Engagement Workflow states

| State | Meaning |

| --- | --- |

| NOT_STARTED | No firm-approved engagement workflow exists. |

| ATTORNEY_APPROVAL_RECORDED | Representation approval and scope are attributable. |

| CONFLICT_REVIEW_PENDING | Potential conflicts await review. |

| CONFLICT_HOLD | Workflow blocked by unresolved conflict concern. |

| PACKAGE_PREPARATION | Approved templates and facts are being assembled. |

| DELIVERY_AUTHORIZED | Required authority to deliver has been verified. |

| DELIVERED | Package reached the intended recipient. |

| CLIENT_REVIEW | Prospect is reviewing, asking questions, or awaiting counsel discussion. |

| SIGNATURE_PENDING | Required signatures are outstanding. |

| FULLY_EXECUTED | Required parties signed the locked package version. |

| ACTIVATION_PENDING | Non-signature activation conditions remain. |

| ACTIVATED | Matter and representation relationship were created. |

| DECLINED_OR_EXPIRED | Prospect declined, authorization was withdrawn, or package expired. |



## 8.2 State diagram

```text
NOT_STARTED
  | ApproveRepresentation
  v
ATTORNEY_APPROVAL_RECORDED
  | RequestConflictReview
  v
CONFLICT_REVIEW_PENDING ---- ApplyConflictHold ---> CONFLICT_HOLD
  | ClearConflict                                  | ClearConflict
  +------------------------------------------------+
  v
PACKAGE_PREPARATION
  | AuthorizeDelivery
  v
DELIVERY_AUTHORIZED
  | DeliverPackage
  v
DELIVERED
  | BeginClientReview / RequestSignatures
  v
CLIENT_REVIEW ---> SIGNATURE_PENDING
                      | MarkFullyExecuted
                      v
                 FULLY_EXECUTED
                      | DeliverCompletedCopy
                      v
                 ACTIVATION_PENDING
                      | ConfirmMatterActivated
                      v
                   ACTIVATED

Any permitted pre-activation state -> DECLINED_OR_EXPIRED through an authorized terminal command
```


## 8.3 Transition registry

| ID | Command | From | To | Authority | Key guards | Event |

| --- | --- | --- | --- | --- | --- | --- |

| TR-RET-001 | ApproveRepresentation | NOT_STARTED | ATTORNEY_APPROVAL_RECORDED | ATTY_AUTH | tenant.active_or_trial, candidate.current, actor.verified_attorney | representation.approved_by_attorney |

| TR-RET-002 | DeclineRepresentation | NOT_STARTED | DECLINED_OR_EXPIRED | ATTY_AUTH | tenant.active_or_trial, candidate.current, actor.verified_attorney | representation.declined_by_attorney |

| TR-RET-003 | RequestConflictReview | ATTORNEY_APPROVAL_RECORDED | CONFLICT_REVIEW_PENDING | FIRM_POLICY | search.completed, search.tenant_scoped | conflict.review_requested |

| TR-RET-004 | ApplyConflictHold | CONFLICT_REVIEW_PENDING, PACKAGE_PREPARATION | CONFLICT_HOLD | ATTY_AUTH | actor.verified_attorney | conflict.hold_applied |

| TR-RET-005 | ClearConflict | CONFLICT_REVIEW_PENDING, CONFLICT_HOLD | PACKAGE_PREPARATION | ATTY_AUTH | actor.verified_attorney, party_set.current | conflict.cleared_by_attorney |

| TR-RET-006 | ResolveTemplate | PACKAGE_PREPARATION | PACKAGE_PREPARATION | FIRM_POLICY | jurisdiction_profile.effective, template.approved, template.current | template.resolved |

| TR-RET-007 | GeneratePackage | PACKAGE_PREPARATION | PACKAGE_PREPARATION | FIRM_POLICY | template.resolved, merge_fields.valid, required_disclosures.present | package.generated |

| TR-RET-008 | AuthorizeDelivery | PACKAGE_PREPARATION | DELIVERY_AUTHORIZED | FIRM_POLICY | representation.approved, conflict.cleared, package.locked, tenant.active_or_trial | package.delivery_authorized |

| TR-RET-009 | DeliverPackage | DELIVERY_AUTHORIZED | DELIVERED | SYS_ADMIN | channel.allowed, recipient.verified, package.hash_matches | package.delivered |

| TR-RET-010 | BeginClientReview | DELIVERED | CLIENT_REVIEW | CLIENT_AUTH | access.valid, package.current | engagement.client_review_started |

| TR-RET-011 | RequestSignatures | DELIVERED, CLIENT_REVIEW | SIGNATURE_PENDING | FIRM_POLICY | esign_consent.effective, signer_requirements.complete | signature.requested |

| TR-RET-012 | ApplySignature | SIGNATURE_PENDING | SIGNATURE_PENDING | CLIENT_AUTH / ATTY_AUTH | signer.authenticated, intent.captured, document.hash_matches | signature.applied |

| TR-RET-013 | InvalidateSignature | SIGNATURE_PENDING, FULLY_EXECUTED | SIGNATURE_PENDING | FIRM_POLICY / ATTY_AUTH | reason.recorded, actor.authorized | signature.invalidated |

| TR-RET-014 | MarkFullyExecuted | SIGNATURE_PENDING | FULLY_EXECUTED | SYS_ADMIN | all_required_signatures.valid, all_acknowledgments.complete, package.hash_matches | package.fully_executed |

| TR-RET-015 | DeliverCompletedCopy | FULLY_EXECUTED | ACTIVATION_PENDING | SYS_ADMIN | delivery.retainable, final_hash.matches | completed_copy.delivered |

| TR-RET-016 | AuthorizeMatterActivation | ACTIVATION_PENDING | ACTIVATION_PENDING | ATTY_AUTH | checklist.all_required_pass, actor.verified_attorney | matter.activation_authorized |

| TR-RET-017 | ConfirmMatterActivated | ACTIVATION_PENDING | ACTIVATED | FIRM_POLICY | matter_id.present, activation_id.matches, event.valid | matter.activated |

| TR-RET-018 | ExpireEngagement | ATTORNEY_APPROVAL_RECORDED, CONFLICT_REVIEW_PENDING, CONFLICT_HOLD, PACKAGE_PREPARATION, DELIVERY_AUTHORIZED, DELIVERED, CLIENT_REVIEW, SIGNATURE_PENDING, FULLY_EXECUTED, ACTIVATION_PENDING | DECLINED_OR_EXPIRED | FIRM_POLICY | policy.due, no_activation_success | engagement.expired |

| TR-RET-019 | RecordClientDecline | DELIVERED, CLIENT_REVIEW, SIGNATURE_PENDING | DECLINED_OR_EXPIRED | CLIENT_AUTH | actor.matches_recipient | engagement.declined_by_client |

| TR-RET-020 | WithdrawAuthorization | ATTORNEY_APPROVAL_RECORDED, CONFLICT_REVIEW_PENDING, CONFLICT_HOLD, PACKAGE_PREPARATION, DELIVERY_AUTHORIZED, DELIVERED, CLIENT_REVIEW, SIGNATURE_PENDING, FULLY_EXECUTED, ACTIVATION_PENDING | DECLINED_OR_EXPIRED | ATTY_AUTH | actor.verified_attorney, matter.not_activated | engagement.authorization_withdrawn |



## 8.4 Runtime rules

- Only WorkflowRuntime may mutate `retainer_workflows.state`.

- Every command supplies expected aggregate version; mismatches return a retryable concurrency error.

- A transition contract names prior states, destination, authority, evidence, guards, event and fail-closed behavior.

- Self-transitions may record material events without inventing UI/job states.

- Delivery queues, provider jobs, reminders and projections never redefine canonical workflow state.

- Terminal workflow reissue creates a new workflow/package version rather than rewriting history.



# 9. Event and Command Architecture

## 9.1 EventEnvelope v1.0.1

The normalized contract contains 18 required fields. `schema_version` is the explicit patch needed to make the ontology rule `schema_versioned` executable.

| Field | Purpose |

| --- | --- |

| event_id | Globally unique idempotency key |

| event_type | Stable dot-notated event name |

| occurred_at | Business occurrence time |

| recorded_at | Event-store persistence time |

| tenant_id | Non-null tenant boundary |

| aggregate_type | Canonical aggregate type |

| aggregate_id | Aggregate identifier |

| aggregate_version | Version after event |

| actor_type | Actor classification |

| actor_id | Attributable actor/reference |

| authority_class | One of six canonical classes |

| authority_record_id | Evidence of authority where required |

| policy_version_id | Exact policy/configuration snapshot |

| correlation_id | End-to-end workflow trace |

| causation_id | Immediate causal command/event |

| payload | Schema-validated minimal payload |

| sensitivity_class | Handling/retention classification |

| schema_version | Payload/envelope schema version |



## 9.2 Canonical RETAINER events

- conflict.search_started

- conflict.candidate_detected

- conflict.review_requested

- conflict.cleared_by_attorney

- conflict.hold_applied

- representation.approved_by_attorney

- representation.declined_by_attorney

- engagement.workflow_started

- template.resolved

- package.generated

- package.delivery_authorized

- esign.consent_granted

- package.delivered

- engagement.question_received

- engagement.question_escalated

- signature.applied

- signature.invalidated

- package.fully_executed

- completed_copy.delivered

- matter.activation_authorized

- matter.activated

- engagement.expired



## 9.3 RETAINER/product extension events

| Event | Owner | Canonical? | Schema |

| --- | --- | --- | --- |

| candidate.submitted_for_representation_review | INTAKE | false | 1.0.0 |

| engagement.client_review_started | RETAINER | false | 1.0.0 |

| signature.requested | RETAINER | false | 1.0.0 |

| engagement.declined_by_client | RETAINER | false | 1.0.0 |

| engagement.authorization_withdrawn | RETAINER | false | 1.0.0 |

| engagement.delivery_failed | RETAINER | false | 1.0.0 |

| engagement.reminder_sent | RETAINER | false | 1.0.0 |

| engagement.reminder_suppressed | RETAINER | false | 1.0.0 |

| engagement.reconciliation_required | RETAINER | false | 1.0.0 |



## 9.4 Command semantics

- Commands are imperative requests and are not facts.

- A command carries actor, authority evidence, policy snapshot reference, expected aggregate version and idempotency key.

- A rejected command emits an audit denial/operational result but does not emit the requested business event.

- Events are past-tense facts and never instruct consumers to perform legal judgment.



## 9.5 Delivery guarantees

| Concern | Control |

| --- | --- |

| Producer atomicity | Domain write + outbox event in one local database transaction |

| At-least-once delivery | Outbox publisher retries with backoff |

| Consumer idempotency | Inbox keyed by event_id and payload hash |

| Ordering | Per aggregate_version monotonic validation; gaps trigger reconciliation |

| Schema evolution | Backward-compatible additive changes within major; explicit adapter for breaking version |

| Poison events | Quarantine with tenant-safe metadata and human work item |

| Replay | Consumer/projection checkpoints; no side-effect replay without explicit mode |



# 10. Service and Deployment Architecture

## 10.1 Recommended repository/deployables

```text
TrueVow-RETAINER/
  apps/
    web/              # Next.js staff/attorney + client portal
    api/              # FastAPI command/query API
  workers/
    workflow/         # timers, reminders, escalations
    events/           # inbox/outbox, projections, reconciliation
  packages/
    retainer-domain/
    retainer-contracts/
    ui/
  registries/
  alembic/
  tests/
  docs/
```


## 10.2 Logical components

| Component | Responsibility | Must not do |

| --- | --- | --- |

| RETAINER Web | Firm workflows, client portal, accessible experience | Enforce authority only in browser |

| RETAINER API | Commands, queries, auth context, orchestration | Read other product databases |

| RETAINER Domain | Aggregates, invariants, command handlers | Call providers directly |

| Workflow Worker | Timers, reminders, work-item escalation | Mutate canonical state outside runtime |

| Event Worker | Outbox publish, inbox consume, projections, reconciliation | Infer legal/business success from transport success |

| Shared adapters | Authority, policy, consent, document, communication, audit, integration | Redefine shared contracts |

| PostgreSQL | RETAINER aggregates, inbox/outbox, projections | Store credentials or mutable shared truth |

| Redis (optional) | Short locks, rate limits, queue coordination | Permanent business state |



## 10.3 Technology baseline

- Python 3.12+ / FastAPI / Pydantic v2 / SQLAlchemy 2 / Alembic.

- Next.js with TypeScript and server-side authorization-aware data access.

- PostgreSQL with tenant_id on every tenant-owned table and RLS where supported.

- Shared `truevow-contracts` package generated from registry/schema sources.

- Transactional outbox/inbox; message transport may be PostgreSQL polling initially and NATS or another broker later without changing contracts.

- Object bytes remain in shared Document Service storage; RETAINER stores references/hashes.



## 10.4 Deployment environments

| Environment | Purpose | Data policy |

| --- | --- | --- |

| local | Developer workflows and contract tests | Synthetic data only |

| test | Automated integration/chaos tests | Synthetic fixtures |

| staging | Full provider sandbox and migration rehearsal | Synthetic/de-identified only |

| pilot | Selected California tenant(s) | Production controls; feature flags; heightened audit |

| production | Approved supported tenants/jurisdictions | Full SLO, backup, retention, incident controls |



# 11. API Contracts

## 11.1 API conventions

- Base path `/api/v1` and explicit versioned schemas.

- Tenant is derived from authenticated context and cross-checked against resource tenant.

- Mutating requests require `Idempotency-Key` and expected aggregate version.

- Reserved actions require authority evidence reference; server evaluates it.

- Responses include canonical resource IDs, version, state and correlation ID.

- Errors use stable machine codes and never leak cross-tenant existence.



## 11.2 Primary command endpoints

| Method/path | Purpose | Required authority |

| --- | --- | --- |

| POST /candidates/import | Internal candidate handoff intake | SYS_ADMIN service identity |

| POST /candidates/{id}/decisions | Approve, decline or defer representation | ATTY_AUTH |

| POST /workflows/{id}/conflict-searches | Run configured conflict search | FIRM_POLICY / STAFF_AUTH |

| POST /conflict-reviews/{id}/decisions | Clear, hold or approve exception | ATTY_AUTH |

| POST /workflows/{id}/template-resolution | Resolve effective approved template | FIRM_POLICY |

| POST /workflows/{id}/packages | Generate package after preflight | FIRM_POLICY / STAFF_AUTH |

| POST /packages/{id}/authorize-delivery | Authorize delivery | FIRM_POLICY |

| POST /packages/{id}/deliver | Execute delivery | SYS_ADMIN after gate |

| POST /portal/sessions | Create/redeem secure portal session | CLIENT_AUTH context |

| POST /workflows/{id}/questions | Submit question | CLIENT_AUTH |

| POST /questions/{id}/responses | Respond to escalated question | ATTY_AUTH where legal |

| POST /packages/{id}/signature-ceremonies | Create provider-neutral ceremony | FIRM_POLICY |

| POST /signature-callbacks/{provider} | Receive verified provider callback | Provider service identity |

| POST /workflows/{id}/activation-checklists/evaluate | Evaluate objective checklist | SYS_ADMIN |

| POST /workflows/{id}/authorize-activation | Named-attorney authorization | ATTY_AUTH |

| POST /workflows/{id}/activate | Send canonical activation command | FIRM_POLICY after gates |

| POST /workflows/{id}/expire | Apply firm expiration policy | FIRM_POLICY |

| POST /workflows/{id}/withdraw | Withdraw pre-activation authorization | ATTY_AUTH |



## 11.3 Primary query endpoints

| Method/path | Purpose |

| --- | --- |

| GET /review-queue | Tenant-scoped representation review projection |

| GET /workflows/{id} | Workflow detail and current evidence summary |

| GET /workflows/{id}/timeline | Material event timeline |

| GET /conflict-reviews/{id} | Search scope, matches and decision history |

| GET /packages/{id} | Manifest, versions, preflight and delivery/signature status |

| GET /questions | Tenant/assignee question queue |

| GET /activation-queue | Checklist and reconciliation projection |

| GET /portal/packages/{token} | Authorized client package projection |



## 11.4 Error codes

| Code | Meaning | Retry? |

| --- | --- | --- |

| RET_AUTHORITY_MISSING | Required authority/evidence absent | No until corrected |

| RET_POLICY_INACTIVE | No effective policy/profile | No until configured |

| RET_STATE_CONFLICT | Command not allowed from current state/version | Refresh/re-evaluate |

| RET_TENANT_MISMATCH | Tenant boundary mismatch | No; security event |

| RET_TEMPLATE_UNRESOLVED | No effective approved template | No until configured |

| RET_PREFLIGHT_FAILED | Required package data/control missing | After correction |

| RET_DOCUMENT_HASH_MISMATCH | Bytes differ from locked version | No; incident/reconciliation |

| RET_CONSENT_NOT_EFFECTIVE | Required consent absent/revoked | After valid consent |

| RET_SIGNATURE_INVALID | Signature evidence invalid or mismatched | After re-execution |

| RET_ACTIVATION_UNKNOWN | Activation result uncertain | Reconciliation only |



# 12. Cross-Product Integration Contracts

## 12.1 INTAKE -> RETAINER candidate handoff

```text
event_type: candidate.submitted_for_representation_review
required references:
  tenant_id
  matter_candidate_id
  candidate_version
  prospective_client_party_role_ids[]
  intake_session_ids[]
  qualification_assessment_id?
  consent_record_ids[]
  communication_ids[]
  source_event_ids[]
  submitted_by_actor_id
  submitted_at
constraints:
  - candidate is not a Matter
  - no representation approval implied
  - immutable source references
  - idempotent by event_id
```


## 12.2 SaaS Admin -> RETAINER governance resolution

| Contract | Inputs | Outputs |

| --- | --- | --- |

| ResolveActionAuthority | tenant, actor, action, aggregate, state | allow/deny, authority class, record ID, reason |

| ResolvePolicySnapshot | tenant, policy type, effective time, jurisdiction | immutable policy ID/version/hash |

| ResolveJurisdictionProfile | tenant, jurisdiction, workflow type | status, effective version, enabled controls |

| ResolveTemplate | tenant, jurisdiction, matter type, fee type, effective time | approved template/version/hash/merge schema |

| ResolveEntitlements | tenant, product/capability | enabled, limits, effective version |

| ResolveActor | tenant, user/actor, action | roles, attorney verification, authority eligibility |



## 12.3 RETAINER -> canonical Matter activation

```text
command: ActivateMatter
idempotency_key: <workflow_id>:<activation_version>
evidence:
  representation_decision_id
  conflict_review_id
  engagement_workflow_id
  engagement_package_id
  executed_document_version_ids[]
  signature_evidence_ids[]
  completed_copy_delivery_id
  responsible_attorney_assignment_request
  jurisdiction_profile_version_id
  activation_policy_version_id
  activation_authority_record_id
  source_manifest_hash
result:
  activation_id
  matter_id
  representation_relationship_id
  responsible_attorney_assignment_id
  aggregate_version
  event_id
```


## 12.4 matter.activated -> TRACE

- TRACE consumes the canonical event, not RETAINER private tables.

- TRACE verifies tenant, schema, activation evidence references and idempotency.

- TRACE stores source references and creates its case-production context only once.

- Unknown/unsupported events enter reconciliation without changing case state.



## 12.5 SETTLE relationship

There is no direct RETAINER-to-SETTLE dependency in v1. SETTLE may later retrieve the executed fee agreement, scope, amendments and authority records through shared Matter/Document services using tenant permissions. It must not call RETAINER private storage.

# 13. Templates, Documents, Consent and Signatures

## 13.1 Template governance

1. Draft template created under tenant.

2. Named attorney reviews and approves exact version.

3. Jurisdiction, practice area, fee arrangement, effective dates and merge schema assigned.

4. SHA-256 hash and approval evidence stored.

5. SaaS Admin activates mapping policy.

6. Supersession creates new version; prior versions remain available for evidence.



## 13.2 Package preflight controls

| Control | Failure behavior |

| --- | --- |

| Effective California jurisdiction profile | Block |

| Attorney-approved template/version | Block |

| Current representation approval/scope | Block |

| Current conflict clearance for current party set | Block |

| Required client/firm identity fields | Block |

| Fee rate and scope selected by attorney/policy | Block |

| Required disclosures and acknowledgments | Block |

| Merge-field provenance and validation | Block |

| Preview bytes/hash parity | Block |



## 13.3 Consent ledger uses

| Consent type | Required before | Revocation effect |

| --- | --- | --- |

| Electronic transaction | Electronic delivery/signature | Stop new e-sign activity; offer approved alternative |

| SMS | Automated SMS reminder | Suppress SMS immediately |

| Recording/transcription | Any recorded engagement communication | Stop future recording; preserve history per policy |

| Data sharing/integration | Feature-specific external transmission where required | Disable future transmission; route review |



## 13.4 Signature-provider adapter contract

- Create ceremony with document hashes and signer requirements.

- Generate provider session/link without exposing provider-specific IDs as canonical identities.

- Verify callback authenticity and replay protection.

- Map provider status to canonical ceremony/evidence states.

- Fetch final bytes and confirm hashes.

- Store provider raw evidence under retention policy while preserving normalized SignatureEvidence.

- Support cancellation, expiration, invalidation and export.



# 14. Communications and Reminders

## 14.1 Message classes

| Class | Examples | Controls |

| --- | --- | --- |

| Transactional | Package available, signature needed, completed copy, delivery failure | Firm identity, content version, permitted channel |

| Legal-question notice | Question assigned, attorney response available | No legal content in notification unless approved |

| Reminder | Unsigned package, incomplete consent | Policy cadence, quiet hours, attempt limits, suppression |

| Operational escalation | Delivery failed, SLA breached, activation unknown | Internal recipient and work item |

| Marketing | Not part of RETAINER engagement stream | Must remain separate and respect suppression |



## 14.2 Reminder policy fields

```text
policy_id, version, channels, initial_delay, intervals[], max_attempts, quiet_hours,
expiration_after, stop_conditions[], escalation_after, sender_profile_id,
message_template_versions, jurisdiction_scope, effective_from, effective_to
```


## 14.3 Stop conditions

- All required signatures complete.

- Client declines or revokes channel consent.

- Attorney withdraws authorization.

- Package expires or is superseded.

- Tenant becomes inactive.

- Security/compliance hold.

- Recipient contact point becomes invalid or suppressed.



# 15. Security, Privacy, Retention and Audit

## 15.1 Tenant isolation

- Every RETAINER table row carries non-null tenant_id and indexed access path.

- Authorization derives tenant from identity context; request tenant values are never trusted alone.

- RLS and application-layer checks both enforce isolation where available.

- Object/document access uses tenant-scoped shared-service authorization and short-lived URLs.

- Cross-tenant identifiers return not-found behavior and create security telemetry.



## 15.2 Security controls

| Control area | Requirement |

| --- | --- |

| Authentication | Firm SSO/session through shared identity; secure client portal tokens with revocation/step-up |

| Authorization | Server-side Authority Gate on every command and sensitive query |

| Encryption | TLS in transit; encryption at rest; shared key-management policy |

| Secrets | Managed secret store; never database/event payload/source control |

| Support access | Just-in-time, reason-bound, time-limited, audited |

| Callbacks | Signature verification, replay protection, provider IP/rate controls where appropriate |

| Rate limiting | Tenant/user/token/provider limits; abuse detection |

| Dependency security | Pinned dependencies, SBOM, vulnerability scanning, secret scanning |

| Secure SDLC | Threat model, code review, SAST, DAST, penetration testing |



## 15.3 Retention and deletion

- Retention class is assigned to each aggregate, document/evidence reference and event.

- Legal hold overrides ordinary deletion.

- Subscription termination does not automatically delete engagement evidence.

- Deletion is a governed, auditable process after tenant instruction and retention/hold checks.

- Exports include manifests and checksums; exported data does not remove the platform retention duty until deletion is authorized.



## 15.4 Audit event minimum

Every material action records tenant, event ID/type/schema, actor, authority, policy version, aggregate/version, prior and resulting state where applicable, correlation/causation, evidence references, result, timestamp and sensitivity class. Diagnostic logs may point to event IDs but are not the source of business evidence.

# 16. Reliability, Observability and Operations

## 16.1 Service objectives

| Measure | Pilot target | Notes |

| --- | --- | --- |

| API availability | 99.9% monthly excluding planned maintenance | Authority/policy dependencies included in critical path |

| Command p95 latency | < 750 ms excluding external document/e-sign operations | Reserved actions may require external checks |

| Query p95 latency | < 500 ms | Tenant-scoped projections |

| Outbox publication | 99% within 30 seconds; 100% eventual or alerted | No silent event loss |

| Reminder timer accuracy | Within 5 minutes of policy due time | Respect quiet hours |

| Audit completeness | 100% material events | Launch blocker |

| Cross-tenant incidents | 0 | Launch/incident severity critical |

| Document hash mismatches | 0 unresolved | Security/activation blocker |



## 16.2 Required telemetry

- Command counts, success/deny/failure by action and reason.

- Workflow counts by canonical state and age.

- Attorney review and conflict review latency.

- Package preflight failures by control.

- Delivery and signature provider latency/failure.

- Question SLA and escalation counts.

- Activation success/unknown/reconciliation counts.

- Outbox/inbox lag and poison events.

- Policy/version coverage and audit completeness.

- Tenant isolation denials and security exceptions.



## 16.3 Operational runbooks

1. Signature provider outage.

2. Email/SMS provider outage.

3. Document hash mismatch.

4. Authority or policy service unavailable.

5. Matter activation timeout/unknown result.

6. Outbox backlog or duplicate event conflict.

7. Cross-tenant access alert.

8. Client portal token compromise.

9. Template/policy emergency supersession.

10. Data export, legal hold and tenant offboarding.



# 17. Testing and Quality Gates

## 17.1 Test pyramid

| Layer | Coverage |

| --- | --- |

| Registry/schema lint | YAML/JSON/OpenAPI validity, canonical IDs, no duplicate event/state/action names |

| Unit | Aggregates, invariants, policy decisions, merge validation, hash/evidence logic |

| State-machine contract | Every transition allowed/denied from every state and authority class |

| Service integration | Shared authority/policy/consent/document/communication/audit adapters |

| Cross-product contract | INTAKE handoff, SaaS Admin resolution, Matter activation, TRACE consumption |

| E2E browser/API | Staff happy/exception paths and client portal/signature paths |

| Security | Tenant isolation, role bypass, token abuse, callback forgery, injection, IDOR |

| Resilience/chaos | Provider outages, duplicate/gap/reordered events, timeouts, retries, projection rebuild |

| Migration | Forward/backward compatibility, rollback, reference-data version checks |



## 17.2 Mandatory negative tests

- Staff attempts to approve representation.

- No-match conflict search attempts to clear conflict.

- AI/service actor attempts self-authorization.

- Inactive tenant attempts delivery/signature/activation.

- Delivered document bytes differ from locked hash.

- Client signs a different document version.

- Revoked SMS consent followed by scheduled reminder.

- Matter activation called without completed-copy delivery.

- Duplicate activation command with changed payload.

- Cross-tenant candidate/package/token access.

- Unsupported jurisdiction/profile/template.

- Missing schema_version in event.



## 17.3 Acceptance scenario catalog

The companion build pack includes executable-style YAML scenarios covering happy path, decline, defer, conflict hold, party-change invalidation, question escalation, consent decline, signature invalidation, provider outage, expiration, withdrawal, activation timeout, duplicate events and cross-tenant denial.

## 17.4 CI release gates

1. All unit/integration/contract/security tests pass.

2. Ruff, type checking, ESLint/TypeScript and formatting pass.

3. Database migration upgrade/downgrade rehearsal passes.

4. Shared contract compatibility matrix passes against deployed versions.

5. No P0 requirement lacks a passing test reference.

6. Threat model and dependency/SBOM checks pass.

7. Audit completeness and tenant-isolation test suites pass 100 percent.

8. Staging E2E with provider sandboxes passes.



# 18. Repository Structure and Coding Standards

## 18.1 Suggested tree

```text
apps/api/app/
  api/v1/
  domain/
    representation/
    conflicts/
    engagement/
    templates/
    packages/
    questions/
    signatures/
    activation/
  application/commands/
  application/queries/
  application/projections/
  adapters/
  shared_contracts/
  db/
  security/
workers/
registries/
tests/unit/
tests/contracts/
tests/integration/
tests/e2e/
tests/security/
```


## 18.2 Coding rules

- Domain aggregates do not import web frameworks, provider SDKs or another product models.

- Commands and events use typed schemas and stable versioning.

- No bare strings for canonical IDs where typed enums/value objects are possible.

- No state assignment outside WorkflowRuntime.

- No direct shared-table mutation unless the shared service explicitly owns the call contract.

- Every database query includes tenant context by construction.

- Retries require idempotency and bounded backoff.

- Exceptions map to stable error codes and safe user messages.

- PII/confidential content is minimized in logs and events.

- Tests are required with every registry, transition, permission or contract change.



## 18.3 Shared contracts package

```text
truevow-contracts/
  ontology/ids.py
  authority/classes.py
  events/envelope.schema.json
  events/catalog.yaml
  transitions/contract.schema.json
  entities/references.py
  errors/codes.py
  compatibility/manifest.json
  generated/  # language-specific generated types
```


# 19. Build Sequence and Coding-Agent Work Packages

## 19.1 Delivery sequence

| Package | Outcome |

| --- | --- |

| BP-00 Contract normalization | Patch EventEnvelope to 18 fields; freeze six authority classes; classify canonical/extension events; publish shared package; name Matter activation owner. |

| BP-01 Repository bootstrap | Create monorepo/deployables, CI, health/version endpoints, DB, tenant context, inbox/outbox, idempotency and shared adapters. |

| BP-02 Candidate and representation review | Consume INTAKE handoff; review queue; RepresentationDecision; attorney assignment; approve/decline/defer; audit. |

| BP-03 Conflict workflow | Deterministic search; candidates; attorney decision; hold/reopen; party-change invalidation; tests. |

| BP-04 Templates and packages | Resolve approved template; merge schema; preflight; package manifest; exact preview; immutable hashes. |

| BP-05 Client portal | Secure access, firm branding, electronic consent, document review, questions, decline/fallback. |

| BP-06 Signatures | Provider adapter, ceremonies, signer requirements, evidence, invalidation, fully executed and completed-copy delivery. |

| BP-07 Communications | Transactional email, consent-aware SMS flag, reminders, suppression, delivery failure and escalation. |

| BP-08 Activation and TRACE handoff | Checklist, attorney authorization, activation command/result, matter.activated, TRACE manifest, reconciliation. |

| BP-09 Pilot hardening | Security, chaos, export, legal hold, observability, runbooks, performance, California feature flags. |



## 19.2 Coding-agent execution rules

1. Read ontology registry, shared contract schemas, this specification and relevant package instructions before coding.

2. Do not rename canonical IDs or create aliases without registry change.

3. Inspect the current repository and reuse existing shared services/contracts.

4. Implement only one build package at a time with migrations, tests and rollback notes.

5. Never weaken fail-closed behavior to make a test pass.

6. No authority-sensitive action is implemented as a front-end-only check.

7. Provide a file-by-file change summary and test evidence.

8. Stop and report contract mismatch rather than inventing an interpretation.

9. Preserve backward compatibility for already deployed event consumers.

10. Do not modify INTAKE, SaaS Admin, TRACE or SETTLE databases from RETAINER.



## 19.3 Definition of complete for each package

- Requirements mapped to code/tests.

- Schemas/registries valid and versioned.

- Migrations include upgrade and downgrade.

- Unit, contract and integration tests pass.

- Authority, tenant and audit negative tests included.

- Observability and error codes added.

- Documentation/runbook updated.

- No unresolved P0 security or data-integrity issue.



# 20. Acceptance Criteria and Launch Gates

## 20.1 Product acceptance

- A California direct tenant prospect can complete the full approved engagement workflow and enter TRACE without duplicate entry.

- Staff can prepare work while attorney/client reserved decisions remain attributable and nondelegated.

- The firm can explain exactly which template, policy, authority, document bytes, consent, signatures and events supported activation.

- Every exception has a visible queue, owner and recovery path.



## 20.2 Architecture acceptance

- No direct database integration with another product.

- No duplicate shared ontology/authority/event definitions.

- Only WorkflowRuntime mutates canonical state.

- All transmitted/signed bytes are immutable and hash-verified.

- Matter creation occurs only through canonical activation contract.

- Projections are rebuildable from event/reference sources.

- Unknown external results do not silently change business state.



## 20.3 Security/compliance acceptance

- Zero confirmed cross-tenant access paths.

- 100 percent material audit completeness.

- Every P0 authority action has positive and negative tests.

- Client legal questions never receive automated legal explanations.

- No AI/service actor can create or satisfy its own authority record.

- Consent revocation and communication suppression are race-tested.

- Legal hold and retention controls override deletion.



## 20.4 California pilot activation flags

| Flag | Pilot value |

| --- | --- |

| jurisdiction | CA |

| agreement_type | PI_CONTINGENCY_6147 |

| direct_tenant_leads_only | true |

| named_attorney_representation_approval | required |

| named_attorney_conflict_clearance | required |

| named_attorney_activation | required |

| ai_authority_path | disabled |

| ai_legal_explanation | disabled |

| cross_firm_referral | disabled |

| sms_reminders | disabled until tenant/counsel/channel config effective |

| automated_voice_reminders | disabled |

| translated_authoritative_agreements | disabled |



## 20.5 Founder-level success measures

| Metric | Definition / use |

| --- | --- |

| Attorney review latency | Decision time minus review requested, excluding prospect-information wait |

| Engagement completion rate | Activated engagements / delivered approved packages, segmented by decline/expiry/question |

| Time to activation | Matter activated minus attorney representation approval |

| Question escalation latency | Attributable attorney response minus legal-question receipt |

| Second-workflow adoption | Firms completing a second qualifying RETAINER workflow during onboarding |

| Authority-gate denial rate | Denied material actions / attempted material actions, reviewed for training or misuse |

| Audit completeness | Material events with complete actor/authority/policy/object/result evidence |



# Appendix A. Canonical Traceability

## A.1 Ontology entities used by RETAINER

| ID | Entity | Owner | Use |

| --- | --- | --- | --- |

| ENT-001 | Tenant | Shared Platform | A law firm customer security and data boundary. |

| ENT-002 | Office | COMMAND | Operational location or business unit within a tenant. |

| ENT-004 | Role Assignment | Shared Platform | Time-bounded grant of permissions and responsibilities. |

| ENT-005 | Jurisdiction Profile | Compliance Control Plane | Versioned package of rules, constraints, and supported workflows for a jurisdiction. |

| ENT-006 | Firm Policy | Compliance Control Plane | Tenant-approved rule governing administrative execution. |

| ENT-007 | Authority Record | Compliance Control Plane | Evidence that a named actor may approve a defined action. |

| ENT-008 | Configuration Version | Shared Platform | Immutable snapshot of operational configuration. |

| ENT-011 | Person | Shared Platform | Canonical natural-person identity independent of role. |

| ENT-012 | Organization | Shared Platform | Canonical legal or operational organization identity. |

| ENT-013 | Party Role | Shared Platform | Context-specific role of a Person or Organization. |

| ENT-014 | Contact Point | Shared Platform | Email, phone, postal address, or channel endpoint with verification status. |

| ENT-016 | Representation Relationship | RETAINER | Defined lawyer-client relationship for a scope and matter. |

| ENT-017 | Responsible Attorney Assignment | Shared Platform | Accountability assignment for a matter or decision. |

| ENT-018 | Personal Representative Authority | RETAINER | Evidence and scope by which one person acts for another. |

| ENT-022 | Communication | Shared Platform | Message, call, voicemail, email, SMS, or portal interaction. |

| ENT-024 | Consent Record | Shared Platform | Versioned, attributable grant or revocation of permission. |

| ENT-025 | Matter Candidate | INTAKE | Structured prospect-and-incident record for firm review. |

| ENT-027 | Conflict Search | RETAINER | Search execution across parties and relationships. |

| ENT-028 | Conflict Candidate | RETAINER | Potential match requiring legal review. |

| ENT-031 | Representation Decision | RETAINER | Attorney-attributable decision to accept, decline, or defer representation. |

| ENT-032 | Engagement Workflow | RETAINER | Stateful process from firm approval through completed engagement conditions. |

| ENT-033 | Template Definition | RETAINER | Versioned attorney-approved legal or administrative template. |

| ENT-034 | Engagement Package | RETAINER | Set of documents and disclosures delivered together. |

| ENT-035 | Engagement Agreement | RETAINER | Agreement defining scope, fees, costs, and other terms. |

| ENT-036 | Disclosure | RETAINER | Required or firm-approved information presented separately or within package. |

| ENT-037 | Signature Ceremony | RETAINER | Bounded electronic or wet-sign process. |

| ENT-038 | Signature Evidence | RETAINER | Immutable evidence supporting a signature. |

| ENT-039 | Engagement Question | RETAINER | Prospect/client question about agreement or representation. |

| ENT-040 | Activation Checklist | RETAINER | Firm-approved requirements for creating an active matter. |

| ENT-041 | Matter | Shared Business Core | Canonical represented legal engagement with lifecycle and scope. |

| ENT-107 | Work Item | COMMAND | Actionable unit of work with owner, due date, policy, and state. |

| ENT-110 | Service Level Policy | COMMAND | Target response or completion time and escalation rules. |

| ENT-112 | Notification | Shared Platform | System-generated or user-triggered communication about an event. |

| ENT-115 | Document Version | Shared Platform | Immutable binary/text version and metadata. |

| ENT-119 | Legal Hold | Compliance Control Plane | Instruction suspending normal deletion for defined data. |



## A.2 Invariants enforced

| Invariant | RETAINER enforcement |

| --- | --- |

| INV-001 Tenant isolation | Every tenant-owned entity carries a non-null tenant_id, and access is denied unless an active authorization path exists. |

| INV-002 No candidate-to-client shortcut | A Matter Candidate cannot become a Matter without an attorney-attributable Representation Decision and activation gates. |

| INV-003 Conflict separation | Conflict search, conflict candidate detection, and conflict clearance are distinct events and authorities. |

| INV-004 Responsible attorney required | Every active Matter has at least one current Responsible Attorney Assignment. |

| INV-005 Client settlement authority | No settlement acceptance transition occurs without an attributable client or valid representative decision. |

| INV-006 Immutable transmitted version | Every sent, filed, or executed document references an immutable Document Version and hash. |

| INV-007 Derived facts require provenance | Every material Normalized Fact and Timeline Event links to one or more Source Citations or is explicitly marked user-authored without source. |

| INV-008 Contradictions are preserved | A later fact cannot overwrite a conflicting earlier fact; the conflict is represented explicitly. |

| INV-009 Signals are not conclusions | Risk flags, scores, treatment gaps, and readiness indicators remain reviewable signals unless a human authority adopts them. |

| INV-010 Policy-at-execution | Every material automated action stores the exact effective policy/configuration version used. |

| INV-011 No self-approval | A service or AI component cannot create the authority record needed to approve its own proposed action. |

| INV-012 Consent history preserved | Consent grants, refusals, revocations, expirations, and supersessions are append-only events. |

| INV-013 Money reconciliation | Settlement allocations and disbursements must reconcile to cleared funds and immutable ledger entries. |

| INV-014 Legal hold precedence | Legal hold prevents deletion regardless of ordinary retention schedule. |

| INV-015 Audit/log separation | Business audit evidence is not derived solely from mutable diagnostic logs. |

| INV-016 External system ambiguity | External sync status never silently changes the authoritative business state without a mapped, validated event. |

| INV-017 Jurisdiction gating | A jurisdiction-dependent workflow cannot activate without an approved, effective jurisdiction profile. |

| INV-018 Role does not create licensure | Administrative role or tenant ownership never implies attorney authority. |

| INV-019 Matter closure is not deletion | Closed matters remain subject to retention, access, accounting, and continuing-duty rules. |

| INV-020 AI remains nonauthoritative | AI outputs are drafts, extractions, classifications, or signals until accepted by an authorized human or deterministic approved rule. |



## A.3 Metrics

| ID | Metric | Definition | Guardrail |

| --- | --- | --- | --- |

| MET-003 | Attorney review latency | Representation decision time - review requested time | Exclude periods awaiting prospect information. |

| MET-004 | Engagement completion rate | Activated engagements / delivered approved packages | Track decline, expiry, question escalation separately. |

| MET-005 | Time to representation activation | Matter activated - attorney approval recorded | Do not start clock from marketing contact by default. |

| MET-006 | Second-workflow adoption | Firms completing a second qualifying workflow within defined onboarding window | A behavioral-adoption hypothesis, not a contractual KPI. |

| MET-015 | Authority-gate denial rate | Denied material actions / attempted material actions | Investigate repeated attempts; not automatically negative. |

| MET-016 | Audit completeness | Material events with actor, authority, policy, object, result / material events | Target 100%. |

| MET-018 | Policy-version coverage | Automated actions referencing immutable policy version / automated actions | Target 100% for material actions. |



# Appendix B. Build Pack Contents

- Machine-readable RETAINER states, transitions, events, authority actions and workflow policies.

- EventEnvelope JSON Schema v1.0.1.

- Candidate handoff and Matter activation JSON Schemas.

- OpenAPI starter contract.

- PostgreSQL schema seed for RETAINER-owned operational tables.

- Acceptance scenario YAML.

- Requirement traceability CSV.

- Coding-agent build sequence and do-not-regress checklist.



# Appendix C. Final Non-Negotiables

1. A candidate is not a client or Matter.

2. A conflict search result is not conflict clearance.

3. A signature is not by itself matter activation.

4. Transport success is not legal/business authorization.

5. An admin role is not attorney authority.

6. An AI output is not an authority record.

7. A mutable log is not audit evidence.

8. A UI status is not canonical business state.

9. Another product database is not an integration API.

10. Missing or uncertain evidence fails closed.


