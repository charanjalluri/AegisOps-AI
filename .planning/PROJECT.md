# AegisOps AI

## What This Is

AegisOps AI is an evidence-driven AI incident intelligence and autonomous operations platform designed to detect operational problems, investigate them using real-world evidence, determine probable root causes, recommend safe actions, enforce human approval for high-risk operations, execute controlled remediations, and verify resolution. It continuously ingests operational telemetry (logs, metrics, alerts, deployment events) via Apache Kafka, orchestrates investigations via LangGraph and domain-specific Model Context Protocol (MCP) servers, maintains short-term and long-term memory via PostgreSQL and Qdrant, and provides real-time visibility through a React dashboard.

## Core Value

Detect operational problems automatically, investigate using verifiable evidence across controlled MCP tools, reason with quantified uncertainty, mandate human approval for risky actions, and verify remediation before marking incidents resolved.

## Business Context

- **Customer**: SRE teams, Platform Engineers, DevOps teams, and Incident Responders.
- **Revenue model**: Open-source core with enterprise observability and automation deployments.
- **Success metric**: High Root Cause Analysis (RCA) accuracy (>90%), zero unverified or unauthorized remediations, reduced Mean Time to Detect (MTTD) and Mean Time to Resolve (MTTR).
- **Strategy notes**: Miniature, fully reproducible production-style architecture running locally via Docker Compose with zero cloud lock-in for development.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **Event Streaming Backbone (Kafka)**: Ingest raw logs, metrics, alerts, and deployment events asynchronously across dedicated Kafka topics (`logs.raw`, `metrics.raw`, `alerts.raw`, `deployments.events`, `incidents.created`, `incidents.updated`, `ai.analysis`, `ai.actions`).
- [ ] **Deterministic Incident Detector**: Rule-based detection engine monitoring latency, error rate spikes, database timeouts, and resource utilization to trigger structured incidents without LLM latency or hallucination.
- [ ] **LangGraph Investigation Agent**: State machine orchestrator controlling the investigative cycle (intake -> question formulation -> MCP tool invocation -> evidence gathering -> hypothesis updating -> RCA synthesis -> action proposal -> post-action verification).
- [ ] **Controlled MCP Server Suite**:
  - `Logs MCP`: Structured log filtering, error rate analysis, timestamp-correlated log searches with query boundaries and token limits.
  - `Database MCP`: Strictly read-only introspection (connection pools, active queries, slow queries, table statistics, sanitized read-only SQL).
  - `GitHub MCP`: Read-only repository telemetry (recent commits, diffs, changed files, pull requests, deployment tags).
  - `Deployment MCP`: Version inspection, deployment history, plus gated rollback and scaling actions subject to policy verification.
  - `Incident MCP`: Transactional incident state management, timeline logging, evidence anchoring, hypothesis tracking, and audit trails.
  - `n8n MCP`: External workflow triggers for Slack, Jira, email notifications, and human approval handoffs.
- [ ] **Evidence Engine & Hypothesis Tracker**: Normalizes heterogeneous MCP outputs into structured evidence objects, evaluates competing hypotheses, and computes calibrated confidence scores based on multi-signal correlation.
- [ ] **Dual Memory Subsystem**:
  - *Short-Term Memory*: Investigation state, active hypotheses, evidence chain, and tool history maintained in PostgreSQL.
  - *Long-Term Memory*: Semantic vector retrieval via Qdrant for historical incidents, postmortems, known failure patterns, and runbooks.
- [ ] **Policy Engine & Human-in-the-Loop (HITL) Guardrails**: Strict action classification (`READ`, `WRITE`, `EXECUTE`, `DESTRUCTIVE`), budget constraints (max tool calls, timeouts), policy validation, and interactive human approval for high-risk operations (e.g. rollbacks).
- [ ] **Automated Post-Remediation Verification**: Closed-loop metric polling and telemetry comparison against pre-incident baselines to confirm service recovery before closing incidents.
- [ ] **Self-Contained Local Demonstration & Simulation Environment**:
  - Full Docker Compose stack (PostgreSQL, Kafka, Kafka UI, Qdrant, n8n, Prometheus, Grafana, API, Agent, Dashboard).
  - Multi-scenario incident simulator (e.g., `payment-service` v2.8.1 database connection leak, memory leak, slow queries, high latency) with deterministic ground-truth configs.
  - Demo reset scripts (`make reset-demo`, `make demo`).
- [ ] **React Operations Dashboard**: Interactive timeline, active incident triage, live evidence graph, hypothesis confidence meters, tool execution inspector, pending approval action cards, and Kafka/MCP system health monitoring.
- [ ] **Evaluation & Benchmarking Framework**: Synthetic test suite evaluating RCA accuracy, tool-selection precision, evidence grounding, hallucination rate, and prompt injection resilience against ground-truth scenarios.

### Out of Scope

- **Unrestricted Shell / Root Cluster Access**: LLM will never have unrestricted terminal, SSH, or raw Kubernetes administrative execution permissions.
- **Direct Database Mutations by LLM**: Database MCP is strictly read-only; mutations or schema changes are permanently disallowed.
- **Generic Chatbot UI**: The dashboard is an operational workbench and audit viewer, not a conversational chatbot widget.
- **Cloud-Only Vendor Lock-In**: Platform runs completely self-contained locally via Docker Compose before requiring AWS/GCP/Kubernetes.

## Context

- **Event-Driven Architecture**: Decouples telemetry ingestion from AI reasoning. High-frequency telemetry streams into Kafka; deterministic rules trigger incidents, ensuring the LLM only consumes actionable, batched context.
- **Safety Architecture**: LLM proposes; Policy Engine validates; Human approves; Infrastructure executes; Verification confirms.
- **Dual Database Topology**: Isolated `aegisops_db` for platform operational data and `demo_payment_db` for the simulated target service.
- **Separation of MCP Concerns**: Shared internal library `mcp_common` provides standardized schemas, auth, error handling, rate limiting, and audit logging across all 6 specialized servers.

## Constraints

- **Security**: Zero plain credentials in LLM prompts or tool arguments; strict read-only boundaries on investigation tools.
- **Local Packaging**: Must spin up fully on a developer workstation via `docker compose up -d` with minimal prerequisites (Docker Desktop, Git, API keys).
- **LLM Compatibility**: Primary reasoning powered by Muse Spark 1.3 Contributor / OpenAI / LangChain compatible interfaces with structured output schemas.
- **Execution Limits**: Strict investigation budget (max 20 tool calls, 5-minute timeout, max 5 expensive operations) to prevent runaway loops.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Kafka as event backbone | Decouples data ingestion from AI reasoning; enables scalable, non-blocking telemetry stream handling | — Pending |
| LangGraph for agent orchestration | Provides deterministic cyclic state machine control over investigation rather than opaque autonomous loops | — Pending |
| Domain-specific MCP servers | Isolates tool capabilities, enables strict least-privilege access, and standardizes input/output contracts | — Pending |
| Qdrant for semantic retrieval | Efficient, lightweight vector database for historical runbooks and incident postmortems | — Pending |
| Deterministic incident detection | Avoids expensive and hallucination-prone LLM polling for threshold violations | — Pending |
| Two-tier memory model | Separates ephemeral investigation hypotheses from permanent institutional knowledge | — Pending |
| Human-in-the-Loop policy gate | High-risk actions (e.g. rollbacks) strictly mandate explicit approval before execution | — Pending |
| Self-contained local simulator | Allows end-to-end demonstration, debugging, and automated evaluation on a single developer laptop | — Pending |

---
*Last updated: 2026-10-08 after project initialization*
