# Phase 5: Policy Engine, Human Approval & Controlled Remediation Verification - Research

**Researched:** 2026-10-13
**Domain:** Action Governance, Operation Risk Tiering, Human-in-the-Loop (HITL) Gates, Deployment MCP, n8n Workflow Automation, Closed-Loop Telemetry Verification
**Confidence:** HIGH

<user_constraints>
## User Constraints (from REQUIREMENTS.md, PROJECT.md & User Rules)

### Locked Decisions
- **Zero Plain Credentials in LLM Prompts or Tool Arguments**: Credentials, webhook tokens, and sensitive params must never leak into prompts or logs. Handled by environment variables and filtered by `Sanitizer`.
- **Strict Operation Risk Tiering (GOV-01)**:
  - Every action in the system must be classified into one of 5 distinct tiers:
    - `READ`: Non-mutating diagnostic inspections (`search_logs`, `get_connection_pool`, `get_commit`, `qdrant_search`, `get_current_version`) -> Always permitted without approval.
    - `LOW`: Idempotent, low-impact external notifications (e.g. `n8n` Slack alerts, Jira issue logging) -> Auto-permitted with audit log.
    - `MEDIUM`: Diagnostic service restart in non-production, configuration reload -> Permitted with warning.
    - `HIGH`: Production-impacting service mutations (`rollback_deployment`, production container restart, pool reconfiguration) -> **STRICT HITL APPROVAL MANDATED**. Action execution is strictly blocked until an operator explicitly approves the proposal.
    - `DESTRUCTIVE`: Permanent data mutation, schema alteration, table drops, S3/GCS bucket deletion -> **STRICTLY PROHIBITED BY POLICY** (cannot be executed under any circumstances).
