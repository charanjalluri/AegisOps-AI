# Phase 1: Local Containerized Infrastructure & Event Backbone - Research

**Researched:** 2026-10-08
**Domain:** Distributed Event-Driven Architecture, Local Container Orchestration, Observability
**Confidence:** HIGH

<user_constraints>
## User Constraints (from PROJECT.md & Initial Requirements)

### Locked Decisions
- **Single-command local packaging**: The entire system must spin up via `docker compose up -d` with minimal prerequisites (Docker Desktop, Git, API keys).
- **Event-driven backbone**: Apache Kafka acts as the central event stream for all operational events (`logs.raw`, `metrics.raw`, `alerts.raw`, `deployments.events`, `incidents.created`, `incidents.updated`, `ai.analysis`, `ai.actions`).
- **Dual database isolation**: PostgreSQL must host two separated databases/schemas: `aegisops_db` for platform operational data and `demo_payment_db` for the simulated target service.
- **Self-contained target simulation**: A realistic microservice (`payment-service` baseline v2.8.0) must simulate realistic baseline traffic, DB connection pools, and logs without external cloud dependencies.
- **Self-observability**: Platform includes Prometheus and Grafana for internal telemetry and Kafka UI for stream inspection.

### Agent Discretion
- Kafka broker distribution: Apache Kafka KRaft mode (single container, no Zookeeper) chosen for minimal workstation footprint.
- Python framework for internal services: FastAPI + `aiokafka` + `asyncpg` for non-blocking asynchronous event handling and high throughput.

### Deferred Ideas (OUT OF SCOPE)
- Real cloud-hosted Kubernetes cluster deployment (deferred to v2).
- Direct mutation of the target database by AI (strictly prohibited).
- Direct shell/root access inside containers (strictly prohibited).
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Event Streaming Bus | Kafka Broker | Kafka UI | Decouples event ingest from consumers; UI provides visual auditability |
| Operational State & Persistence | PostgreSQL (`aegisops_db`) | Backend API | Structured transactional data, incidents, audit logs |
| Simulated Target Storage | PostgreSQL (`demo_payment_db`) | `payment-service` | Simulates realistic target DB connection pool and schemas |
| Vector Store | Qdrant | RAG Service | Semantic storage for runbooks and historical incidents |
| External Workflow Automation | n8n | Webhook Handlers | Offloads third-party alerts and notifications |
| Health & Readiness Probes | Backend API (`/health`, `/ready`) | Docker Healthchecks | Ensures deterministic container dependency startup order |
| Target Microservice Simulator | `payment-service` | Kafka Producer | Generates baseline v2.8.0 healthy telemetry |
</architectural_responsibility_map>

<research_summary>
## Summary

Phase 1 establishes the production-grade local foundation for AegisOps AI. A single `docker-compose.yml` orchestrates all infrastructure components: Kafka (KRaft mode), Kafka UI, PostgreSQL 16 (with automated initialization for both `aegisops_db` and `demo_payment_db`), Qdrant vector database, Prometheus, Grafana, and n8n. 

To ensure stability across various developer laptops (Windows, macOS, Linux), services utilize strict container healthchecks (`test: ["CMD-SHELL", ...]`) and dependency conditions (`depends_on: { service: { condition: service_healthy } }`). This prevents race conditions where the API or simulator starts before Kafka and PostgreSQL are ready.

A dedicated Kafka initialization script or container provisions all required event topics with proper partition counts and retention policies. The simulated `payment-service` acts as a realistic producer, streaming normal HTTP traffic, database transactions, latency metrics, and logs into Kafka topics, establishing the operational baseline needed for subsequent incident detection and AI investigation phases.

**Primary recommendation:** Use KRaft-mode Kafka with healthchecked multi-container Docker Compose and an async FastAPI foundation to ensure deterministic, zero-friction developer setup via `make up`.
</research_summary>

<standard_stack>
## Standard Stack

### Core Infrastructure
| Component | Image / Version | Purpose | Why Standard |
|-----------|-----------------|---------|--------------|
| Kafka | `apache/kafka:3.7.0` | Event Streaming Backbone | Native KRaft mode eliminates Zookeeper, reduces memory and CPU usage |
| Kafka UI | `provectuslabs/kafka-ui:latest` | Stream Visualizer | Web GUI to inspect messages, consumer groups, and topic partitions |
| PostgreSQL | `postgres:16-alpine` | Structured Persistence | Rock-solid relational DB; lightweight Alpine image; multi-DB init scripts |
| Qdrant | `qdrant/qdrant:v1.9.0` | Vector Database | High performance, memory-efficient, native REST & gRPC API |
| Prometheus | `prom/prometheus:v2.51.0` | Metric Scraper & Store | Industry standard for time-series operational metrics |
| Grafana | `grafana/grafana:10.4.0` | Metric Visualizer | Rich pre-built dashboards for system health |
| n8n | `n8nio/n8n:1.36.0` | Automation Engine | Visual workflow automation with webhook support |

### Application & Library Stack (Python 3.11+)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | `^0.110.0` | API & Probes | High performance, async-native, automatic OpenAPI documentation |
| `uvicorn` | `^0.29.0` | ASGI Web Server | Standard lightning-fast ASGI server for FastAPI |
| `aiokafka` | `^0.10.0` | Async Kafka Client | Non-blocking async producer/consumer for FastAPI event loops |
| `asyncpg` | `^0.29.0` | Async Postgres Driver | Highest throughput PostgreSQL client in Python ecosystem |
| `pydantic` | `^2.6.0` | Schema Validation | Type-safe domain models for event schemas and config |
| `pydantic-settings`| `^2.2.0` | Environment Config | Clean `.env` loading with strong typing and default fallbacks |
</standard_stack>

<pitfalls_and_patterns>
## Common Pitfalls & Architectural Patterns

### Pitfalls to Avoid
1. **Container Startup Race Conditions**: Starting the API before Kafka or Postgres finishes its bootstrap leads to crashes and restart loops.
   *Mitigation:* Use Docker Compose `service_healthy` conditions on all dependent services.
2. **Missing Multi-Database Creation in Postgres**: The official `postgres` Docker container only creates one database by default (`POSTGRES_DB`).
   *Mitigation:* Mount an initialization script into `/docker-entrypoint-initdb.d/init-databases.sh` to create both `aegisops_db` and `demo_payment_db` along with appropriate grants.
3. **Kafka Advertised Listeners Mismatch**: Kafka container communication fails when internal containers and host machine ports conflict.
   *Mitigation:* Configure dual listeners: `PLAINTEXT://kafka:9092` for Docker internal networks and `EXTERNAL://localhost:29092` for host machine access.
4. **Hardcoded Secrets & Environment Drift**: Committing secrets or missing required keys breaks setup for new developers.
   *Mitigation:* Provide a comprehensive `.env.example` with sensible defaults and zero sensitive credentials.

### Established Patterns
- **Health / Readiness Separation**: `/health` checks if the application server is up; `/ready` actively pings downstream dependencies (Kafka, PostgreSQL, Qdrant) and returns 503 until all connections are healthy.
- **Idempotent Make Commands**: `make up` creates networks and volumes cleanly; `make down` shuts down gracefully without destroying persistent volumes unless `make clean` is invoked.
</pitfalls_and_patterns>

---
*Phase 1 Research generated: 2026-10-08*
