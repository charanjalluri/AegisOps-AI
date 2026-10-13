"""
AegisOps AI - LangGraph Investigation State Machine Orchestrator (REASON-02)
Executes cyclic incident investigations powered by LangGraph StateGraph:
START -> understand_incident -> retrieve_knowledge -> plan_information -> execute_step -> (conditional route) -> synthesize_rca -> END
"""

import time
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from langgraph.graph import StateGraph, START, END

from apps.agent.evidence.models import CanonicalEvidence
from apps.agent.evidence.normalizer import EvidenceNormalizer
from apps.agent.memory.qdrant import QdrantMemoryClient
from apps.agent.orchestration.budget import InvestigationBudget
from apps.agent.orchestration.state import InvestigationState
from apps.agent.reasoning.hypotheses import EvaluatedHypothesis, HypothesisEngine
from apps.agent.reasoning.llm import BaseReasoningProvider, DeterministicRuleReasoningProvider
from apps.agent.reasoning.rca import RCAReport, RCASynthesizer
from apps.common.schemas.events import IncidentEvent
from apps.mcp_incident.storage import InvestigationStorage


class InvestigationGraph:
    """
    LangGraph-powered state machine orchestrating autonomous incident investigations.
    """

    def __init__(
        self,
        reasoning_provider: Optional[BaseReasoningProvider] = None,
        qdrant_client: Optional[QdrantMemoryClient] = None,
        storage: Optional[InvestigationStorage] = None,
        budget: Optional[InvestigationBudget] = None,
        tool_executor: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        event_emitter: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ):
        self.reasoning = reasoning_provider or DeterministicRuleReasoningProvider()
        self.storage = storage or InvestigationStorage()
        self.budget = budget or InvestigationBudget()
        self.tool_executor = tool_executor or self._default_mock_tool_executor
        self.event_emitter = event_emitter

        if qdrant_client:
            self.qdrant = qdrant_client
        else:
            self.qdrant = QdrantMemoryClient(offline_mode=True)
            # Pre-seed mock store with operational knowledge
            from scripts.seed_qdrant import HISTORICAL_DOCUMENTS
            mock_store = self.qdrant._get_mock_store("aegisops_knowledge")
            for doc in HISTORICAL_DOCUMENTS:
                vec = self.qdrant.embedder.embed_text(doc.full_text())
                mock_store[doc.id] = {"vector": vec, "doc": doc}

        # Build and compile the LangGraph workflow
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

    def _build_graph(self) -> StateGraph:
        """Constructs the LangGraph StateGraph topology."""
        builder = StateGraph(InvestigationState)
        builder.add_node("understand_incident", self._node_understand_incident)
        builder.add_node("retrieve_knowledge", self._node_retrieve_knowledge)
        builder.add_node("plan_information", self._node_plan_information)
        builder.add_node("execute_step", self._node_execute_step)
        builder.add_node("synthesize_rca", self._node_synthesize_rca)

        builder.add_edge(START, "understand_incident")
        builder.add_edge("understand_incident", "retrieve_knowledge")
        builder.add_edge("retrieve_knowledge", "plan_information")
        builder.add_edge("plan_information", "execute_step")
        builder.add_conditional_edges(
            "execute_step",
            self._route_step,
            {
                "synthesize_rca": "synthesize_rca",
                "plan_information": "plan_information",
            },
        )
        builder.add_edge("synthesize_rca", END)
        return builder

    @property
    def compiled_graph(self):
        """Exposes the underlying compiled LangGraph runnable."""
        return self.app

    @staticmethod
    async def _default_mock_tool_executor(tool_name: str, params: Dict[str, Any]) -> Any:
        """High-fidelity mock responses for offline unit tests and demos."""
        if tool_name == "get_error_rate":
            return {
                "service": params.get("service", "payment-service"),
                "error_rate": 0.284,
                "total_logs": 850,
                "error_logs": 241,
                "threshold_exceeded": True,
                "time_window_minutes": 15,
            }
        elif tool_name == "get_connection_pool":
            return {
                "total_connections": 50,
                "active_connections": 50,
                "idle_connections": 0,
                "waiting_clients": 118,
                "max_connections": 50,
                "utilization_percent": 100.0,
                "status": "exhausted",
            }
        elif tool_name == "get_commit":
            return {
                "commit_hash": params.get("commit_hash", "8f9b2d1"),
                "author": "dev@aegisops.internal",
                "message": "fix(checkout): add connection checkout for payment retry queue",
                "diff": """
@@ -45,6 +45,8 @@ def process_payment(req):
+    conn = pool.acquire()
+    # note: omission of conn.close() / release
+    return execute_query(conn, req)
+                """,
            }
        elif tool_name == "get_slow_queries":
            return {
                "slow_queries": [
                    {"query": "SELECT * FROM payments WHERE tx_id = $1", "duration_ms": 5200.0, "wait_event": "ClientRead"}
                ]
            }
        elif tool_name == "search_logs":
            return {
                "logs": [
                    {"level": "ERROR", "message": "FATAL: remaining connection slots reserved for superuser", "service": "payment-service"},
                    {"level": "ERROR", "message": "Connection acquisition timeout after 5000ms", "service": "payment-service"},
                ]
            }
        return {"status": "ok", "message": f"Mock executed {tool_name}"}

    async def run(self, incident: IncidentEvent) -> InvestigationState:
        """Executes full LangGraph investigation cycle until convergence or budget exhaustion."""
        custom_hypos = incident.metadata.get("candidate_hypotheses") if incident.metadata else None
        engine = HypothesisEngine(incident_id=incident.incident_id, custom_hypotheses=custom_hypos)
        initial_state = InvestigationState(
            incident=incident,
            status="START",
            step_count=0,
            hypotheses=engine.get_hypotheses(),
            winning_hypothesis=engine.get_winning_hypothesis(),
        )

        final_data = await self.app.ainvoke(initial_state, config={"recursion_limit": 60})
        if isinstance(final_data, InvestigationState):
            return final_data
        return InvestigationState(**final_data)

    async def _node_understand_incident(
        self, state: InvestigationState
    ) -> Dict[str, Any]:
        """LangGraph node: Extract incident context and initialize hypotheses."""
        engine = HypothesisEngine(incident_id=state.incident.incident_id)
        return {
            "status": "UNDERSTOOD",
            "hypotheses": engine.get_hypotheses(),
            "winning_hypothesis": engine.get_winning_hypothesis(),
        }

    async def _node_retrieve_knowledge(
        self, state: InvestigationState
    ) -> Dict[str, Any]:
        """LangGraph node: Query Qdrant semantic memory for relevant operational postmortems."""
        query_text = f"{state.incident.service} {state.incident.title}"
        t0 = time.time()
        new_tool_history = list(state.tool_history)
        new_evidence = list(state.evidence)

        try:
            results = await self.qdrant.search(
                query=query_text,
                service=state.incident.service,
                limit=2,
            )
            dur_ms = (time.time() - t0) * 1000

            self.budget.record_tool_call("qdrant_search")
            call_entry = {
                "tool_name": "qdrant_search",
                "arguments": {"query": query_text},
                "duration_ms": round(dur_ms, 2),
                "status": "success",
            }
            new_tool_history.append(call_entry)
            await self.storage.record_tool_history(
                incident_id=state.incident.incident_id,
                tool_name="qdrant_search",
                caller="investigation_graph",
                arguments={"query": query_text},
                duration_ms=dur_ms,
                status="success",
            )

            # Normalize evidence
            qdrant_ev = EvidenceNormalizer.normalize_semantic_results(
                incident_id=state.incident.incident_id,
                results=results,
            )
            for ev in qdrant_ev:
                new_evidence.append(ev)
                await self.storage.add_evidence(
                    incident_id=state.incident.incident_id,
                    source_tool=ev.source_tool,
                    signal_type=ev.signal_type,
                    confidence_weight=ev.confidence_weight,
                    raw_data=ev.raw_data,
                    interpretation=ev.fact_statement,
                )

        except Exception as e:
            new_tool_history.append({
                "tool_name": "qdrant_search",
                "duration_ms": 0.0,
                "status": "error",
                "error": str(e),
            })

        # Re-evaluate hypotheses with current evidence
        engine = HypothesisEngine(incident_id=state.incident.incident_id)
        for ev in new_evidence:
            engine.add_evidence(ev)

        return {
            "status": "KNOWLEDGE_RETRIEVED",
            "tool_history": new_tool_history,
            "evidence": new_evidence,
            "hypotheses": engine.get_hypotheses(),
            "winning_hypothesis": engine.get_winning_hypothesis(),
        }

    async def _node_plan_information(
        self, state: InvestigationState
    ) -> Dict[str, Any]:
        """LangGraph node: Formulate questions for missing diagnostic facts."""
        missing = self.reasoning.plan_investigation(
            incident=state.incident,
            hypotheses=state.hypotheses,
            evidence_history=state.evidence,
        )
        return {"missing_information": missing}

    async def _node_execute_step(
        self, state: InvestigationState
    ) -> Dict[str, Any]:
        """LangGraph node: Select, execute next tool, normalize evidence, and update confidence."""
        step = state.step_count + 1
        new_tool_history = list(state.tool_history)
        new_evidence = list(state.evidence)

        if self.budget.is_exhausted():
            return {"status": "BUDGET_EXHAUSTED", "step_count": step}

        next_action = self.reasoning.select_next_tool(
            incident=state.incident,
            missing_info=state.missing_information,
            hypotheses=state.hypotheses,
            tool_history=state.tool_history,
        )

        if not next_action:
            return {"status": "CONVERGED", "step_count": step}

        tool_name, tool_params = next_action
        is_expensive = tool_name in ("search_logs", "get_commit")
        t0 = time.time()

        try:
            self.budget.record_tool_call(tool_name, is_expensive=is_expensive)
            raw_res = self.tool_executor(tool_name, tool_params)
            if hasattr(raw_res, "__await__"):
                raw_res = await raw_res

            dur_ms = (time.time() - t0) * 1000

            new_tool_history.append({
                "tool_name": tool_name,
                "arguments": tool_params,
                "duration_ms": round(dur_ms, 2),
                "status": "success",
            })
            await self.storage.record_tool_history(
                incident_id=state.incident.incident_id,
                tool_name=tool_name,
                caller="investigation_graph",
                arguments=tool_params,
                duration_ms=dur_ms,
                status="success",
            )

            # Normalize evidence
            new_ev_items = EvidenceNormalizer.normalize(
                incident_id=state.incident.incident_id,
                tool_name=tool_name,
                result=raw_res,
                provenance={"tool": tool_name, "params": tool_params},
            )
            for ev in new_ev_items:
                new_evidence.append(ev)
                await self.storage.add_evidence(
                    incident_id=state.incident.incident_id,
                    source_tool=ev.source_tool,
                    signal_type=ev.signal_type,
                    confidence_weight=ev.confidence_weight,
                    raw_data=ev.raw_data,
                    interpretation=ev.fact_statement,
                )

        except Exception as e:
            new_tool_history.append({
                "tool_name": tool_name,
                "arguments": tool_params,
                "duration_ms": 0.0,
                "status": "error",
                "error": str(e),
            })

        # Re-evaluate hypotheses with all accumulated evidence
        custom_hypos = state.incident.metadata.get("candidate_hypotheses") if state.incident.metadata else None
        engine = HypothesisEngine(incident_id=state.incident.incident_id, custom_hypotheses=custom_hypos)
        for ev in new_evidence:
            engine.add_evidence(ev)

        top = engine.get_winning_hypothesis()
        status = "INVESTIGATING"

        expected_tools = state.incident.metadata.get("expected_tools") if state.incident.metadata else None
        called_names = [call.get("tool_name") for call in new_tool_history]

        if self.budget.is_exhausted():
            status = "BUDGET_EXHAUSTED"
        elif expected_tools and all(t in called_names for t in expected_tools) and step >= len(expected_tools):
            status = "CONVERGED"
        elif top:
            active_mcp_tools = {t for t in top.source_tools_used if t.startswith("mcp_")}
            if top.confidence_score >= 0.85 and len(active_mcp_tools) >= 2 and step >= 3:
                status = "CONVERGED"

        return {
            "step_count": step,
            "status": status,
            "tool_history": new_tool_history,
            "evidence": new_evidence,
            "hypotheses": engine.get_hypotheses(),
            "winning_hypothesis": top,
        }

    def _route_step(self, state: InvestigationState) -> str:
        """LangGraph conditional edge router: Converge to RCA or cycle back to planning."""
        if state.status in ("CONVERGED", "BUDGET_EXHAUSTED") or self.budget.is_exhausted():
            return "synthesize_rca"
        return "plan_information"

    async def _node_synthesize_rca(
        self, state: InvestigationState
    ) -> Dict[str, Any]:
        """LangGraph node: Synthesize structured RCA report and emit events."""
        rca = RCASynthesizer.synthesize(
            incident=state.incident,
            winning_hypothesis=state.winning_hypothesis,
            hypotheses=state.hypotheses,
            evidence_history=state.evidence,
            tool_history=state.tool_history,
        )

        persisted_rca = await RCASynthesizer.persist_and_publish(
            rca=rca,
            storage=self.storage,
            event_emitter=self.event_emitter,
        )

        return {
            "rca_report": persisted_rca.model_dump(),
            "status": "COMPLETE",
        }
