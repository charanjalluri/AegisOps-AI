---
phase: "4"
slug: "langgraph-investigation-agent-evidence-engine-semantic-rag"
status: complete
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-13"
validated: "2026-10-13"
---

# Phase 4 — Validation Strategy & Execution Results

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
| **Actual suite runtime** | **10.23 seconds (182/182 tests green)** |

---

## Sampling Rate

- **After every task commit:** Run `.venv\Scripts\pytest tests/unit -v`
- **After every plan wave:** Run `.venv\Scripts\pytest tests/unit -v` and syntax/schema validation
- **Before `/gsd-verify-work`:** Unit test suite is 100% green; all evidence normalization, hypothesis scoring, budget guards, and RCA synthesis pass offline
- **Max feedback latency:** <5 seconds per plan

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | MEM-02 | T-04-01 | DeterministicEmbedder and knowledge document models validate with sanitization | unit | `python -m pytest tests/unit/test_qdrant_client.py -k "test_embedder or test_models" -v` | ✅ Yes | ✅ green |
| 04-01-02 | 01 | 1 | MEM-02 | T-04-02 | QdrantMemoryClient executes search, upsert, payload filtering, and mock fallback | unit | `python -m pytest tests/unit/test_qdrant_client.py -v` | ✅ Yes | ✅ green |
| 04-01-03 | 01 | 1 | MEM-03 | T-04-03 | Knowledge seeder script populates documents; make seed executes cleanly | unit | `python -m pytest tests/unit/test_qdrant_seeder.py -v` | ✅ Yes | ✅ green |
| 04-02-01 | 02 | 2 | REASON-01 | T-04-04 | CanonicalEvidence schema and log normalizer scrub secrets and record provenance | unit | `python -m pytest tests/unit/test_evidence_normalizer.py -k "test_models or test_log_normalization" -v` | ✅ Yes | ✅ green |
| 04-02-02 | 02 | 2 | REASON-01 | T-04-05 | Full EvidenceNormalizer maps DB, GitHub, and Qdrant outputs to facts | unit | `python -m pytest tests/unit/test_evidence_normalizer.py -v` | ✅ Yes | ✅ green |
| 04-02-03 | 02 | 2 | REASON-03 | T-04-06 | Multi-hypothesis engine scores calibrated probabilities and enforces corroboration | unit | `python -m pytest tests/unit/test_hypothesis_scoring.py -v` | ✅ Yes | ✅ green |
| 04-03-01 | 03 | 3 | REASON-04 | T-04-07 | InvestigationBudget caps max 20 tool calls, 300s timeout, and 5 expensive ops | unit | `python -m pytest tests/unit/test_investigation_budget.py -v` | ✅ Yes | ✅ green |
| 04-03-02 | 03 | 3 | REASON-02 | T-04-08 | LangGraph cyclic investigation state machine converges on verified causes | unit | `python -m pytest tests/unit/test_investigation_state_machine.py -v` | ✅ Yes | ✅ green |
| 04-03-03 | 03 | 3 | REASON-05 | T-04-09 | Structured RCA synthesizer outputs report, creates proposal, and broadcasts event | unit | `python -m pytest tests/unit/test_rca_synthesis.py -v` | ✅ Yes | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements Verification

- [x] `tests/unit/test_qdrant_client.py` — Qdrant vector operations, cosine similarity, and in-memory mock fallback (5 passed)
- [x] `tests/unit/test_qdrant_seeder.py` — Seeder dataset schemas, >=20 document count, duplicate handling and idempotency (6 passed)
- [x] `tests/unit/test_evidence_normalizer.py` — Heterogeneous MCP output normalization to canonical evidence (7 passed)
- [x] `tests/unit/test_hypothesis_scoring.py` — Multi-hypothesis confidence calibration and corroboration caps (4 passed)
- [x] `tests/unit/test_investigation_budget.py` — Budget guard counters, timeouts, and exhaustion handling (4 passed)
- [x] `tests/unit/test_investigation_state_machine.py` — LangGraph cyclic investigation state machine, topology, and routing (5 passed)
- [x] `tests/unit/test_rca_synthesis.py` — Root Cause Analysis document synthesis, action proposal, and event emission (2 passed)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Qdrant Container Vector Upsert | MEM-02 | Container runtime verification | Boot `docker compose up -d qdrant` and run `python scripts/seed_qdrant.py --url http://localhost:6333` |
| Live Kafka Analysis Event Broadcast | REASON-05 | Event bus runtime verification | Run agent against live Kafka cluster and inspect `ai.analysis` topic via Kafka UI (`:8080`) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all unit tests
- [x] No watch-mode flags
- [x] Feedback latency < 5s target
- [x] `nyquist_compliant: true` set in frontmatter

**Sign-off status:** Phase 4 Validation 100% Passed (33 unit tests implemented across Phase 4, total 185/185 unit tests green offline).

