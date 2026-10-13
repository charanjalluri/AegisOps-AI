# Requirements: AegisOps AI

**Defined:** 2026-10-08
**Core Value:** Detect operational problems automatically, investigate using verifiable evidence across controlled MCP tools, reason with quantified uncertainty, mandate human approval for risky actions, and verify remediation before marking incidents resolved.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Infrastructure & Event Backbone (INFRA)

- [x] **INFRA-01**: Single-command Docker Compose stack (`PostgreSQL` with dual `aegisops_db`/`demo_payment_db`, `Kafka`, `Kafka UI`, `Qdrant`, `Prometheus`, `Grafana`, `n8n`, `API`, `Agent`, `Dashboard`).
- [x] **INFRA-02**: Event streaming backbone configured with dedicated Kafka topics (`logs.raw`, `metrics.raw`, `alerts.raw`, `deployments.events`, `incidents.created`, `incidents.updated`, `ai.analysis`, `ai.actions`).
- [x] **INFRA-03**: Developer automation tooling (`Makefile` / CLI scripts: `make setup`, `make up`, `make down`, `make demo`, `make reset-demo`, `make seed`).
- [x] **INFRA-04**: System readiness and health check endpoints (`GET /health`, `GET /ready`) verifying connectivity across PostgreSQL, Kafka, Qdrant, MCP, and agent services.

### Deterministic Incident Detection (DETECT)

- [x] **DETECT-01**: High-throughput telemetry ingestion consumer streaming logs, metrics, and deployment events from Kafka into structured operational tables.
- [x] **DETECT-02**: Deterministic rule-based detection engine monitoring latency anomalies, error rate thresholds, and database connection timeouts over sliding time windows.
- [x] **DETECT-03**: Automated incident generation publishing `incidents.created` events and persisting initial incident records to PostgreSQL.

### Controlled MCP Server Suite (MCP)

- [x] **MCP-01**: Shared MCP core framework (`mcp_common`) providing standardized schemas, timeouts, error handling, rate limiting, and sanitized audit logging.
- [x] **MCP-02**: `Logs MCP` server with structured search (`search_logs`, `get_service_logs`, `get_error_rate`, `get_correlated_errors`, `get_logs_around_event`) enforcing pagination and token limits.
- [x] **MCP-03**: `Database MCP` server providing read-only diagnostics (`get_database_health`, `get_connection_pool`, `get_slow_queries`, `get_active_connections`, `run_readonly_query`).
- [x] **MCP-04**: `GitHub MCP` server providing read-only change tracking (`get_recent_commits`, `get_commit`, `get_pull_requests`, `get_changed_files`, `get_deployment_history`).
- [x] **MCP-05**: `Incident MCP` server for transactional lifecycle state management (`create_incident`, `update_incident`, `add_evidence`, `add_hypothesis`, `create_action_proposal`, `close_incident`).
- [x] **MCP-06**: `Deployment MCP` server with read inspection (`get_current_version`, `get_previous_version`, `get_deployment_history`) and policy-gated action execution (`rollback_deployment`, `restart_service`).
- [x] **MCP-07**: `n8n MCP` server providing workflow automation triggers (`execute_workflow`, `get_execution_status`) for Slack, Jira, email, and external notifications.

### Evidence Engine & LangGraph Agent (REASON)

- [x] **REASON-01**: Evidence Engine normalizer converting heterogeneous MCP responses into canonical evidence objects with provenance timestamps and signal weights.
- [x] **REASON-02**: LangGraph cyclic state machine orchestrating the investigation flow (understand incident -> plan missing information -> select MCP tool -> evaluate evidence -> iterate).
- [x] **REASON-03**: Multi-hypothesis generation and confidence scoring distinguishing facts, hypotheses, assumptions, and alternative explanations.
- [x] **REASON-04**: Investigation budget enforcement capping maximum tool calls (limit 20), wall-clock execution time (5 minutes), and expensive queries.
- [x] **REASON-05**: Structured Root Cause Analysis (RCA) synthesis producing auditable findings, primary root cause, confidence score, and remediation recommendations.

### Dual Memory & Semantic RAG (MEM)

- [x] **MEM-01**: Short-term transactional memory storing active investigation state, tool executions, hypothesis transitions, and evidence chains in PostgreSQL.
- [x] **MEM-02**: Long-term semantic retrieval via Qdrant for historical incidents, postmortems, failure patterns, and operational runbooks.
- [x] **MEM-03**: Operational memory seeder (`scripts/seed-qdrant.py`) prepopulating Qdrant with 20–50 realistic historical incidents and troubleshooting guides.

### Policy Engine, HITL Guardrails & Verification (GOV)

