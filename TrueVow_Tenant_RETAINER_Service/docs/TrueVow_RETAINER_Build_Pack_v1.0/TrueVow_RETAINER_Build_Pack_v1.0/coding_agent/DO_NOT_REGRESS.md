# RETAINER Do-Not-Regress Controls

1. Candidate is never treated as Client or Matter.
2. Conflict search/no-match is never conflict clearance.
3. Only attorney authority approves representation and California v1 activation.
4. STAFF_AUTH remains distinct from FIRM_POLICY.
5. AI and services cannot self-authorize or provide legal explanation.
6. Only WorkflowRuntime changes canonical workflow state.
7. No direct reads/writes to INTAKE, SaaS Admin, TRACE or SETTLE databases.
8. Delivered/signed document versions are immutable and hash-verified.
9. Consent history is append-only and revocation suppresses the relevant channel.
10. Unknown external results enter reconciliation; transport success is not business authorization.
11. Every material event uses the normalized 18-field EventEnvelope and exact policy version.
12. Tenant isolation fails closed at query, command, event, document and portal-token boundaries.
