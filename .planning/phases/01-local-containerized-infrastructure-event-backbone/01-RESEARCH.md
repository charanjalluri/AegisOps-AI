# Phase 1: Local Containerized Infrastructure & Event Backbone - Research

**Researched:** 2026-10-08
**Domain:** Distributed Event-Driven Architecture, Local Container Orchestration, Observability
**Confidence:** HIGH

<user_constraints>
## User Constraints (from User Guidance & SKELETON.md)

### Locked Decisions
- **Pin all Docker images**: No `:latest` tags. Pinned versions: `apache/kafka:3.7.0`, `provectuslabs/kafka-ui:v0.7.2`, `postgres:16.4-alpine`, `qdrant/qdrant:v1.9.0`, `prom/prometheus:v2.51.0`, `grafana/grafana:10.4.0`, `n8nio/n8n:1.36.0`.
- **Kafka Listener Architecture**: Dual listeners must be explicitly configured:
  - Internal Docker network: `kafka:9092`
  - Host machine access: `localhost:29092`
- **Soft Readiness Probing**: In Phase 1, PostgreSQL (`aegisops_db`) and Kafka are hard dependencies for `/ready`. Qdrant and n8n are available via Compose but probed as optional/informational so Phase 1 readiness is not blocked.
- **Real Microservice Simulation**: `payment-service` must be a real lightweight HTTP service backed by PostgreSQL (`demo_payment_db`) that executes real database transactions, records latency, and emits telemetry events to Kafka.
- **Line Ending Safety**: Shell scripts executed by Linux containers must have LF line endings enforced via `.gitattributes`.
- **Test Separation**: Offline unit tests (`tests/unit`) must be strictly decoupled from Docker-dependent integration tests (`tests/integration`).
- **Clean Volume Lifecycle**: `make clean` must remove containers and volumes (`docker compose down -v`), while `make reset-demo` resets demo database tables and Kafka topics without destroying the infrastructure.
- **Strict Scope Fencing**: No LangGraph, Muse Spark, MCP servers, RAG, policy remediation, or React dashboard in Phase 1.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Event Streaming Bus | Kafka Broker (`kafka:9092` / `localhost:29092`) | Kafka UI (`:8080`) | Decouples telemetry ingestion; dual listeners support internal and host access |
| Operational Persistence | PostgreSQL (`aegisops_db`) | Backend API | Structured transactional data, incidents, audit logs |
| Target Microservice Storage | PostgreSQL (`demo_payment_db`) | `payment-service` | Simulates realistic target DB transactions and connection pools |
| Target Microservice | `payment-service` HTTP API (`:8001`) | Kafka Producer | Real FastAPI app executing SQL queries and streaming operational telemetry |
| Platform Health Probes | Backend API (`/health`, `/ready`) | Docker Healthchecks | Reports readiness (Postgres + Kafka hard; Qdrant + n8n soft) |
| Vector Store | Qdrant (`:6333`) | Informational Probe | Containerized for future RAG; non-blocking in Phase 1 |
| Workflow Automation | n8n (`:5678`) | Informational Probe | Containerized for future notification workflows; non-blocking in Phase 1 |
</architectural_responsibility_map>

<standard_stack>
## Pinned Standard Stack (October 2026 Compatible)

### Infrastructure Containers
| Container | Pinned Image | Purpose | Ports |
|-----------|--------------|---------|-------|
| Kafka Broker | `apache/kafka:3.7.0` | KRaft-mode Event Backbone | `9092` (internal), `29092` (host) |
| Kafka UI | `provectuslabs/kafka-ui:v0.7.2` | Web Topic & Message Viewer | `8080` |
| PostgreSQL | `postgres:16.4-alpine` | Dual DB (`aegisops_db`, `demo_payment_db`) | `5432` |
| Qdrant | `qdrant/qdrant:v1.9.0` | Semantic Vector Store | `6333`, `6334` |
| Prometheus | `prom/prometheus:v2.51.0` | Metrics Scraper & Store | `9090` |
| Grafana | `grafana/grafana:10.4.0` | Metrics Dashboard | `3000` |
| n8n | `n8nio/n8n:1.36.0` | Workflow Automation Engine | `5678` |

### Python Application Stack (Python 3.11+)
| Library | Version | Purpose |
|---------|---------|---------|
| `fastapi` | `^0.110.0` | Async HTTP APIs for Platform API and `payment-service` |
| `uvicorn` | `^0.29.0` | Lightning-fast ASGI web server |
| `pydantic` | `^2.6.0` | Strongly-typed operational event schemas |
| `aiokafka` | `^0.10.0` | Async non-blocking Kafka producer and consumer |
| `asyncpg` | `^0.29.0` | Async driver for PostgreSQL database pools |
| `httpx` | `^0.27.0` | Async HTTP client for probe checks and simulator test requests |
| `pytest` | `^8.0.0` | Unit and integration test runner |
</standard_stack>

<pitfalls_and_patterns>
## Common Pitfalls & Architectural Patterns

### Pitfalls to Avoid
1. **Windows CRLF Inside Alpine Containers**: Shell scripts with `\r\n` fail with `syntax error: unexpected end of file` in `postgres:16.4-alpine`.
   *Mitigation:* Add `.gitattributes` with `*.sh text eol=lf` and ensure `init-databases.sh` is saved with LF.
2. **Kafka Listener Misconfiguration**: If `advertised.listeners` only lists `localhost:29092`, other Docker containers cannot communicate with Kafka.
   *Mitigation:* Configure dual listeners: `PLAINTEXT://kafka:9092` for internal Docker containers and `EXTERNAL://localhost:29092` for the host machine.
3. **Hard Dependencies Blocking Readiness**: Waiting for Qdrant or n8n before the core platform reports ready can delay early startup.
   *Mitigation:* Make Postgres and Kafka the primary readiness gates; probe Qdrant and n8n opportunistically without returning HTTP 503.
4. **Volume Persistence Across Resets**: Re-running demo scripts without cleaning old data leads to state confusion.
   *Mitigation:* Provide distinct commands: `make reset-demo` for database table truncates and `make clean` for full `docker compose down -v`.
</pitfalls_and_patterns>

---
*Phase 1 Research updated: 2026-10-08*
