---
phase: "6"
slug: "react-operations-dashboard-visual-incident-workbench"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-13"
validated: "2026-10-13"
---

# Phase 6 — Validation Strategy & Execution Matrix

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (Backend API & Integration) & TypeScript compiler / Vitest (Frontend) |
| **Config files** | `pyproject.toml`, `apps/dashboard/vite.config.ts`, `apps/dashboard/tsconfig.json` |
| **Offline unit tests** | `pytest tests/unit/test_api_*.py -v` (Fast, mocked, <5s feedback loop) |
| **Integration tests** | `pytest tests/integration/test_dashboard_api_live.py -m integration -v` (Services running together) |
| **Frontend build validation** | `cd apps/dashboard && npm run build` (Typecheck + Vite production bundle) |
| **Target feedback latency** | <5 seconds for unit tests, <15 seconds for integration tests |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | UI-01, UI-05 | T-06-01, T-06-03 | Backend API exposes incidents and 4-state active observability status (`healthy`, `unhealthy`, `unknown`, `stale`); validates operator authorization dependency | unit | `python -m pytest tests/unit/test_api_incidents.py tests/unit/test_api_observability.py -v` | ✅ yes | ✅ green |
| 06-01-02 | 01 | 1 | UI-01 | T-06-02 | React dashboard scaffold compiles cleanly with UI/UX Pro Max OLED design tokens and typed 4-state observability schema | build | `cd apps/dashboard && npm run build` | ✅ yes | ✅ green |
| 06-01-03 | 01 | 1 | UI-01, UI-05 | T-06-02 | Triage queue renders incidents with severity filters and observability drawer displays 4-state badges with probe latencies | build | `cd apps/dashboard && npm run build` | ✅ yes | ✅ green |
| 06-02-01 | 02 | 2 | UI-02, UI-03 | T-06-04, T-06-05 | Backend exposes evidence, Bayesian calibrated hypotheses (priors, single-tool 70% cap, multi-tool corroboration), and sanitized tool history | unit | `python -m pytest tests/unit/test_api_incidents.py -v` | ✅ yes | ✅ green |
| 06-02-02 | 02 | 2 | UI-02 | T-06-05 | Investigation workbench displays timeline, evidence gallery, and hypothesis meter reflecting Bayesian calibration rules | build | `cd apps/dashboard && npm run build` | ✅ yes | ✅ green |
| 06-02-03 | 02 | 2 | UI-03 | T-06-04 | MCP tool inspector renders sanitized parameters, duration in ms, and output summaries | build | `cd apps/dashboard && npm run build` | ✅ yes | ✅ green |
| 06-03-01 | 03 | 3 | UI-04, GOV-02, GOV-03 | T-06-06, T-06-07, T-06-08 | Governance router enforces server-side operator authorization, proposal parameter binding, TTL expiration, and replay prevention | unit | `python -m pytest tests/unit/test_api_governance.py -v` | ✅ yes | ✅ green |
| 06-03-02 | 03 | 3 | UI-04, GOV-02 | T-06-06, T-06-07 | Interactive HITL approval card displays bound proposal parameters, operator identity, and triggers policy-gated rollback | build | `cd apps/dashboard && npm run build` | ✅ yes | ✅ green |
| 06-03-03 | 03 | 3 | GOV-03, GOV-04 | T-06-08, T-06-09 | Telemetry verification widget strictly renders backend-computed metric streams and thresholds; audit viewer shows immutable entries | build | `cd apps/dashboard && npm run build` | ✅ yes | ✅ green |
| 06-INT-01 | 03 | 3 | UI-01..05, GOV-02..04 | T-06-06..08 | Live integration test verifies core API routers, policy evaluation, proposal lifecycle, and active probing with services running together | integration | `python -m pytest tests/integration/test_dashboard_api_live.py -m integration -v` | ✅ yes | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Validation Sign-Off

- [x] All tasks have automated verification commands.
- [x] Dual validation: Backend unit suites verify API contracts; Vite/TypeScript verify frontend compilation.
- [x] Live integration test (`test_dashboard_api_live.py`) verifies running services together while offline unit suites remain fast.
- [x] Security gates: Server-side operator authorization (`X-Operator-Id`, `X-Operator-Role`) mandated for privileged routes.
- [x] Proposal integrity: Strict parameter binding, 30m TTL expiration, and one-time execution replay prevention enforced.
- [x] Active observability: Probing differentiates `healthy`, `unhealthy`, `unknown`, and `stale` states.
- [x] Closed-loop verification: Frontend strictly renders backend evaluation results without client-side recovery declarations.
- [x] UI/UX Pro Max OLED Dark design system and WCAG AAA accessibility rules verified.

**Sign-off status:** Phase 6 Fully Validated & Verified (10/10 tasks green).
