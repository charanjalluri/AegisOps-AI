---
phase: "2"
slug: "telemetry-ingestion-deterministic-detection-logs-mcp"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-10"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` |
| **Offline unit tests** | `pytest tests/unit -v` |
| **Docker integration tests** | `pytest tests/integration -v` (runs when containers are active) |
| **Full suite command** | `pytest tests/unit -v` (default offline validation gate) |
| **Estimated runtime** | ~3-5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv\Scripts\pytest tests/unit -v`
- **After every plan wave:** Run `.venv\Scripts\pytest tests/unit -v` and syntax/schema validation
- **Before `/gsd-verify-work`:** Unit test suite is 100% green; all MCP contracts and detection rules pass offline
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | MCP-01 | T-02-01 | MCP protocol models serialize JSON-RPC 2.0 requests, responses, and errors | unit | `python -m pytest tests/unit/test_mcp_common_protocol.py -v` | ✅ Yes | ✅ green |
| 02-01-02 | 01 | 1 | MCP-01 | T-02-02 | BaseMCPServer enforces tool decorators, timeouts, and rate limits | unit | `python -m pytest tests/unit/test_mcp_common_server.py -v` | ✅ Yes | ✅ green |
| 02-01-03 | 01 | 1 | MCP-01 | T-02-03 | Sanitizer redacts credentials in audit logs and TokenBudgetGuard enforces caps | unit | `python -m pytest tests/unit/test_mcp_common_audit_and_security.py -v` | ✅ Yes | ✅ green |
| 02-02-01 | 02 | 2 | DETECT-01 | T-02-04 | PostgreSQL telemetry schema DDL creates raw_logs, metrics, and incident tables | unit | `python -m pytest tests/unit/test_telemetry_schema.py -v` | ✅ Yes | ✅ green |
| 02-02-02 | 02 | 2 | DETECT-01 | T-02-05 | TelemetryConsumer micro-batches Kafka events safely into persistence | unit | `python -m pytest tests/unit/test_telemetry_consumer.py -v` | ✅ Yes | ✅ green |
| 02-02-03 | 02 | 2 | DETECT-02, DETECT-03 | T-02-06 | AnomalyDetector detects error spikes, latency, and DB timeouts with cooldown | unit | `python -m pytest tests/unit/test_anomaly_detector.py -v` | ✅ Yes | ✅ green |
| 02-03-01 | 03 | 3 | MCP-02 | T-02-07 | Logs MCP defines 5 structured tools with validated Pydantic schemas | unit | `python -m pytest tests/unit/test_logs_mcp_spec.py -v` | ✅ Yes | ✅ green |
| 02-03-02 | 03 | 3 | MCP-02 | T-02-08 | Logs MCP tool implementations execute queries, time windows, and token budgets | unit | `python -m pytest tests/unit/test_logs_mcp_tools.py -v` | ✅ Yes | ✅ green |
| 02-03-03 | 03 | 3 | MCP-02 | T-02-09 | Logs MCP server exposes JSON-RPC 2.0 endpoint with audit logging and health check | unit | `python -m pytest tests/unit/test_logs_mcp_server.py -v` | ✅ Yes | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/test_mcp_common_protocol.py` — JSON-RPC 2.0 & MCP protocol schemas
- [x] `tests/unit/test_mcp_common_server.py` — BaseMCPServer execution, timeouts, rate limiting
- [x] `tests/unit/test_mcp_common_audit_and_security.py` — credential masking, audit logs, token budgets
- [x] `tests/unit/test_telemetry_schema.py` — schema DDL and table definitions
- [x] `tests/unit/test_telemetry_consumer.py` — batch consumer ingestion and retry
- [x] `tests/unit/test_anomaly_detector.py` — sliding-window detection rules, cooldown, and incident generation
- [x] `tests/unit/test_logs_mcp_spec.py` — Logs MCP tool schema registration
- [x] `tests/unit/test_logs_mcp_tools.py` — Logs MCP tool query operations and token budgeting
- [x] `tests/unit/test_logs_mcp_server.py` — Logs MCP server JSON-RPC endpoint & healthchecks

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Kafka UI telemetry inspection | DETECT-01 | Visual GUI verification | Open http://localhost:8080 and view streaming messages on `logs.raw`, `metrics.raw`, and `incidents.created` |
| Live Incident Triggering | DETECT-03 | Live integration verification | Trigger payment-service failure and verify incident appears in `incidents` table and `incidents.created` topic |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all unit tests
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (Wave 0 test definitions and tasks mapped to all Phase 2 requirements)
