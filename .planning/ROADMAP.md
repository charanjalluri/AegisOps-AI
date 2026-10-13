# Roadmap: AegisOps AI

## Overview

AegisOps AI is built as a complete evidence-driven incident intelligence and autonomous operations platform. Starting with a self-contained local event-streaming infrastructure and mock microservice, the system moves progressively through deterministic detection, domain-isolated MCP servers, LangGraph-driven evidence investigation with semantic RAG, policy-gated safe remediation with post-action verification, an interactive React operations dashboard, and automated evaluation benchmarking across reproducible incident scenarios.

## Phases

- [x] **Phase 1: Local Containerized Infrastructure & Event Backbone** - Single-command Docker Compose stack, Kafka event topics, health probes, and simulated microservice
- [x] **Phase 2: Telemetry Ingestion, Deterministic Detection & Logs MCP** - Kafka consumer pipeline, threshold-based incident creation, and structured Logs MCP server
- [x] **Phase 3: Investigation Tooling Suite (Database, GitHub & Incident MCPs)** - Read-only Database MCP, GitHub code changes MCP, Incident state MCP, and short-term PostgreSQL storage
- [x] **Phase 4: LangGraph Investigation Agent, Evidence Engine & Semantic RAG** - Cyclic investigation state machine, evidence normalization, multi-hypothesis scoring, and Qdrant memory
- [x] **Phase 5: Policy Engine, Human Approval & Controlled Remediation Verification** - Risk classification, HITL proposal/approval gates, Deployment & n8n MCPs, and recovery verification
- [x] **Phase 6: React Operations Dashboard & Visual Incident Workbench** - Incident triage queue, investigation timeline, live evidence graph, tool inspector, and approval controls
- [ ] **Phase 7: End-to-End Incident Scenarios, Evaluation Suite & Demo Packaging** - Ground-truth scenario library, automated AI evaluation benchmark, and reproducible demo scripts

## Phase Details

### Phase 1: Local Containerized Infrastructure & Event Backbone
**Goal**: Establish a reproducible local development and demonstration environment with core infrastructure and mock microservice.
**Mode**: mvp
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, DEMO-01
**Success Criteria** (what must be TRUE):
  1. `docker compose up -d` boots PostgreSQL (`aegisops_db` and `demo_payment_db`), Kafka, Kafka UI, Qdrant, Prometheus, Grafana, and n8n without failures.
  2. All Kafka topics (`logs.raw`, `metrics.raw`, `alerts.raw`, `deployments.events`, `incidents.created`, `incidents.updated`, `ai.analysis`, `ai.actions`) are initialized.
  3. `GET /health` and `GET /ready` return `200 OK` verifying all core dependencies.
  4. Fictional `payment-service` starts in v2.8.0 baseline mode producing healthy telemetry traffic.
  5. `make setup` and `make down` run idempotently on developer workstations.
**Plans**: 3 plans

Plans:
- [x] 01-01: Containerized infrastructure topology (docker-compose, PostgreSQL schemas, Qdrant, Kafka UI, Prometheus, n8n)
- [x] 01-02: Kafka event bus setup, topic initialization, and shared event schema definitions
- [x] 01-03: Fictional microservice simulator (`payment-service` baseline v2.8.0), health/readiness endpoints, and developer Makefile

### Phase 2: Telemetry Ingestion, Deterministic Detection & Logs MCP
**Goal**: Stream operational telemetry through Kafka, detect anomalies deterministically to trigger incidents, and provide structured log introspection via Logs MCP.
**Mode**: mvp
**Depends on**: Phase 1
**Requirements**: DETECT-01, DETECT-02, DETECT-03, MCP-01, MCP-02
**Success Criteria** (what must be TRUE):
  1. High-throughput Kafka consumer streams logs, metrics, and deployment events into PostgreSQL.
  2. Latency anomalies, error spikes, and database timeout thresholds automatically trigger structured incidents on `incidents.created`.
  3. Shared `mcp_common` framework enforces schema validation, timeouts, error formatting, rate limiting, and audit logging.
  4. `Logs MCP` server supports structured search, error rate queries, and timestamp-correlated log windows with token pagination limits.
