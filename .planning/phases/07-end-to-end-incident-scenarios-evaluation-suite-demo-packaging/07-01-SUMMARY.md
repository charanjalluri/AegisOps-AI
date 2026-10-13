# Plan 07-01: Declarative Incident Scenario Engine — Execution Summary

**Execution Status:** COMPLETED & VERIFIED
**Wave:** 1
**Requirements:** `DEMO-02`, `DEMO-01`

---

## 1. Work Completed

1. **Declarative Scenario Models (`apps/demo/models.py`):**
   - Implemented `ScenarioDefinition`, `FailureInjection`, `GroundTruthContract`, `RemediationProposal`, and `VerificationCondition` schemas with strict Pydantic parsing.
   - Built severity normalization handling both canonical `IncidentSeverity` (`SEV-1`..`SEV-4`) and standard strings (`SEV1`..`SEV4`, `CRITICAL`..`LOW`).
   - Implemented `from_yaml()` and `from_yaml_string()` using `yaml.safe_load()`.

2. **Flagship Scenario (`demo/scenarios/database-connection-leak.yaml`):**
   - Created the declarative specification for payment-service release `v2.8.1`.
   - Captured connection pool leak (50/50 active connections), 28.4% error rate spike, p95 latency 1850ms, and timeout logs.
   - Documented ground truth: expected root cause keywords (`connection pool`, `leak`, `exhaustion`, `v2.8.1`), expected tools (`get_error_rate`, `get_connection_pool`, `get_deployment_history`, `get_recent_commits`), remediation action (`rollback_deployment` to `v2.8.0`), and verification targets (`error_rate < 0.01`, `active_connections < 15.0`).

3. **Scenario Runner Engine (`apps/demo/scenario_runner.py`):**
   - Implemented `ScenarioRunner` with `load_scenario()`, `list_available_scenarios()`, `inject_failure()`, `create_incident_event()`, `execute_investigation()`, and `verify_execution()`.
   - Supports live HTTP injection into `payment-service` when reachable alongside in-memory synthetic event generation for standalone testing.

4. **Simulator Injection Endpoints (`apps/payment_service/main.py`):**
   - Added `/simulate/version`, `/simulate/leak`, and `/simulate/reset` endpoints.

5. **Unit Test Suite (`tests/unit/test_scenario_runner.py`):**
   - Created 4 unit tests covering YAML validation, scenario loading, failure injection lifecycle, and end-to-end investigation verification with LangGraph.
   - 4/4 tests passing in 2.80s.

---

## 2. Verification Evidence

```powershell
.venv\Scripts\pytest.exe tests/unit/test_scenario_runner.py -v
# 4 passed in 2.80s
```
