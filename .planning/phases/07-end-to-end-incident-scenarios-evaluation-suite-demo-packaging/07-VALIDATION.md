---
phase: "7"
slug: "end-to-end-incident-scenarios-evaluation-suite-demo-packaging"
status: passed
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-13"
verified: "2026-10-13"
---

# Phase 7 — Validation Strategy & Execution Matrix

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|:---|:---|
| **Framework** | pytest 9.x (Backend & Evaluation CLI) |
| **Config files** | `pyproject.toml`, `Makefile` |
| **Offline unit tests** | `pytest tests/unit/test_scenario_*.py tests/unit/test_evaluation_*.py tests/unit/test_demo_scripts.py -v` (Fast, <5s feedback loop) |
| **Benchmark runner** | `python -m apps.evaluation.runner --all` (Evaluates all 5 scenarios against ground truth) |
| **Demo runner validation** | `python scripts/run_demo.py --standalone --auto-approve` (Validates full closed loop in standalone mode) |
| **Integration tests** | `pytest tests/integration/test_end_to_end_demo_live.py -m integration -v` |
| **Target feedback latency** | <5 seconds for unit tests, <15 seconds for evaluation and demo runners |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| 07-01-01 | 01 | 1 | DEMO-02 | T-07-01 | Pydantic scenario schemas parse and validate YAML with strict safe loader, rejecting malicious executable tags | unit | `python -m pytest tests/unit/test_scenario_runner.py -k "test_scenario_yaml_schema" -v` | ✅ | ✅ green |
| 07-01-02 | 01 | 1 | DEMO-02 | T-07-01 | Flagship scenario `database-connection-leak.yaml` defines complete ground-truth contract | unit | `python -m pytest tests/unit/test_scenario_runner.py -k "test_flagship_scenario_loaded" -v` | ✅ | ✅ green |
| 07-01-03 | 01 | 1 | DEMO-01, DEMO-02 | T-07-02 | Scenario runner injects faults into simulator/Kafka and triggers anomaly detection in live and standalone modes | unit | `python -m pytest tests/unit/test_scenario_runner.py -k "test_failure_injection_lifecycle" -v` | ✅ | ✅ green |
| 07-02-01 | 02 | 2 | DEMO-03 | T-07-01 | Benchmark catalog includes 5 valid declarative operational failure scenarios | unit | `python -m pytest tests/unit/test_scenario_benchmark.py -k "test_all_scenarios_exist" -v` | ✅ | ✅ green |
| 07-02-02 | 02 | 2 | DEMO-04 | T-07-04 | Evaluation metrics calculate RCA accuracy, tool precision/recall, zero hallucination, and action match with calibrated math | unit | `python -m pytest tests/unit/test_evaluation_metrics.py -v` | ✅ | ✅ green |
| 07-02-03 | 02 | 2 | DEMO-04 | T-07-04 | Automated evaluation runner executes all scenarios and outputs structured ASCII and JSON benchmark reports | unit/cli | `python -m apps.evaluation.runner --all` | ✅ | ✅ green |
| 07-03-01 | 03 | 3 | DEMO-02 | T-07-02 | `run_demo.py` executes full closed-loop demo (inject $\rightarrow$ investigate $\rightarrow$ approve $\rightarrow$ rollback $\rightarrow$ verify $\rightarrow$ close) | unit/cli | `python scripts/run_demo.py --standalone --auto-approve` | ✅ | ✅ green |
| 07-03-02 | 03 | 3 | DEMO-01 | T-07-03 | `reset_demo.py` cleanly resets demo database and test incidents without touching system data | unit | `python -m pytest tests/unit/test_demo_scripts.py -k "test_reset_demo" -v` | ✅ | ✅ green |
| 07-03-03 | 03 | 3 | INFRA-01 | T-07-02 | Prometheus alerting rules and Grafana dashboard JSON are syntactically valid | unit | `python -m pytest tests/unit/test_demo_scripts.py -k "test_prometheus_grafana_configs" -v` | ✅ | ✅ green |
| 07-03-04 | 03 | 3 | DEMO-01, DEMO-04 | T-07-02 | Makefile defines `demo:`, `reset-demo:`, and `evaluate:` targets | unit | `python -m pytest tests/unit/test_makefile_targets.py -v` | ✅ | ✅ green |
| 07-INT-01 | 03 | 3 | DEMO-02, DEMO-04 | T-07-02 | Live integration test verifies end-to-end demo execution with co-running components | integration | `python -m pytest tests/integration/test_end_to_end_demo_live.py -m integration -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Validation Sign-Off Criteria

- [x] All 10 tasks have automated verification commands.
- [x] Complete offline unit test suite remains 100% green and fast (<5 seconds).
- [x] Evaluation runner (`make evaluate`) executes all 5 benchmark scenarios and verifies composite scores $\ge 80\%$ (Achieved 96.7%).
- [x] Demo runner (`make demo`) executes the end-to-end closed loop with verification and resolution.
- [x] Reset script (`make reset-demo`) cleanly and idempotently returns environment to baseline.
- [x] Quickstart guide (`docs/QUICKSTART.md`) is documented and verified.