- **Human-in-the-Loop (HITL) Approval Gate (GOV-02)**:
  - When the agent recommends a `HIGH`-risk remediation (e.g. `rollback_deployment` to `v2.8.0`), it creates a structured proposal in PostgreSQL `action_proposals` table with status `proposed`.
  - The remediation tool (`Deployment MCP`'s `rollback_deployment`) validates proposal status via the `PolicyEngine`. If status is not `approved` with a valid `approved_by` operator ID, execution is blocked with error `POLICY_VIOLATION` (`-32003`).
- **Post-Remediation Telemetry Verification Loop (GOV-03)**:
  - After a remediation action is executed, the incident must **NOT** be marked resolved immediately.
  - The verification loop polls telemetry (error rates from Logs MCP, connection pool metrics from Database MCP, and service `/health` probe).
  - Only when error rate drops below recovery threshold (<1%) and connection pool returns to nominal range (<15 active connections) is the proposal marked `verified` and the incident closed.
- **Immutable Audit Logging (GOV-04)**:
  - All policy evaluations, approval/rejection decisions, tool invocations, and post-action verification metrics must be durably recorded in audit logs with timestamps and operator IDs.
- **Controlled Deployment MCP Server (MCP-06)**:
  - Port `8006`, JSON-RPC 2.0. Exposes read tools (`get_current_version`, `get_previous_version`, `get_deployment_history`) and policy-gated action tools (`rollback_deployment`, `restart_service`).
  - Capable of executing rollback on simulated `payment-service` (reverting version from `v2.8.1` to `v2.8.0` and clearing pool leaks).
- **n8n Workflow Automation MCP Server (MCP-07)**:
  - Port `8007`, JSON-RPC 2.0. Exposes `execute_workflow` and `get_execution_status`.
  - Seamless offline mock fallback when n8n container is not running, ensuring zero test flakiness.
- **Test Separation**:
  - Unit tests run 100% offline in <5 seconds without requiring running Docker containers or external webhooks.
  - Integration tests marked `@pytest.mark.integration`.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Module | Secondary Tier | Rationale |
|------------|----------------|----------------|-----------|
| Risk Tiering & Policy Engine | `apps/policy/engine.py` | `apps/policy/models.py` | Formally evaluates proposed actions against risk tiers, enforces approval prerequisites, and blocks destructive actions |
| HITL Approval Subsystem | `apps/policy/approval.py` | `apps/mcp_incident/storage.py` | Manages proposal approval/rejection transitions, validates operator credentials, and emits `ai.actions` events |
| Governance Audit Logging | `apps/policy/audit.py` | `investigation_tool_history` table | Durably records policy evaluation decisions, approval events, and remediation execution logs |
| Deployment MCP Server | `apps/mcp_deployment/server.py` | `apps/payment_service/` | Inspects versions and executes controlled service rollbacks only when verified by PolicyEngine |
| n8n Workflow MCP Server | `apps/mcp_n8n/server.py` | `apps/mcp_n8n/tools.py` | Dispatches Slack/Jira/email notification workflows with automatic offline mock execution |
| Post-Remediation Verifier | `apps/verification/verifier.py` | Logs MCP & Database MCP | Polls telemetry after remediation to confirm error rate drop and pool recovery before closure |
| Automated Incident Closure | `apps/verification/closure.py` | `apps/mcp_incident/storage.py` | Transitions proposal to `verified`, closes incident record with winning hypothesis, and emits Kafka notifications |
</architectural_responsibility_map>

<standard_stack>
## Pinned Standard Stack (Phase 5 Additions & Schemas)

### Application Components
| Component | Module | Port | Transport |
|-----------|--------|------|-----------|
| Deployment MCP Server | `apps/mcp_deployment/main.py` | `8006` | JSON-RPC 2.0 (`POST /mcp`), stdio |
| n8n MCP Server | `apps/mcp_n8n/main.py` | `8007` | JSON-RPC 2.0 (`POST /mcp`), stdio |
| Policy & Verification Engine | `apps/policy/`, `apps/verification/` | Python library / async service | In-process & Kafka event integration |

### Action Risk Classification Matrix
| Risk Level | Permitted Operations | Approval Requirement | Examples |
|------------|----------------------|----------------------|----------|
| `READ` | Inspection & queries | Automatic (no approval) | `search_logs`, `get_connection_pool`, `get_commit`, `get_current_version`, `qdrant_search` |
| `LOW` | Idempotent notifications | Automatic (logged) | `n8n` Slack alerts, Jira ticket creation, metric annotations |
| `MEDIUM` | Non-production restarts | Permitted with audit | `restart_service` on staging or sandbox environments |
| `HIGH` | Production service mutation | **Strict Human Approval Required** | `rollback_deployment`, production container restart, pool size alterations |
| `DESTRUCTIVE` | Permanent data deletion | **Prohibited by Policy** | `DROP TABLE`, `DELETE FROM ...`, `DROP DATABASE`, `TRUNCATE` |

### Action Proposal Lifecycle States
$$\text{proposed} \xrightarrow[\text{operator reject}]{\text{operator approve}} \begin{cases} \text{rejected} \\ \text{approved} \xrightarrow{\text{execute rollback}} \text{executed} \xrightarrow[\text{failed}]{\text{verified}} \begin{cases} \text{failed} \\ \text{verified} \implies \text{incident closed} \end{cases} \end{cases}$$
</standard_stack>

<pitfalls_and_patterns>
## Common Pitfalls & Architectural Patterns

### Pitfalls to Avoid
1. **Unchecked Rollback Execution**: Allowing an autonomous LLM agent to execute rollbacks without verified human authorization creates severe availability risks in production.
   *Mitigation:* `Deployment MCP`'s `rollback_deployment` tool checks `PolicyEngine.validate_execution(proposal_id)` before touching the service. If the proposal is not `approved`, it immediately aborts with `POLICY_VIOLATION`.
2. **Premature Incident Closure**: Closing an incident immediately after issuing a rollback command without verifying that the service actually recovered.
   *Mitigation:* `RemediationVerifier` polls telemetry over multiple cycles, checking both log error rates (<1.0%) and database active connections (<15/50). Only when both metrics recover is the incident marked `resolved`.
3. **External n8n Dependency Breaking Offline Tests**: Requiring a live n8n workflow server causes local unit tests and developer setups to fail when n8n is offline.
   *Mitigation:* `n8n MCP` features an automatic mock workflow dispatcher that simulates successful Slack and Jira notifications with realistic webhook responses when n8n is unreachable.
4. **Audit Trail Gaps**: Performing actions without recording who approved them and what policy checks occurred.
   *Mitigation:* `GovernanceAuditLogger` logs every policy check, approval timestamp, operator ID, and post-action verification metric into PostgreSQL.
</pitfalls_and_patterns>

---
*Phase 5 Research completed: 2026-10-13*