- [x] **GOV-01**: Operation risk tiering classifying actions into `READ`, `LOW`, `MEDIUM`, `HIGH`, and `DESTRUCTIVE`.
- [x] **GOV-02**: Human-in-the-Loop (HITL) gate mandating structured proposals, risk rationale, and explicit approval before executing any `HIGH`-risk action (e.g. production rollback).
- [x] **GOV-03**: Automated post-remediation verification loop polling service telemetry after action execution to confirm error rate and metric recovery before incident closure.
- [x] **GOV-04**: Immutable audit logging recording all MCP requests, policy checks, approval decisions, and remediation executions.

### Target Simulation & Evaluation Framework (DEMO)

- [x] **DEMO-01**: Fictional microservice simulator (`payment-service`) emitting realistic logs, metrics, DB connection traffic, and failure events.
- [ ] **DEMO-02**: Declarative incident scenario runner executing `demo/scenarios/database-connection-leak.yaml` (v2.8.1 deployment triggering pool exhaustion and 500 spikes).
- [ ] **DEMO-03**: Additional ground-truth scenario library (bad-deployment, memory-leak, slow-query, service-dependency-failure).
- [ ] **DEMO-04**: AI evaluation benchmarking suite (`make evaluate`) measuring RCA accuracy, tool selection precision, hallucination rate, and verification reliability.

### React Operations Dashboard (UI)

- [x] **UI-01**: Overview & active incident triage dashboard displaying active incidents, severity badges, and status summaries.
- [x] **UI-02**: Incident detail investigation workbench featuring visual timeline, live evidence graph, and hypothesis confidence rankings.
- [x] **UI-03**: MCP tool inspector detailing each tool call, parameters, latency, and returned evidence data.
- [x] **UI-04**: Human approval interface card presenting proposed remediation, risk level, expected benefit, and interactive Approve/Reject actions.
- [x] **UI-05**: Platform health & observability panel monitoring Kafka topic lags, MCP server health, and agent performance metrics.

## v2 Requirements

Deferred to future releases.

### Kubernetes & Cloud Production Integration

- **K8S-01**: Native Kubernetes Deployment MCP integrating with real Kube API / ArgoCD for canary rollbacks and pod restarts.
- **K8S-02**: OpenTelemetry & Prometheus live cluster telemetry collector replacing local mock streams.
- **CLOUD-01**: Cloud secret manager integrations (AWS Secrets Manager / GCP Secret Manager / Vault).

### Advanced Autonomous Features

- **AUTO-01**: Adaptive auto-remediation for LOW-risk actions without human approval when confidence exceeds 98%.
- **AUTO-02**: Multi-agent collaborative swarm (specialized log investigator agent, code reviewer agent, and database investigator agent).

## Out of Scope

| Feature | Reason |
|---------|--------|
| Unrestricted shell / root cluster access | Direct shell execution violates the least-privilege security principle. |
| Database write / mutation operations by AI | Database MCP is strictly read-only to prevent irreversible data loss. |
| Chatbot-only conversational interface | AegisOps is an evidence-based incident platform, not a conversational chat assistant. |
| Direct cloud infrastructure provisioning | Infrastructure provisioning belongs in Terraform/Pulumi; AegisOps focuses on operations & incident response. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| DEMO-01 | Phase 1 | Complete |
| DETECT-01 | Phase 2 | Complete |
| DETECT-02 | Phase 2 | Complete |
| DETECT-03 | Phase 2 | Complete |
| MCP-01 | Phase 2 | Complete |
| MCP-02 | Phase 2 | Complete |
| MCP-03 | Phase 3 | Complete |
| MCP-04 | Phase 3 | Complete |
| MCP-05 | Phase 3 | Complete |
| MEM-01 | Phase 3 | Complete |
| MEM-02 | Phase 4 | Complete |
| MEM-03 | Phase 4 | Complete |
| REASON-01 | Phase 4 | Complete |
| REASON-02 | Phase 4 | Complete |
| REASON-03 | Phase 4 | Complete |
| REASON-04 | Phase 4 | Complete |
| REASON-05 | Phase 4 | Complete |
| MCP-06 | Phase 5 | Complete |
| MCP-07 | Phase 5 | Complete |
| GOV-01 | Phase 5 | Complete |
| GOV-02 | Phase 5 | Complete |
| GOV-03 | Phase 5 | Complete |
| GOV-04 | Phase 5 | Complete |
| UI-01 | Phase 6 | Complete |
| UI-02 | Phase 6 | Complete |
| UI-03 | Phase 6 | Complete |
| UI-04 | Phase 6 | Complete |
| UI-05 | Phase 6 | Complete |
| DEMO-02 | Phase 7 | Complete |
| DEMO-03 | Phase 7 | Complete |
| DEMO-04 | Phase 7 | Complete |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-08*
*Last updated: 2026-10-08 after initial definition*
