---
phase: "3"
slug: "investigation-tooling-suite-database-github-incident-mcps"
status: complete
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-10"
validated: "2026-10-10"
---

# Phase 3 — Validation Strategy & Execution Results

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
| **Actual suite runtime** | **1.42 seconds (152/152 tests green)** |

---

## Sampling Rate

- **After every task commit:** Run `.venv\Scripts\pytest tests/unit -v`
- **After every plan wave:** Run `.venv\Scripts\pytest tests/unit -v` and syntax/schema validation
- **Before `/gsd-verify-work`:** Unit test suite is 100% green; all MCP contracts and mutation guards pass offline
- **Max feedback latency:** <2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | MCP-03 | T-03-01 | SQLMutationValidator rejects all mutations, DDL, and chained statements | unit | `python -m pytest tests/unit/test_database_mcp_validator.py -v` | ✅ Yes | ✅ green |
| 03-01-02 | 01 | 1 | MCP-03 | T-03-02 | Database MCP tools execute read-only pool, health, and slow query diagnostics | unit | `python -m pytest tests/unit/test_database_mcp_tools.py -v` | ✅ Yes | ✅ green |
| 03-01-03 | 01 | 1 | MCP-03 | T-03-03 | Database MCP server exposes JSON-RPC 2.0 endpoints with audit logging | unit | `python -m pytest tests/unit/test_database_mcp_server.py -v` | ✅ Yes | ✅ green |
| 03-02-01 | 02 | 2 | MCP-04 | T-03-04 | GitHub MCP models and LocalMockGitProvider return realistic commits and diffs | unit | `python -m pytest tests/unit/test_github_mcp_spec.py -v` | ✅ Yes | ✅ green |
| 03-02-02 | 02 | 2 | MCP-04 | T-03-05 | GitHub MCP tools inspect PRs, file diffs, commits, and deployment history | unit | `python -m pytest tests/unit/test_github_mcp_tools.py -v` | ✅ Yes | ✅ green |
| 03-02-03 | 02 | 2 | MCP-04 | T-03-06 | GitHub MCP server exposes JSON-RPC 2.0 endpoints and stdio runner | unit | `python -m pytest tests/unit/test_github_mcp_server.py -v` | ✅ Yes | ✅ green |
| 03-03-01 | 03 | 3 | MEM-01 | T-03-07 | Short-term memory schema DDL creates evidence, hypotheses, and proposal tables | unit | `python -m pytest tests/unit/test_incident_storage_schema.py -v` | ✅ Yes | ✅ green |
| 03-03-02 | 03 | 3 | MCP-05 | T-03-08 | Incident MCP tools manage evidence chain, hypothesis scores, and proposals | unit | `python -m pytest tests/unit/test_incident_mcp_tools.py -v` | ✅ Yes | ✅ green |
| 03-03-03 | 03 | 3 | MCP-05, MEM-01 | T-03-09 | Incident MCP server handles JSON-RPC 2.0 dispatch and state persistence | unit | `python -m pytest tests/unit/test_incident_mcp_server.py -v` | ✅ Yes | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements Verification

- [x] `tests/unit/test_database_mcp_validator.py` — SQL parser and mutation rejection tests (27 passed)
- [x] `tests/unit/test_database_mcp_tools.py` — Database diagnostic tools with mock pools (7 passed)
- [x] `tests/unit/test_database_mcp_server.py` — Database MCP server JSON-RPC dispatch (6 passed)
- [x] `tests/unit/test_github_mcp_spec.py` — Git provider models and mock datasets (5 passed)
- [x] `tests/unit/test_github_mcp_tools.py` — Git tool operations (diffs, commits, PRs) (7 passed)
- [x] `tests/unit/test_github_mcp_server.py` — GitHub MCP server JSON-RPC dispatch (8 passed)
- [x] `tests/unit/test_incident_storage_schema.py` — Short-term memory DDL and entity models (5 passed)
- [x] `tests/unit/test_incident_mcp_tools.py` — Evidence, hypothesis, and proposal tools (7 passed)
- [x] `tests/unit/test_incident_mcp_server.py` — Incident MCP server JSON-RPC dispatch and recovery (4 passed)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Database Introspection | MCP-03 | Container runtime verification | Run `python -m apps.mcp_database.main` with running postgres and verify `get_connection_pool` returns demo_payment_db pool metrics |
| Live Git Token Integration | MCP-04 | External network verification | Set `GITHUB_TOKEN` and query a live GitHub repository |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all unit tests
- [x] No watch-mode flags
- [x] Feedback latency < 5s (actual 1.42s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** Phase 3 Validation 100% Passed (76 new unit tests implemented, total 152/152 tests green).
