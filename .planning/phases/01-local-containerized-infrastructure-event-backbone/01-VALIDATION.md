---
phase: "1"
slug: "local-containerized-infrastructure-event-backbone"
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-10-08"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x / Docker Compose health checks |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/unit -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit -v`
- **After every plan wave:** Run `docker compose ps` & `pytest tests/ -v`
- **Before `/gsd-verify-work`:** All containers healthy and readiness probe returns 200 OK
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INFRA-01 | T-01-01 | Postgres dual DB init creates aegisops_db & demo_payment_db | integration | `pytest tests/integration/test_db_init.py` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | INFRA-01 | T-01-02 | Docker Compose boots with all healthy services | integration | `docker compose config` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | INFRA-02 | T-01-03 | Kafka topic init script idempotently creates all 8 topics | integration | `pytest tests/integration/test_kafka_topics.py` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | INFRA-02 | — | Event schema models validate telemetry payloads | unit | `pytest tests/unit/test_event_schemas.py` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 3 | INFRA-04 | T-01-04 | GET /health and /ready return 200 with dependency statuses | integration | `pytest tests/integration/test_health_probes.py` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 3 | DEMO-01 | — | payment-service baseline v2.8.0 emits healthy traffic to Kafka | integration | `pytest tests/integration/test_payment_simulator.py` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 3 | INFRA-03 | — | Makefile targets (up, down, setup) execute cleanly | integration | `make setup` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures for Docker and Kafka connections
- [ ] `tests/unit/test_event_schemas.py` — unit tests for telemetry models
- [ ] `tests/integration/test_db_init.py` — DB connection & schema tests
- [ ] `tests/integration/test_kafka_topics.py` — Kafka admin topic verification
- [ ] `tests/integration/test_health_probes.py` — FastAPI probe endpoint tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Kafka UI message inspection | INFRA-02 | Visual GUI verification | Open http://localhost:8080 and confirm topic lists and partitions |
| Grafana & Prometheus dashboards | INFRA-01 | Visual GUI verification | Open http://localhost:3000 and verify Prometheus datasource |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
