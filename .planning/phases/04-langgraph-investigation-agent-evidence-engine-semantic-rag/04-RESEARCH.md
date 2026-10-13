# Phase 4: LangGraph Investigation Agent, Evidence Engine & Semantic RAG - Research

**Researched:** 2026-10-13
**Domain:** LangGraph Orchestration, Evidence Engine Normalization, Multi-Hypothesis Calibrated Scoring, Qdrant Vector Semantic Memory, Historical RAG
**Confidence:** HIGH

<user_constraints>
## User Constraints (from REQUIREMENTS.md, PROJECT.md & User Rules)

### Locked Decisions
- **Zero Plain Credentials in Prompts & Tool Arguments**: API keys, database credentials, and auth tokens must never leak into LLM prompts, tool arguments, or logs. All payloads pass through `Sanitizer`.
- **Strict Read-Only Investigation Boundary**: The agent may only query read-only diagnostic tools (Logs MCP, Database MCP, GitHub MCP, and Qdrant memory). Remediation execution belongs to Phase 5.
- **Dual Memory Architecture**:
  - Short-Term Memory: PostgreSQL `aegisops_db` tables (`incident_evidence`, `incident_hypotheses`, `action_proposals`, `investigation_tool_history`) managed via `InvestigationStorage` (Phase 3).
  - Long-Term Semantic Memory (MEM-02, MEM-03): Qdrant vector database on port 6333 storing historical incidents, postmortems, and operational runbooks.
- **Strict Investigation Budget Limits (REASON-04)**:
  - Maximum tool calls: Capped at 20 (configurable, default 20).
  - Wall-clock timeout: Capped at 5 minutes (300 seconds).
  - Expensive operations: Max 5 expensive queries (deep log scans, large diff analyses).
  - When budget is exhausted, the agent must not crash or loop infinitely; it must gracefully terminate the cycle and synthesize an RCA report based on best available evidence.
- **Canonical Evidence Normalization (REASON-01)**:
  - Heterogeneous outputs from Logs MCP, Database MCP, GitHub MCP, and Qdrant must be normalized into strongly typed `CanonicalEvidence` records.
  - Each record must include `source_tool`, `signal_type`, `confidence_weight` (0.0 to 1.0), provenance timestamps, and factual interpretation.
- **Multi-Hypothesis Calibrated Scoring (REASON-03)**:
  - Generates multiple competing hypotheses (e.g. Connection pool exhaustion vs Traffic spike vs Database hardware degradation).
  - Explicitly separates **Facts** (verified observations), **Hypotheses** (testable explanations), **Assumptions** (unverified premises), and **Alternative Explanations**.
  - Calibrated confidence scoring: requires corroboration from at least 2 independent MCP tools to exceed 85% confidence score; confidence distribution across competing hypotheses is normalized.
- **Structured Root Cause Analysis Synthesis (REASON-05)**:
  - Synthesizes auditable RCA report with winning hypothesis, confidence score, timeline, key evidence chain, and recommended action proposal.
  - Publishes `ai.analysis` event to Kafka topic and updates PostgreSQL incident state.
- **Test Separation & Fast Offline Execution**:
  - Unit tests must run 100% offline in <5 seconds without requiring live Qdrant, live Kafka, or live LLM API keys.
  - Provide in-memory mock Qdrant provider and mock deterministic LLM reasoning provider.
  - Integration tests marked with `@pytest.mark.integration`.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Module | Secondary Tier | Rationale |
|------------|----------------|----------------|-----------|
| Qdrant Semantic Memory Client | `apps/agent/memory/qdrant.py` | Qdrant REST API (`:6333`) | Connects to Qdrant via async `httpx`, handles collection setup, embedding generation, payload filtering, and in-memory mock fallback |
| Historical Knowledge Seeder | `scripts/seed_qdrant.py` | `Makefile` (`make seed`) | Idempotently populates Qdrant with 25–40 realistic incidents, runbooks, and failure patterns |
| Evidence Engine Normalizer | `apps/agent/evidence/normalizer.py` | `apps/agent/evidence/models.py` | Ingests heterogeneous MCP responses and outputs strongly typed `CanonicalEvidence` with signal weights |
| Multi-Hypothesis Scoring | `apps/agent/reasoning/hypotheses.py` | `apps/mcp_incident/storage.py` | Formulates competing hypotheses, updates Bayesian/calibrated confidence scores, enforces multi-source corroboration |
| Investigation Budget Guard | `apps/agent/orchestration/budget.py` | Timer & Counter primitives | Enforces max 20 tool calls, 300s timeout, max 5 expensive ops, and budget exhaustion signaling |
| LangGraph Cyclic Orchestrator | `apps/agent/orchestration/graph.py` | `apps/agent/orchestration/state.py` | Orchestrates cyclic investigation workflow: Understand -> Plan -> Select Tool -> Execute -> Evaluate -> Check Convergence -> Synthesize RCA |
| RCA Synthesizer & Kafka Publisher | `apps/agent/reasoning/rca.py` | Kafka `ai.analysis` topic | Compiles structured RCA document, creates action proposal, and notifies Kafka subscribers |
</architectural_responsibility_map>

