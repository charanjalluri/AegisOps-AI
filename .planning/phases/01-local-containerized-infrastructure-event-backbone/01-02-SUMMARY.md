---
phase: 01-local-containerized-infrastructure-event-backbone
plan: 02
subsystem: kafka
tags: [kafka, events, schemas, pydantic, topics, telemetry]

requires:
  - phase: 01-01
    provides: Kafka broker container definition with dual listeners (kafka:9092, localhost:29092)
provides:
  - Kafka topic provisioner script declaring 8 operational topics idempotently
  - Strongly typed Pydantic event models (RawLogEvent, RawMetricEvent, DeploymentEvent, AlertEvent, IncidentEvent, AIActionEvent)
  - Unit test suite verifying schema validation and serialization offline
  - Integration test stub for live cluster validation

actuals:
  tokens: 16200
  tasks: 3
  commits: 1

tech-stack:
  added:
    - "pydantic"
    - "scripts/init_kafka.py"
    - "apps/common/schemas/events.py"
  patterns:
    - "Centralized Pydantic telemetry models with UTC timestamps and UUID event IDs"
    - "Explicit partition and retention configurations per operational topic"
    - "Idempotent topic provisioning with retry and graceful error handling"

key-files:
  created:
    - scripts/init_kafka.py
    - scripts/init-kafka.py
    - infrastructure/kafka/init-topics.sh
    - apps/common/__init__.py
    - apps/common/schemas/__init__.py
    - apps/common/schemas/events.py
    - tests/unit/test_kafka_spec.py
    - tests/unit/test_event_schemas.py
    - tests/integration/test_kafka_topics.py

key-decisions:
  - "Configured all 8 operational topics (logs.raw, metrics.raw, alerts.raw, deployments.events, incidents.created, incidents.updated, ai.analysis, ai.actions) with 7 to 30 day retentions."
  - "Built reusable Pydantic models with enum-backed log levels, risk levels, and incident severities."

requirements-completed:
  - INFRA-02
---

# Plan 01-02 Summary: Kafka Event Bus Setup & Telemetry Schemas

Delivered the Apache Kafka event streaming backbone provisioner and shared Pydantic telemetry models. Created `scripts/init_kafka.py` and `infrastructure/kafka/init-topics.sh` declaring the 8 operational topics with partitions and retention settings. Implemented strongly typed schemas in `apps/common/schemas/events.py` for raw logs, metrics, deployments, alerts, incidents, and AI actions. Verified 100% of schema serialization, validation, and topic specifications with offline unit tests.
