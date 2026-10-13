---
phase: "5"
slug: "policy-engine-human-approval-controlled-remediation-verification"
status: planned
nyquist_compliant: true
wave_0_complete: false
created: "2026-10-13"
validated: null
---

# Phase 5 — Validation Strategy & Execution Matrix

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
| **Target suite runtime** | <15 seconds (all offline tests green) |

---

## Sampling Rate

- **After every task commit:** Run the dedicated task test command (`pytest tests/unit/test_... -v`)
- **After every plan wave:** Run full unit suite `.venv\Scripts\pytest tests/unit -v`
- **Before `/gsd-verify-work`:** Unit test suite is 100% green; all policy gates, deployment tools, n8n fallbacks, and verification loops pass offline
- **Max feedback latency:** <5 seconds per task

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | GOV-01 | T-05-02 | RiskClassifier classifies operations into 5 tiers and rejects destructive operations | unit | `python -m pytest tests/unit/test_policy_risk_tiers.py -v` | ⬜ pending | ⬜ pending |
| 05-01-02 | 01 | 1 | GOV-01, GOV-02 | T-05-01 | PolicyEngine allows READ/LOW actions and blocks unapproved HIGH-risk mutations | unit | `python -m pytest tests/unit/test_policy_engine.py -v` | ⬜ pending | ⬜ pending |
| 05-01-03 | 01 | 1 | GOV-02, GOV-04 | T-05-03 | ApprovalManager requires operator ID and GovernanceAuditLogger creates immutable entries | unit | `python -m pytest tests/unit/test_hitl_approval.py -v` | ⬜ pending | ⬜ pending |
| 05-02-01 | 02 | 2 | MCP-06 | T-05-01 | Deployment MCP inspects current version, previous version, and deployment history | unit | `python -m pytest tests/unit/test_deployment_mcp_tools.py -k "test_version or test_history" -v` | ⬜ pending | ⬜ pending |
| 05-02-02 | 02 | 2 | MCP-06, GOV-02 | T-05-01 | Rollback execution validates proposal through PolicyEngine; rejects unapproved requests | unit | `python -m pytest tests/unit/test_deployment_mcp_tools.py tests/unit/test_deployment_mcp_server.py -v` | ⬜ pending | ⬜ pending |
| 05-02-03 | 02 | 2 | MCP-07 | T-05-03 | n8n MCP dispatches notification workflows with seamless offline mock fallback | unit | `python -m pytest tests/unit/test_n8n_mcp_tools.py tests/unit/test_n8n_mcp_server.py -v` | ⬜ pending | ⬜ pending |
| 05-03-01 | 03 | 3 | GOV-03 | T-05-04 | Telemetry verification models evaluate thresholds and record metric samples | unit | `python -m pytest tests/unit/test_remediation_verifier.py -k "test_condition or test_models" -v` | ⬜ pending | ⬜ pending |
| 05-03-02 | 03 | 3 | GOV-03 | T-05-05 | RemediationVerifier polls error rate and connection pool with consecutive pass rules and timeout | unit | `python -m pytest tests/unit/test_remediation_verifier.py -v` | ⬜ pending | ⬜ pending |
| 05-03-03 | 03 | 3 | GOV-03, GOV-04 | T-05-06 | IncidentClosurePipeline verifies metrics, updates proposal/incident, emits audit and n8n alerts | unit | `python -m pytest tests/unit/test_incident_closure_pipeline.py -v` | ⬜ pending | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements Verification

- [ ] `tests/unit/test_policy_risk_tiers.py` — Risk tier classification and destructive command detection
- [ ] `tests/unit/test_policy_engine.py` — Policy authorization and unapproved rollback rejection
- [ ] `tests/unit/test_hitl_approval.py` — Operator approval workflow and immutable audit log persistence
- [ ] `tests/unit/test_deployment_mcp_tools.py` — Version inspection and policy-gated rollback tools
- [ ] `tests/unit/test_deployment_mcp_server.py` — JSON-RPC 2.0 endpoints on port 8006
- [ ] `tests/unit/test_n8n_mcp_tools.py` — Workflow triggers and offline mock execution
- [ ] `tests/unit/test_n8n_mcp_server.py` — JSON-RPC 2.0 endpoints on port 8007
- [ ] `tests/unit/test_remediation_verifier.py` — Telemetry polling loop and timeout guard
- [ ] `tests/unit/test_incident_closure_pipeline.py` — End-to-end verified incident closure and alerting

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Deployment MCP rollback | MCP-06 | Container service state check | Spin up payment-service container, invoke rollback via MCP on `:8006`, verify version endpoint |
| Live n8n webhook notification | MCP-07 | External webhook container check | Boot n8n container, trigger alert workflow on `:8007`, verify Slack channel / mock webhook log |
| Closed-loop scenario recovery | GOV-03 | Multi-service end-to-end integration | Run `make scenario` with leaky deployment and observe policy gate -> approval -> rollback -> verified recovery |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all unit tests
- [x] No watch-mode flags
- [x] Feedback latency < 5s target
- [x] `nyquist_compliant: true` set in frontmatter

**Sign-off status:** Phase 5 Validation Matrix Ready for Execution.
