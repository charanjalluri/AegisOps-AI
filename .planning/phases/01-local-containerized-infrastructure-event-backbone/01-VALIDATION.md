---
phase: "1"
slug: "local-containerized-infrastructure-event-backbone"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-08"
---

# Phase 1 — Validation Strategy

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
- **After every plan wave:** Run `.venv\Scripts\pytest tests/unit -v` and syntax/config validation
- **Before `/gsd-verify-work`:** Unit test suite is 100% green; Docker configuration is valid
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INFRA-01 | T-01-01 | Docker Compose defines pinned images and validates syntax | unit | `python tests/unit/test_compose_spec.py` | ✅ Yes | ✅ green |
| 01-01-02 | 01 | 1 | INFRA-01 | T-01-02 | Postgres init script creates dual DBs with LF line endings | unit | `python tests/unit/test_postgres_script.py` | ✅ Yes | ✅ green |
| 01-01-03 | 01 | 1 | INFRA-01 | T-01-03 | pyproject.toml and .env.example provide complete configurations | unit | `python tests/unit/test_env_and_config.py` | ✅ Yes | ✅ green |
| 01-02-01 | 02 | 2 | INFRA-02 | T-01-04 | Kafka topic provisioner defines 8 operational topics idempotently | unit | `python tests/unit/test_kafka_spec.py` | ✅ Yes | ✅ green |
| 01-02-02 | 02 | 2 | INFRA-02 | — | Pydantic event models validate telemetry schemas | unit | `pytest tests/unit/test_event_schemas.py -v` | ✅ Yes | ✅ green |
| 01-03-01 | 03 | 3 | INFRA-04 | T-01-06 | FastAPI /health and /ready endpoints decouple hard vs soft deps | unit | `pytest tests/unit/test_health_probes.py -v` | ✅ Yes | ✅ green |
| 01-03-02 | 03 | 3 | DEMO-01 | T-01-07 | payment-service simulator executes real HTTP & DB logic | unit | `pytest tests/unit/test_payment_simulator_unit.py -v` | ✅ Yes | ✅ green |
| 01-03-03 | 03 | 3 | INFRA-03 | T-01-08 | Makefile defines setup, up, down, clean, reset-demo targets | unit | `python tests/unit/test_makefile_targets.py` | ✅ Yes | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/test_compose_spec.py` — verifies pinned image tags, listener ports, volumes
- [x] `tests/unit/test_postgres_script.py` — verifies LF line endings and dual database creation
- [x] `tests/unit/test_env_and_config.py` — verifies environment configuration keys and types
- [x] `tests/unit/test_kafka_spec.py` — verifies topic names, partition count, and replication
- [x] `tests/unit/test_event_schemas.py` — tests serialization/deserialization across all 6 telemetry models
- [x] `tests/unit/test_health_probes.py` — tests `/health` and `/ready` with mocked dependencies
- [x] `tests/unit/test_payment_simulator_unit.py` — tests payment-service API routes and transaction models
- [x] `tests/unit/test_makefile_targets.py` — tests Makefile target existence and clean/reset targets

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
- [x] Wave 0 covers all unit tests
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (Wave 0 and all Phase 1 test tasks verified green)
