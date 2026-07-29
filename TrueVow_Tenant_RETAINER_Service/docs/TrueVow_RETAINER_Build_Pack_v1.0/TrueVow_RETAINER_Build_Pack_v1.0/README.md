# TrueVow RETAINER Build Pack v1.0

This pack accompanies **TrueVow RETAINER Product Architecture and Build Specification v1.0**.

## Contents
- `registries/`: product states, transitions, events, authority actions and California v1 policy seed.
- `contracts/`: JSON Schemas and OpenAPI starter.
- `database/`: RETAINER-owned PostgreSQL schema seed.
- `tests/`: acceptance scenarios.
- `coding_agent/`: ordered build packages, traceability and non-regression controls.
- `docs/`: specification source.

## Required pre-build gate
Normalize the shared EventEnvelope to 18 required fields by adding `schema_version` to the 17 listed ontology fields, then publish the same contract version to every repository.