**Plans**: 3 plans

Plans:
- [x] 02-01: Shared MCP framework (`mcp_common`) with schemas, timeouts, error contracts, and audit logging
- [x] 02-02: Telemetry ingestion consumer and sliding-window deterministic anomaly detector
- [x] 02-03: Logs MCP server implementation with structured search, error rate analytics, and log window extraction

### Phase 3: Investigation Tooling Suite (Database, GitHub & Incident MCPs)
**Goal**: Deliver read-only database introspection, code change tracking, transactional incident state management, and short-term investigation persistence.
**Mode**: mvp
**Depends on**: Phase 2
**Requirements**: MCP-03, MCP-04, MCP-05, MEM-01
**Success Criteria** (what must be TRUE):
  1. `Database MCP` executes strictly read-only diagnostics (connection pool, slow queries, active queries) and rejects any SQL mutation.
  2. `GitHub MCP` retrieves recent commits, pull requests, diffs, changed files, and deployment tags for the target service.
  3. `Incident MCP` manages incident records, records timeline events, logs evidence items, and updates hypothesis status.
  4. Short-term investigation state persists reliably in PostgreSQL across service restarts.
**Plans**: 3 plans

Plans:
- [x] 03-01: Read-only Database MCP server connecting to `demo_payment_db` with query parsing & mutation rejection
- [x] 03-02: GitHub MCP server with local mock repository data provider and change inspection tools
- [x] 03-03: Incident MCP server and PostgreSQL short-term transactional investigation state model

### Phase 4: LangGraph Investigation Agent, Evidence Engine & Semantic RAG
**Goal**: Orchestrate autonomous incident investigation via LangGraph, normalize evidence, evaluate hypotheses with calibrated confidence, and retrieve historical knowledge from Qdrant.
**Mode**: mvp
**Depends on**: Phase 3
**Requirements**: REASON-01, REASON-02, REASON-03, REASON-04, REASON-05, MEM-02, MEM-03
**Success Criteria** (what must be TRUE):
  1. `make seed` populates Qdrant with 20–50 realistic historical incidents, postmortems, and runbooks.
  2. LangGraph state machine consumes `incidents.created`, plans missing information, invokes appropriate MCP tools within an execution budget (max 20 calls), and normalizes outputs into evidence objects.
  3. Agent retrieves semantically similar historical incidents from Qdrant to inform diagnosis.
  4. Agent scores multiple competing hypotheses with calibrated confidence scores (e.g. 92% connection pool exhaustion vs 8% infra degradation).
  5. Agent synthesizes an auditable Root Cause Analysis (RCA) report explaining the winning hypothesis.
**Plans**: 3 plans

Plans:
- [x] 04-01: Qdrant semantic memory integration, vector schema, and historical incident seeding script
- [x] 04-02: Central Evidence Engine normalizer and multi-hypothesis confidence scoring algorithm
- [x] 04-03: LangGraph investigation state machine orchestrator, tool budget enforcement, and structured RCA synthesis

### Phase 5: Policy Engine, Human Approval & Controlled Remediation Verification
**Goal**: Implement action risk classification, require human approval for high-risk actions, execute rollbacks safely via Deployment MCP & n8n MCP, and verify post-remediation recovery.
**Mode**: mvp
**Depends on**: Phase 4
**Requirements**: MCP-06, MCP-07, GOV-01, GOV-02, GOV-03, GOV-04
**Success Criteria** (what must be TRUE):
  1. Operations are classified into `READ`, `LOW`, `MEDIUM`, `HIGH`, and `DESTRUCTIVE`.
  2. `HIGH`-risk rollback action generates an action proposal and remains blocked until explicit human approval is recorded.
  3. `Deployment MCP` executes controlled rollback of the simulated service only after approval validation.
  4. `n8n MCP` triggers external workflow notifications (Slack, Jira, email) without blocking core agent operations.
  5. Post-remediation verification loop polls telemetry, confirms metrics return to normal range, and closes incident automatically.
  6. Audit log captures all tool calls, approval metadata, and verification results.
