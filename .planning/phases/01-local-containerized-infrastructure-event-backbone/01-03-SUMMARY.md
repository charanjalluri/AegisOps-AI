---
phase: 01-local-containerized-infrastructure-event-backbone
plan: 03
subsystem: api-simulator
tags: [fastapi, probes, simulator, postgres, makefile, automation]

requires:
  - phase: 01-01
    provides: Docker Compose topology with PostgreSQL and Kafka
  - phase: 01-02
    provides: Pydantic telemetry models and Kafka operational topics
provides:
  - Platform API with /health and decoupled /ready probes (Postgres+Kafka hard, Qdrant+n8n soft)
  - Real lightweight payment-service simulator (FastAPI app, PostgreSQL persistence, telemetry emission)
  - Developer Makefile automation with clean (volume removal) and reset-demo lifecycle targets
  - Complete offline unit test suite validating probes, simulator logic, and Makefile targets

actuals:
  tokens: 21500
  tasks: 3
  commits: 1

tech-stack:
  added:
    - "apps/api"
    - "apps/payment_service"
    - "Makefile"
    - "scripts/reset-demo.py"
  patterns:
    - "Decoupled readiness probing: hard dependencies gate 200 OK while soft dependencies report status without 503"
    - "Real microservice simulator with transactional database layer and telemetry event emission"
    - "Clean and reset lifecycle targets in developer Makefile"

key-files:
  created:
    - apps/api/__init__.py
    - apps/api/main.py
    - apps/api/routers/__init__.py
    - apps/api/routers/health.py
    - apps/payment_service/__init__.py
    - apps/payment_service/main.py
    - apps/payment_service/models.py
    - apps/payment_service/database.py
    - Makefile
    - scripts/reset-demo.py
    - tests/unit/test_health_probes.py
    - tests/unit/test_payment_simulator_unit.py
    - tests/unit/test_makefile_targets.py

key-decisions:
  - "Decoupled readiness checks so that non-critical Phase 1 components (Qdrant, n8n) do not block core platform readiness."
  - "Implemented payment-service as an authentic HTTP + PostgreSQL service generating real transactions rather than static fake logs."
  - "Configured make clean to explicitly remove persistent volumes via docker compose down -v."

requirements-completed:
  - INFRA-03
  - INFRA-04
  - DEMO-01
---

# Plan 01-03 Summary: Microservice Simulator, Health Probes & Developer Automation

Delivered the platform core API and simulated microservice. Implemented FastAPI liveness (`/health`) and decoupled readiness (`/ready`) probes evaluating PostgreSQL and Kafka as hard dependencies while treating Qdrant and n8n as non-blocking soft status. Built a real lightweight HTTP + PostgreSQL microservice simulator in `apps/payment_service/` executing SQL transactions against `demo_payment_db` and emitting structured operational telemetry (`RawLogEvent`, `RawMetricEvent`). Authored the developer `Makefile` with clean and reset lifecycle targets, and verified all components with 29 passing unit tests.