<standard_stack>
## Pinned Standard Stack (Phase 4 Additions & Schemas)

### Application Components
| Component | Module | Port / Interface | Transport |
|-----------|--------|------------------|-----------|
| Investigation Agent Core | `apps/agent/main.py` | Python entrypoint / Kafka consumer | Async event loop / Kafka `incidents.created` |
| Qdrant Vector Client | `apps/agent/memory/qdrant.py` | `6333` | HTTP REST API / `httpx` async |
| Operational Seeder | `scripts/seed_qdrant.py` | CLI script | `httpx` / mock fallback |

### Qdrant Vector Collection Schema
| Collection Name | Dimension | Distance Metric | Payloads |
|-----------------|-----------|-----------------|----------|
| `aegisops_knowledge` | 384 (all-MiniLM / fast deterministic) | Cosine | `id`, `document_type` (`incident`, `postmortem`, `runbook`), `service`, `title`, `root_cause`, `symptoms`, `resolution`, `tags`, `text` |

### Canonical Evidence Schema (`CanonicalEvidence`)
| Field | Type | Description |
|-------|------|-------------|
| `evidence_id` | `str` (UUID) | Unique identifier |
| `incident_id` | `str` | Associated incident identifier |
| `source_tool` | `str` | Originating tool (e.g. `mcp_logs`, `mcp_database`, `mcp_github`, `semantic_memory`) |
| `signal_type` | `str` | Classification (`error_spike`, `pool_exhaustion`, `code_diff_leak`, `historical_match`, etc.) |
| `confidence_weight` | `float` (0.0 - 1.0) | Weight / reliability of signal |
| `fact_statement` | `str` | Concise factual observation |
| `raw_data` | `Dict[str, Any]` | Sanitized raw diagnostic output |
| `timestamp` | `datetime` | Provenance observation timestamp |
| `is_contradicting` | `bool` | Whether signal refutes current primary hypothesis |

### Root Cause Analysis Report Schema (`RCAReport`)
| Field | Type | Description |
|-------|------|-------------|
| `incident_id` | `str` | Associated incident identifier |
| `service` | `str` | Target service (e.g. `payment-service`) |
| `primary_root_cause` | `str` | Pinpointed cause (e.g. "Database connection leak in v2.8.1 PR #42") |
| `confidence_score` | `float` | Calibrated confidence (0.0 - 1.0) |
| `executive_summary` | `str` | Human-readable executive summary |
| `timeline` | `List[str]` | Event chronology |
| `key_evidence` | `List[CanonicalEvidence]` | Critical evidence items supporting conclusion |
| `evaluated_hypotheses` | `List[HypothesisItem]` | Competing hypotheses and final evaluated scores |
| `recommended_remediation`| `Dict[str, Any]` | Proposed action (`rollback_deployment`, risk `HIGH`) |
| `action_proposal_id` | `Optional[str]` | Linked action proposal in `action_proposals` table |
| `preventative_actions` | `List[str]` | Long-term architectural safeguards |
</standard_stack>

<pitfalls_and_patterns>
## Common Pitfalls & Architectural Patterns

### Pitfalls to Avoid
1. **Unbounded Agent Loops & Cost Inflation**: Autonomous LLM agents can get trapped in repetitive query cycles.
   *Mitigation:* Strict `InvestigationBudget` tracking tool counts (<= 20), wall-clock elapsed time (<= 300s), and repeated query hashes; forces RCA synthesis when limits are approached.
2. **Overconfidence from Single Signals**: An error log mentioning "database timeout" might jump to a faulty conclusion if database connection pool metrics or git diffs are not inspected.
   *Mitigation:* Calibrated hypothesis scoring algorithm capping single-source confidence at 0.70; requires independent corroboration across >= 2 tools to exceed 0.85 confidence.
3. **External Embeddings Dependency Breaking Offline Testing**: Requiring remote OpenAI or Hugging Face embedding endpoints causes CI and local offline runs to fail without internet/keys.
   *Mitigation:* Built-in deterministic lightweight embedding engine (`DeterministicEmbedder`) producing fixed-dimension Cosine-compatible vectors for tests, paired with extensible OpenAI/HuggingFace adapters when API keys exist.
4. **Qdrant Connection Latency / Flakiness During Unit Tests**: Unit tests failing if Docker Compose is down.
   *Mitigation:* `QdrantMemoryClient` features an automatic in-memory mock vector store when `offline_mode=True` or when Qdrant is unreachable, mirroring the successful pattern from Phase 3's `InvestigationStorage`.
5. **Loss of Provenance Context**: Presenting conclusions without traceability makes human operators distrust AI actions.
   *Mitigation:* Every finding in `RCAReport` links directly to specific `CanonicalEvidence` records and tool invocation IDs.
</pitfalls_and_patterns>

---
*Phase 4 Research completed: 2026-10-13*
