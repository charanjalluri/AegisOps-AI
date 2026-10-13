# Phase 4: Plan 04-03 Summary - LangGraph Investigation Agent, Budgeting & RCA Synthesis

**Execution Date:** 2026-10-13
**Status:** Completed
**Requirements Fulfilled:** REASON-02, REASON-04, REASON-05

## Accomplishments

1. **Investigation Budget Controller (`apps/agent/orchestration/budget.py`)**:
   - Built `InvestigationBudget` strictly capping autonomous agent activity:
     - Max tool calls: capped at 20 (configurable).
     - Wall-clock timeout: capped at 300.0 seconds (5 minutes).
     - Expensive operations: capped at 5 operations.
   - Raises `RuntimeError` and triggers graceful transition to RCA synthesis upon exhaustion.

2. **Reasoning Provider Interfaces (`apps/agent/reasoning/llm.py`)**:
   - `BaseReasoningProvider` contract defining `plan_investigation`, `select_next_tool`, and RCA synthesis.
   - `DeterministicRuleReasoningProvider` implementing 100% offline, deterministic incident triage:
     - Evaluates log error rate -> inspects database connection pool -> analyzes git commit diff -> retrieves Qdrant semantic matches.
     - Extensible `LLMReasoningProvider` interface for live OpenAI / LangChain / Muse Spark execution.

3. **LangGraph Cyclic Investigation State Machine (`apps/agent/orchestration/graph.py`, `apps/agent/orchestration/state.py`)**:
   - Implemented `InvestigationGraph` state machine using LangGraph `StateGraph(InvestigationState)`:
     - START -> understand_incident -> retrieve_knowledge -> plan_information -> execute_step -> (conditional route) -> synthesize_rca -> END.
     - Built-in tolerance for flaky/failing tools without crashing the investigation.
     - Multi-source operational corroboration requirement ensuring >= 2 active MCP tools before converging.
     - Conditional edge router dynamically branching between iterative planning and RCA synthesis.

4. **Root Cause Analysis (RCA) Synthesizer (`apps/agent/reasoning/rca.py`)**:
   - Authored `RCASynthesizer` and `RCAReport` compiling primary root cause, confidence score, executive summary, chronological timeline, key evidence chain, and preventative actions.
   - Automatically generates safe `action_proposals` in PostgreSQL short-term memory (risk level `HIGH`, status `proposed`).
   - Updates incident status to `mitigating` and broadcasts `ai.analysis` event to Kafka.

5. **Agent Service Main Runner (`apps/agent/main.py`)**:
   - Standalone CLI runner with `--test-run` flag and Kafka consumer loop.

## Test Results

- `tests/unit/test_investigation_budget.py`: 4/4 passed.
- `tests/unit/test_investigation_state_machine.py`: 5/5 passed.
- `tests/unit/test_rca_synthesis.py`: 2/2 passed.
- Total Plan 04-03 Tests: **11 passed in 1.45s** (100% green offline).

