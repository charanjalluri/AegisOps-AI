# Phase 2: Telemetry Ingestion, Deterministic Detection & Logs MCP - Research

**Researched:** 2026-10-10
**Domain:** Stream Telemetry Processing, Sliding-Window Anomaly Detection, Model Context Protocol (MCP) Architecture, Log Analytics
**Confidence:** HIGH

<user_constraints>
## User Constraints (from REQUIREMENTS.md & PROJECT.md)

### Locked Decisions
- **Decoupled Architecture**: Telemetry ingestion from Kafka into PostgreSQL (`aegisops_db`) must be completely decoupled from AI reasoning. High-frequency telemetry streams into Kafka; deterministic rules trigger incidents, ensuring the LLM only consumes actionable, batched context.
- **Deterministic Incident Detection**: Rule-based detection engine monitoring latency anomalies, error rate thresholds, and database connection timeouts over sliding time windows. No LLM calls in the detection loop to prevent latency, cost runaway, and hallucination.
- **Incident De-duplication & Cooldown**: When an anomaly is detected, automated incident generation publishes `incidents.created` and persists to PostgreSQL. An active incident cooldown window (e.g. 5–10 minutes) must prevent alert storming for ongoing failure states.
- **Shared MCP Framework (`mcp_common`)**: Standardized core in `apps/common/mcp` providing JSON-RPC 2.0 protocol models, tool registration decorators, automatic Pydantic schema introspection, timeouts, rate limiting, token budget enforcement, and sanitized audit logging.
- **Strict Read-Only Enforcement for Investigation MCPs**: `Logs MCP` executes strictly read-only SELECT queries on operational telemetry tables. Parameter sanitization strips credentials from prompts, arguments, and audit logs.
- **Token Budget & Pagination**: `Logs MCP` responses must enforce token caps (e.g. max 4000 tokens) and query pagination (limit 50, max 200) to protect downstream LLM context windows.
- **Test Separation**: Fast offline unit tests (`tests/unit`) must mock Kafka and database connections so they run in < 5 seconds without Docker dependencies. Docker integration tests (`tests/integration`) validate live broker and database persistence.
- **Strict Scope Fencing**: Phase 2 delivers Telemetry Ingestion, Anomaly Detection, `mcp_common`, and `Logs MCP`. No LangGraph agent, Database MCP, GitHub MCP, Incident MCP, Policy Engine, or React dashboard in Phase 2.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Module | Secondary Tier | Rationale |
|------------|----------------|----------------|-----------|
| Telemetry Ingestion | `apps/ingestion/consumer.py` | `aegisops_db` (`raw_logs`, `raw_metrics`, `deployment_events`) | Batches Kafka messages (`logs.raw`, `metrics.raw`, `deployments.events`) into PostgreSQL for durable queryability |
| Sliding-Window Detection | `apps/detection/detector.py` | In-memory sliding window state tracker | Evaluates rate thresholds and latency percentiles over 60s windows with zero LLM overhead |
| Incident Generation | `apps/detection/incident_creator.py` | Kafka `incidents.created` & PostgreSQL `incidents` table | Generates structured incident records, writes to DB, and emits event to kick off downstream investigation |
| Shared MCP Framework | `apps/common/mcp/` | JSON-RPC 2.0 / FastAPI router | Reusable protocol abstractions, schema generators, rate limiters, timeout guards, and audit loggers |
| Logs Introspection MCP | `apps/mcp_logs/` | `apps/mcp_logs/tools.py` | Exposes `search_logs`, `get_service_logs`, `get_error_rate`, `get_correlated_errors`, `get_logs_around_event` with token budgeting |
</architectural_responsibility_map>

<standard_stack>
## Pinned Standard Stack (Phase 2 Additions & Core Dependencies)

### Python Libraries (Python 3.11+)
| Library | Version | Purpose |
|---------|---------|---------|
| `pydantic` | `^2.6.0` | Event schemas, MCP tool input/output contracts, and validation |
| `aiokafka` | `^0.10.0` | Async non-blocking Kafka consumer for telemetry topics |
| `asyncpg` | `^0.29.0` | High-performance async connection pool and batch insert into PostgreSQL |
| `fastapi` | `^0.110.0` | HTTP transport for MCP JSON-RPC 2.0 endpoints and telemetry health |
| `uvicorn` | `^0.29.0` | ASGI runtime for MCP server endpoints |
| `pytest` | `^8.0.0` | Unit test execution |
| `pytest-asyncio` | `^0.23.0` | Async test fixtures and mock asyncpg/aiokafka testing |

### Database Schemas (`aegisops_db`)
| Table | Primary Keys & Indexes | Purpose |
|-------|------------------------|---------|
| `raw_logs` | `id` (UUID), `(service, timestamp DESC)`, `(service, level, timestamp DESC)` | Durable queryable log records with trace IDs and metadata |
| `raw_metrics` | `id` (UUID), `(service, metric_name, timestamp DESC)` | Time-series metric samples for latency, RPS, and pool stats |
| `deployment_events` | `id` (UUID), `(service, timestamp DESC)` | Version deployment markers and commit metadata |
| `incidents` | `incident_id` (PK, text), `(service, status)`, `(created_at DESC)` | Transactional incident records with severity, status, and summary |
| `incident_events` | `id` (UUID), `(incident_id, timestamp)` | Chronological audit timeline of incident detection and actions |
</standard_stack>

<pitfalls_and_patterns>
## Common Pitfalls & Architectural Patterns

### Pitfalls to Avoid
1. **Unbounded Log Ingestion Commits**: Committing Kafka offsets after every single message destroys consumer throughput.
   *Mitigation:* Micro-batching in `TelemetryConsumer` (e.g. batch size of 100 messages or 1.0 second flush interval) using asyncpg `executemany` or binary copy.
2. **Alert Storming / Duplicate Incidents**: If payment-service enters a failure state emitting 500 errors continuously, the detector could create a new incident every second.
   *Mitigation:* Maintain an in-memory or DB-backed incident deduplication map with a configurable cooldown period (e.g. 10 minutes) per `(service, anomaly_type)`. Ongoing violations update the existing active incident rather than spawning duplicates.
3. **LLM Context Window Blowup in Logs MCP**: Returning 5,000 log lines to an agent exhausts LLM tokens and creates hallucinations.
   *Mitigation:* Implement strict pagination (`limit` capped at 200, default 50) and a `TokenBudgetGuard` that estimates token count and truncates or paginates responses before returning to the caller.
4. **Credential Leakage in Audit Logs**: Passwords or auth tokens present in request payloads or database logs could leak into audit logs.
   *Mitigation:* Implement `Sanitizer` in `mcp_common` that masks sensitive keys (`password`, `token`, `secret`, `authorization`, `connection_string`) across all tool arguments and responses before recording audit logs.
5. **Slow Log Full-Table Scans**: Searching raw logs by text without time bounds can lock PostgreSQL.
   *Mitigation:* Enforce default time bounds (e.g. past 1 hour if unspecified) and composite indexes on `(service, timestamp)` in `raw_logs`.
</pitfalls_and_patterns>

---
*Phase 2 Research completed: 2026-10-10*