**Plans**: 3 plans

Plans:
- [x] 05-01: Policy Engine with risk tiers, action proposal contracts, and approval verification gates
- [x] 05-02: Deployment MCP (with gated rollback) and n8n MCP workflow trigger integrations
- [x] 05-03: Post-remediation metric verification loop and automated incident closure pipeline

### Phase 6: React Operations Dashboard & Visual Incident Workbench
**Goal**: Build a modern, responsive React operations dashboard providing real-time visibility into active incidents, investigation timelines, evidence graphs, tool inspector, approvals, and system health.
**Mode**: mvp
**Depends on**: Phase 5
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. Active incidents display in a real-time triage queue with severity badges and status.
  2. Incident detail workbench renders the chronological investigation timeline, evidence cards, and hypothesis confidence bars.
  3. MCP tool inspector shows exact tool invocations, execution duration, and sanitized inputs/outputs.
  4. Human approval card provides clear risk rationale and interactive one-click Approve/Reject controls.
  5. Platform observability view visualizes Kafka topic throughput, consumer lag, and MCP service availability.
**Plans**: 3 plans

Plans:
- [x] 06-01: React application shell, design system tokens, system health widgets, and active incident triage queue
- [x] 06-02: Incident detail view: investigation timeline, evidence graph, hypothesis confidence meters, and MCP inspector
- [x] 06-03: Interactive HITL approval card, action executor triggers, and post-remediation verification view

### Phase 7: End-to-End Incident Scenarios, Evaluation Suite & Demo Packaging
**Goal**: Package declarative incident scenarios, automated AI evaluation benchmarks, and reproducible demonstration scripts.
**Mode**: mvp
**Depends on**: Phase 6
**Requirements**: DEMO-02, DEMO-03, DEMO-04
**Success Criteria** (what must be TRUE):
  1. Running `make demo` triggers the payment-service v2.8.1 failure scenario through Kafka, executes autonomous investigation, awaits approval, executes rollback, and verifies resolution.
  2. `make reset-demo` cleanly resets all state and returns the environment to initial conditions.
  3. Evaluation test runner (`make evaluate`) executes scenarios against ground truth and reports RCA accuracy, tool selection precision, and verification reliability.
  4. Complete documentation and quick-start guide verified against a fresh setup.
**Plans**: 3 plans

Plans:
- [x] 07-01: Declarative incident scenario engine with `database-connection-leak.yaml` and failure injection triggers
- [x] 07-02: Multi-scenario benchmark library (bad-deployment, memory-leak, slow-query) and `make evaluate` runner
- [x] 07-03: End-to-end `make demo` / `make reset-demo` scripts, Prometheus/Grafana dashboards, and quickstart documentation

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Local Containerized Infrastructure & Event Backbone | 3/3 | Complete | 2026-10-08 |
| 2. Telemetry Ingestion, Deterministic Detection & Logs MCP | 3/3 | Complete | 2026-10-10 |
| 3. Investigation Tooling Suite (Database, GitHub & Incident MCPs) | 3/3 | Complete | 2026-10-10 |
| 4. LangGraph Investigation Agent, Evidence Engine & Semantic RAG | 3/3 | Complete | 2026-10-13 |
| 5. Policy Engine, Human Approval & Controlled Remediation Verification | 3/3 | Complete | 2026-10-13 |
| 6. React Operations Dashboard & Visual Incident Workbench | 3/3 | Complete | 2026-10-13 |
| 7. End-to-End Incident Scenarios, Evaluation Suite & Demo Packaging | 3/3 | Complete | 2026-10-13 |
