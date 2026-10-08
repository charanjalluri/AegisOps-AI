# Walking Skeleton — AegisOps AI

**Phase:** 1 (Local Containerized Infrastructure & Event Backbone)
**Generated:** 2026-10-08

## Capability Proven End-to-End

A developer can clone the repository, run `make setup` and `make up`, and have the complete local operational environment running:
- PostgreSQL 16.4 Alpine with dual isolated databases (`aegisops_db` and `demo_payment_db`)
- Apache Kafka 3.7.0 in KRaft mode with dual listeners (`kafka:9092` inside Docker, `localhost:29092` from host)
- Pinned Kafka UI (`provectuslabs/kafka-ui:v0.7.2`), Qdrant (`qdrant/qdrant:v1.9.0`), Prometheus (`prom/prometheus:v2.51.0`), Grafana (`grafana/grafana:10.4.0`), and n8n (`n8nio/n8n:1.36.0`)
- A real lightweight `payment-service` HTTP + PostgreSQL simulator executing real database transactions against `demo_payment_db` and streaming operational telemetry (`RawLogEvent`, `RawMetricEvent`, `DeploymentEvent`) to Kafka
- A FastAPI platform service exposing `/health` (instant liveness) and `/ready` (evaluating PostgreSQL and Kafka as hard dependencies, and Qdrant/n8n as non-blocking soft status)

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Image Tagging | Strictly pinned images (e.g., `kafka-ui:v0.7.2`, `kafka:3.7.0`, `postgres:16.4-alpine`, `qdrant:v1.9.0`, `n8n:1.36.0`) | Eliminates breaking image drift and ensures reproducible developer environments |
| Event Streaming Listeners | Dual listeners: `PLAINTEXT://kafka:9092` (Docker network) and `EXTERNAL://localhost:29092` (Host) | Enables seamless internal container communication and local host CLI/script tooling access |
| State Isolation | Dual PostgreSQL databases (`aegisops_db` and `demo_payment_db`) | Isolates internal AegisOps operations from simulated target microservice application state |
| Readiness Decoupling | Postgres + Kafka as hard readiness gates; Qdrant + n8n as optional/informational probes | Keeps the Phase 1 core event backbone operational without blocking on ancillary tooling startup |
| Target Simulation | Real lightweight HTTP + PostgreSQL service for `payment-service` | Simulates realistic database queries, connection pool saturation, and latency rather than fake static log emitting |
| Line Endings | `.gitattributes` enforcing `*.sh text eol=lf` | Prevents Windows CRLF syntax errors inside Linux Docker containers |
| Test Organization | Strict isolation of `tests/unit` (offline) and `tests/integration` (Docker-dependent) | Enables instant offline CI/developer feedback without requiring a running Docker daemon |

## Stack Touched in Phase 1

- [x] Project scaffold (`pyproject.toml`, `.gitattributes`, `.env.example`, `Makefile`)
- [x] Container orchestration (`docker-compose.yml`, health checks, network definitions, persistent volumes)
- [x] Multi-database initialization (`infrastructure/postgres/init-databases.sh` with LF endings)
- [x] Event bus provisioner (`scripts/init-kafka.py` provisioning 8 operational topics)
- [x] Shared Pydantic event schemas (`apps/common/schemas/events.py`)
- [x] Platform health & readiness probes (`apps/api/routers/health.py`)
- [x] Real lightweight `payment-service` simulator (`apps/payment_service/`)

## Out of Scope (Deferred to Later Slices)

- Deterministic anomaly detection and incident generation (Phase 2)
- Domain MCP servers: Logs MCP (Phase 2), Database/GitHub/Incident MCPs (Phase 3), Deployment/n8n MCPs (Phase 5)
- LangGraph investigation agent and multi-hypothesis reasoning engine (Phase 4)
- Human-in-the-loop approval gating and recovery verification (Phase 5)
- React operations dashboard (Phase 6)
- Declarative failure scenarios and automated evaluation benchmarks (Phase 7)
