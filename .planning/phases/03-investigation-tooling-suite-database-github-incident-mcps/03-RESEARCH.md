# Phase 3: Investigation Tooling Suite (Database, GitHub & Incident MCPs) - Research

**Researched:** 2026-10-10
**Domain:** Model Context Protocol (MCP), Read-Only Database Diagnostics, Code Change Tracking, Short-Term Investigation State
**Confidence:** HIGH

<user_constraints>
## User Constraints (from REQUIREMENTS.md, PROJECT.md & User Rules)

### Locked Decisions
- **Zero Plain Credentials in Prompts/Tools**: Database credentials and GitHub tokens must never appear in LLM prompts, tool arguments, or logs. Handled via environment variables and sanitized by `Sanitizer`.
- **Strict Read-Only Enforcement on Database MCP (MCP-03)**:
  - Database MCP must connect to `demo_payment_db` to inspect connection pools, slow queries, and active queries.
  - It must strictly reject any SQL mutation (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `COPY`, etc.) or multiple/chained statements.
  - Queries must execute within read-only transactions (`SET TRANSACTION READ ONLY;`).
- **Offline & Reproducible GitHub MCP (MCP-04)**:
  - GitHub MCP must provide realistic commits, pull requests, diffs, changed files, and deployment tags for `payment-service` v2.8.0 and v2.8.1.
  - It must support a local reproducible provider (`LocalMockGitProvider`) for 100% offline development, test, and demo execution without requiring internet access or GitHub tokens.
  - Optional live `GitHubAPIProvider` support when `GITHUB_TOKEN` is configured.
- **Short-Term Transactional Investigation Memory (MEM-01)**:
  - Investigation state (evidence items, competing hypotheses, tool execution history, action proposals) must persist reliably in PostgreSQL (`aegisops_db`).
  - Must survive agent restarts and process crashes.
- **Incident Lifecycle State Machine (MCP-05)**:
  - Transactional incident management: `create_incident`, `update_incident`, `add_evidence`, `add_hypothesis`, `create_action_proposal`, `close_incident`.
  - Publishes `incidents.updated` and `ai.analysis` events to Kafka when incident state or hypotheses change.
- **Test Separation**: Fast offline unit tests (<5s) with mocked database and git providers.
- **Strict Scope Fencing**: Phase 3 delivers the 3 MCP servers and PostgreSQL short-term memory. LangGraph cyclic orchestrator, Qdrant semantic RAG, policy approval gates, and React UI belong to subsequent phases.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Module | Secondary Tier | Rationale |
|------------|----------------|----------------|-----------|
| Read-Only Database Introspection | `apps/mcp_database/` | `demo_payment_db` | Safely diagnoses connection pool exhaustion, locked tables, active connections, and slow queries |
| SQL Mutation Guard | `apps/mcp_database/validator.py` | Query Parser | Lexical and AST verification blocking all write operations before query submission |
| Code Change Tracking | `apps/mcp_github/` | `LocalMockGitProvider` | Inspects recent commits, PRs, and unified diffs (e.g. leaking v2.8.1 connection pool code) offline |
| Transactional Incident State | `apps/mcp_incident/` | `aegisops_db` | Manages evidence chain, hypotheses confidence, and action proposals |
| Short-Term Memory Subsystem | `apps/mcp_incident/storage.py` | PostgreSQL tables | Persists evidence, hypotheses, and tool call history with relational foreign keys |
</architectural_responsibility_map>

<standard_stack>
## Pinned Standard Stack (Phase 3 Additions & Schemas)

### Application Components
| Component | Module | Port | Transport |
|-----------|--------|------|-----------|
| Database MCP Server | `apps/mcp_database/main.py` | `8003` | JSON-RPC 2.0 (`POST /mcp`), stdio |
| GitHub MCP Server | `apps/mcp_github/main.py` | `8004` | JSON-RPC 2.0 (`POST /mcp`), stdio |
| Incident MCP Server | `apps/mcp_incident/main.py` | `8005` | JSON-RPC 2.0 (`POST /mcp`), stdio |

### PostgreSQL Tables (`aegisops_db` Short-Term Memory)
| Table | Primary Keys & Indexes | Purpose |
|-------|------------------------|---------|
| `incident_evidence` | `id UUID PK`, `(incident_id, created_at DESC)` | Normalized evidence records anchored to incidents |
| `incident_hypotheses` | `id UUID PK`, `(incident_id, status)` | Competing hypotheses with confidence scores (0.0-1.0) |
| `action_proposals` | `id UUID PK`, `(incident_id, status)` | Proposed remediations awaiting policy check and human approval |
| `investigation_tool_history` | `id UUID PK`, `(incident_id, created_at DESC)` | Audit log of all MCP tool executions during an investigation |
</standard_stack>

<pitfalls_and_patterns>
## Common Pitfalls & Architectural Patterns

### Pitfalls to Avoid
1. **Accidental Mutation Through Multi-Statement Queries**: An attacker or malformed prompt might send `SELECT 1; DROP TABLE payments;`.
   *Mitigation:* Lexical and statement-level parser ensuring exactly one statement exists, that the AST root is a `SELECT` statement, and executing with `SET TRANSACTION READ ONLY;`.
2. **Brittle External GitHub API in Demos**: Relying on live GitHub API tokens causes CI/demo failures due to rate limits or offline network environments.
   *Mitigation:* Author a comprehensive `LocalMockGitProvider` containing pre-built commits for `payment-service` v2.8.0 (baseline) and v2.8.1 (buggy commit with connection pool leak diff), while allowing `GITHUB_TOKEN` override.
3. **Hypothesis Overwriting**: Updating hypothesis confidence should preserve previous rationale and evidence links.
   *Mitigation:* Relational schema linking evidence IDs to hypotheses, and recording timestamped transitions.
4. **Unbounded Database Diagnostic Queries**: Querying `pg_stat_activity` or table dumps without limits can flood LLM contexts.
   *Mitigation:* Enforce row limits (default 20, max 100) and wrap results in `TokenBudgetGuard`.
</pitfalls_and_patterns>

---
*Phase 3 Research completed: 2026-10-10*
