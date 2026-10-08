# Walking Skeleton — AegisOps AI

**Phase:** 1 (Local Containerized Infrastructure & Event Backbone)
**Generated:** 2026-10-08

## Capability Proven End-to-End

A developer can clone the repository, run `make setup` and `make up`, and have the complete local operational environment running (PostgreSQL with dual databases, Kafka with KRaft mode and all initialized topics, Kafka UI, Qdrant, Prometheus, Grafana, and n8n) with a simulated `payment-service` streaming healthy telemetry and a FastAPI API reporting `200 OK` on `/ready`.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Event Streaming | Apache Kafka (KRaft mode via `apache/kafka:3.7.0`) | High-throughput, asynchronous decoupled event bus; KRaft mode eliminates Zookeeper dependency |
| Stream Inspection | `provectuslabs/kafka-ui:latest` | Web UI allowing real-time developer inspection of operational topics and message payloads |
| Structured State | PostgreSQL 16 Alpine (`postgres:16-alpine`) | Robust relational database; dual database initialization (`aegisops_db` and `demo_payment_db`) |
| Vector Store | Qdrant (`qdrant/qdrant:v1.9.0`) | Fast vector retrieval for historical runbooks and incident postmortems |
| Metric Telemetry | Prometheus & Grafana | Standard time-series metrics collection and visualization for self-observability |
| External Workflows | n8n (`n8nio/n8n:1.36.0`) | Visual automation engine for notification dispatch without polluting agent core |
| API & Probe Layer | FastAPI + Python 3.11 | High-performance async ASGI server with native Pydantic schema validation and asyncpg/aiokafka drivers |
| Target Simulation | `payment-service` Python generator | Standalone simulator emitting baseline v2.8.0 telemetry (logs, DB queries, latency, metrics) to Kafka |

## Stack Touched in Phase 1

- [x] Project scaffold (`pyproject.toml`, Dockerfiles, directory layout, `.env.example`, `Makefile`)
- [x] Container orchestration (`docker-compose.yml`, health checks, network definitions, persistent volumes)
- [x] Database initialization (`infrastructure/postgres/init-databases.sh` creating `aegisops_db` and `demo_payment_db`)
- [x] Event bus setup (Kafka topics provisioner, topic configuration, event schema models)
- [x] Health probe endpoints (`GET /health` and `GET /ready` verifying all downstream dependencies)
- [x] Target microservice simulator (`payment-service` v2.8.0 baseline generation)

## Out of Scope (Deferred to Later Slices)

- Deterministic anomaly detection and incident generation (Phase 2)
- Domain MCP servers: Logs MCP (Phase 2), Database/GitHub/Incident MCPs (Phase 3), Deployment/n8n MCPs (Phase 5)
- LangGraph investigation agent and multi-hypothesis reasoning engine (Phase 4)
- Human-in-the-loop approval gating and recovery verification (Phase 5)
- React operations dashboard (Phase 6)
- Declarative failure scenarios and automated evaluation benchmarks (Phase 7)

## Subsequent Slice Plan

- Phase 2: Telemetry Ingestion, Deterministic Detection & Logs MCP
- Phase 3: Investigation Tooling Suite (Database, GitHub & Incident MCPs)
- Phase 4: LangGraph Investigation Agent, Evidence Engine & Semantic RAG
- Phase 5: Policy Engine, Human Approval & Controlled Remediation Verification
- Phase 6: React Operations Dashboard & Visual Incident Workbench
- Phase 7: End-to-End Incident Scenarios, Evaluation Suite & Demo Packaging
