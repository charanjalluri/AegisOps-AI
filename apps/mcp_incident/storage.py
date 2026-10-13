"""
AegisOps AI - Short-Term Investigation Storage (MEM-01)
Persists incidents, normalized evidence chains, competing hypotheses,
action proposals, and MCP tool call history to PostgreSQL aegisops_db
with in-memory transactional fallback for offline execution.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4
import asyncpg

from apps.mcp_incident.models import (
    ActionProposalItem,
    EvidenceItem,
    HypothesisItem,
    IncidentDetail,
    ToolHistoryItem,
)

INVESTIGATION_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "infrastructure"
    / "postgres"
    / "investigation_schema.sql"
)


class InvestigationStorage:
    """
    Manages durable short-term investigation memory.
    Supports live PostgreSQL pooling or in-memory mock storage.
    """

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        self.pool = pool
        # In-memory mock store
        self._incidents: Dict[str, Dict[str, Any]] = {}
        self._evidence: Dict[str, List[EvidenceItem]] = {}
        self._hypotheses: Dict[str, Dict[str, HypothesisItem]] = {}
        self._proposals: Dict[str, List[ActionProposalItem]] = {}
        self._tool_history: Dict[str, List[ToolHistoryItem]] = {}

    async def init_schema(self) -> bool:
        """Applies investigation_schema.sql to PostgreSQL if connected."""
        if not self.pool:
            return True
        if not INVESTIGATION_SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema not found at {INVESTIGATION_SCHEMA_PATH}")

        sql = INVESTIGATION_SCHEMA_PATH.read_text(encoding="utf-8")
        async with self.pool.acquire() as conn:
            await conn.execute(sql)
        return True

    # 1. Incident CRUD
    async def create_incident(
        self,
        incident_id: str,
        title: str,
        service: str,
        severity: str = "SEV-2",
        summary: Optional[str] = None,
    ) -> IncidentDetail:
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.pool:
            self._incidents[incident_id] = {
                "incident_id": incident_id,
                "title": title,
                "service": service,
                "severity": severity,
                "status": "detected",
                "summary": summary,
                "created_at": now_iso,
                "updated_at": now_iso,
                "resolved_at": None,
            }
            return IncidentDetail(**self._incidents[incident_id])

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO incidents (incident_id, title, service, severity, status, summary, created_at, updated_at)
                VALUES ($1, $2, $3, $4, 'detected', $5, NOW(), NOW())
                ON CONFLICT (incident_id) DO UPDATE
                SET title = EXCLUDED.title, severity = EXCLUDED.severity, summary = EXCLUDED.summary, updated_at = NOW()
                RETURNING incident_id, title, service, severity, status, summary,
                          created_at::text, updated_at::text, resolved_at::text;
                """,
                incident_id,
                title,
                service,
                severity,
                summary,
            )
            return IncidentDetail(**dict(row))

    async def get_incident(self, incident_id: str) -> Optional[IncidentDetail]:
        if not self.pool:
            data = self._incidents.get(incident_id)
            return IncidentDetail(**data) if data else None

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT incident_id, title, service, severity, status, summary,
                       created_at::text, updated_at::text, resolved_at::text
                FROM incidents WHERE incident_id = $1;
                """,
                incident_id,
            )
            return IncidentDetail(**dict(row)) if row else None

    async def update_incident(
        self,
        incident_id: str,
        status: Optional[str] = None,
        summary: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> Optional[IncidentDetail]:
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.pool:
            inc = self._incidents.get(incident_id)
            if not inc:
                return None
            if status:
                inc["status"] = status
            if summary:
                inc["summary"] = summary
            if severity:
                inc["severity"] = severity
            inc["updated_at"] = now_iso
            return IncidentDetail(**inc)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE incidents
                SET status = COALESCE($2, status),
                    summary = COALESCE($3, summary),
                    severity = COALESCE($4, severity),
                    updated_at = NOW()
                WHERE incident_id = $1
                RETURNING incident_id, title, service, severity, status, summary,
                          created_at::text, updated_at::text, resolved_at::text;
                """,
                incident_id,
                status,
                summary,
                severity,
            )
            return IncidentDetail(**dict(row)) if row else None

    async def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> List[IncidentDetail]:
        """Lists incidents with optional status and severity filtering."""
        limit = min(max(1, limit), 100)
        if not self.pool:
            results = []
            for inc in self._incidents.values():
                if status and inc.get("status") != status:
                    continue
                if severity and inc.get("severity") != severity:
                    continue
                results.append(IncidentDetail(**inc))
            # Sort descending by created_at
            results.sort(key=lambda x: x.created_at, reverse=True)
            return results[:limit]

        query = """
            SELECT incident_id, title, service, severity, status, summary,
                   created_at::text, updated_at::text, resolved_at::text
            FROM incidents
            WHERE ($1::text IS NULL OR status = $1)
              AND ($2::text IS NULL OR severity = $2)
            ORDER BY created_at DESC
            LIMIT $3;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, status, severity, limit)
            return [IncidentDetail(**dict(r)) for r in rows]

    # 2. Evidence
    async def add_evidence(
        self,
        incident_id: str,
        source_tool: str,
        signal_type: str,
        confidence_weight: float,
        raw_data: Dict[str, Any],
        interpretation: str,
    ) -> EvidenceItem:
        item = EvidenceItem(
            id=str(uuid4()),
            incident_id=incident_id,
            source_tool=source_tool,
            signal_type=signal_type,
            confidence_weight=confidence_weight,
            raw_data=raw_data,
            interpretation=interpretation,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        if not self.pool:
            self._evidence.setdefault(incident_id, []).append(item)
            return item

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO incident_evidence (
                    id, incident_id, source_tool, signal_type,
                    confidence_weight, raw_data, interpretation, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, NOW());
                """,
                uuid4(),
                incident_id,
                source_tool,
                signal_type,
                confidence_weight,
                json.dumps(raw_data, default=str),
                interpretation,
            )
            return item

    async def get_evidence(self, incident_id: str) -> List[EvidenceItem]:
        if not self.pool:
            return self._evidence.get(incident_id, [])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id::text, incident_id, source_tool, signal_type,
                       confidence_weight, raw_data, interpretation, created_at::text
                FROM incident_evidence
                WHERE incident_id = $1
                ORDER BY created_at ASC;
                """,
                incident_id,
            )
            return [
                EvidenceItem(
                    id=r["id"],
                    incident_id=r["incident_id"],
                    source_tool=r["source_tool"],
                    signal_type=r["signal_type"],
                    confidence_weight=r["confidence_weight"],
                    raw_data=json.loads(r["raw_data"]) if isinstance(r["raw_data"], str) else r["raw_data"],
                    interpretation=r["interpretation"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # 3. Hypotheses
    async def add_or_update_hypothesis(
        self,
        incident_id: str,
        title: str,
        confidence_score: float = 0.5,
        supporting_evidence: Optional[List[str]] = None,
        refuting_evidence: Optional[List[str]] = None,
        rationale: Optional[str] = None,
        hypothesis_id: Optional[str] = None,
        status: str = "active",
    ) -> HypothesisItem:
        hypo_id = hypothesis_id or str(uuid4())
        supp = supporting_evidence or []
        refut = refuting_evidence or []
        now_iso = datetime.now(timezone.utc).isoformat()

        item = HypothesisItem(
            id=hypo_id,
            incident_id=incident_id,
            title=title,
            status=status,
            confidence_score=confidence_score,
            supporting_evidence=supp,
            refuting_evidence=refut,
            rationale=rationale,
            updated_at=now_iso,
        )

        if not self.pool:
            self._hypotheses.setdefault(incident_id, {})[hypo_id] = item
            return item

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO incident_hypotheses (
                    id, incident_id, title, status, confidence_score,
                    supporting_evidence, refuting_evidence, rationale, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, NOW())
                ON CONFLICT (id) DO UPDATE
                SET title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    confidence_score = EXCLUDED.confidence_score,
                    supporting_evidence = EXCLUDED.supporting_evidence,
                    refuting_evidence = EXCLUDED.refuting_evidence,
                    rationale = EXCLUDED.rationale,
                    updated_at = NOW();
                """,
                uuid4(),
                incident_id,
                title,
                status,
                confidence_score,
                json.dumps(supp),
                json.dumps(refut),
                rationale,
            )
            return item

    async def get_hypotheses(self, incident_id: str) -> List[HypothesisItem]:
        if not self.pool:
            return list(self._hypotheses.get(incident_id, {}).values())

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id::text, incident_id, title, status, confidence_score,
                       supporting_evidence, refuting_evidence, rationale, updated_at::text
                FROM incident_hypotheses
                WHERE incident_id = $1
                ORDER BY confidence_score DESC;
                """,
                incident_id,
            )
            return [
                HypothesisItem(
                    id=r["id"],
                    incident_id=r["incident_id"],
                    title=r["title"],
                    status=r["status"],
                    confidence_score=r["confidence_score"],
                    supporting_evidence=json.loads(r["supporting_evidence"]) if isinstance(r["supporting_evidence"], str) else r["supporting_evidence"],
                    refuting_evidence=json.loads(r["refuting_evidence"]) if isinstance(r["refuting_evidence"], str) else r["refuting_evidence"],
                    rationale=r["rationale"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    # 4. Action Proposals
    async def create_action_proposal(
        self,
        incident_id: str,
        action_type: str,
        parameters: Dict[str, Any],
        risk_level: str = "HIGH",
        rationale: Optional[str] = None,
        proposal_id: Optional[str] = None,
    ) -> ActionProposalItem:
        item = ActionProposalItem(
            id=proposal_id or str(uuid4()),
            incident_id=incident_id,
            action_type=action_type,
            parameters=parameters,
            risk_level=risk_level,
            status="proposed",
            rationale=rationale,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        if not self.pool:
            self._proposals.setdefault(incident_id, []).append(item)
            return item

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO action_proposals (
                    id, incident_id, action_type, parameters,
                    risk_level, status, rationale, created_at
                ) VALUES ($1, $2, $3, $4::jsonb, $5, 'proposed', $6, NOW());
                """,
                uuid4(),
                incident_id,
                action_type,
                json.dumps(parameters, default=str),
                risk_level,
                rationale,
            )
            return item

    async def get_action_proposals(self, incident_id: str) -> List[ActionProposalItem]:
        if not self.pool:
            return self._proposals.get(incident_id, [])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id::text, incident_id, action_type, parameters,
                       risk_level, status, rationale, created_at::text,
                       approved_by, executed_at::text
                FROM action_proposals
                WHERE incident_id = $1
                ORDER BY created_at ASC;
                """,
                incident_id,
            )
            return [
                ActionProposalItem(
                    id=r["id"],
                    incident_id=r["incident_id"],
                    action_type=r["action_type"],
                    parameters=json.loads(r["parameters"]) if isinstance(r["parameters"], str) else r["parameters"],
                    risk_level=r["risk_level"],
                    status=r["status"],
                    rationale=r["rationale"],
                    created_at=r["created_at"],
                    approved_by=r["approved_by"],
                    executed_at=r["executed_at"],
                )
                for r in rows
            ]

    # 5. Tool Call History
    async def record_tool_history(
        self,
        incident_id: str,
        tool_name: str,
        caller: str,
        arguments: Dict[str, Any],
        duration_ms: float,
        status: str,
        result_summary: Optional[str] = None,
    ) -> ToolHistoryItem:
        item = ToolHistoryItem(
            id=str(uuid4()),
            incident_id=incident_id,
            tool_name=tool_name,
            caller=caller,
            arguments=arguments,
            duration_ms=duration_ms,
            status=status,
            result_summary=result_summary,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        if not self.pool:
            self._tool_history.setdefault(incident_id, []).append(item)
            return item

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO investigation_tool_history (
                    id, incident_id, tool_name, caller,
                    arguments, duration_ms, status, result_summary, created_at
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, NOW());
                """,
                uuid4(),
                incident_id,
                tool_name,
                caller,
                json.dumps(arguments, default=str),
                duration_ms,
                status,
                result_summary,
            )
            return item

    async def get_tool_history(self, incident_id: str) -> List[ToolHistoryItem]:
        if not self.pool:
            return self._tool_history.get(incident_id, [])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id::text, incident_id, tool_name, caller,
                       arguments, duration_ms, status, result_summary, created_at::text
                FROM investigation_tool_history
                WHERE incident_id = $1
                ORDER BY created_at ASC;
                """,
                incident_id,
            )
            return [
                ToolHistoryItem(
                    id=r["id"],
                    incident_id=r["incident_id"],
                    tool_name=r["tool_name"],
                    caller=r["caller"],
                    arguments=json.loads(r["arguments"]) if isinstance(r["arguments"], str) else r["arguments"],
                    duration_ms=r["duration_ms"],
                    status=r["status"],
                    result_summary=r["result_summary"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # 6. Close Incident
    async def close_incident(
        self,
        incident_id: str,
        root_cause: str,
        winning_hypothesis_id: Optional[str] = None,
        summary: str = "Incident resolved and verified",
    ) -> IncidentDetail:
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.pool:
            inc = self._incidents.get(incident_id)
            if not inc:
                raise ValueError(f"Incident '{incident_id}' does not exist")
            inc["status"] = "resolved"
            inc["summary"] = f"Root cause: {root_cause}. {summary}"
            inc["updated_at"] = now_iso
            inc["resolved_at"] = now_iso
            # If winning hypothesis provided, validate it
            if winning_hypothesis_id and incident_id in self._hypotheses:
                hypo = self._hypotheses[incident_id].get(winning_hypothesis_id)
                if hypo:
                    hypo.status = "validated"
                    hypo.confidence_score = 1.0
            return IncidentDetail(**inc)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if winning_hypothesis_id:
                    await conn.execute(
                        """
                        UPDATE incident_hypotheses
                        SET status = 'validated', confidence_score = 1.0, updated_at = NOW()
                        WHERE id = $1;
                        """,
                        uuid4() if isinstance(winning_hypothesis_id, str) and len(winning_hypothesis_id) != 36 else winning_hypothesis_id,
                    )

                row = await conn.fetchrow(
                    """
                    UPDATE incidents
                    SET status = 'resolved',
                        summary = $2,
                        resolved_at = NOW(),
                        updated_at = NOW()
                    WHERE incident_id = $1
                    RETURNING incident_id, title, service, severity, status, summary,
                              created_at::text, updated_at::text, resolved_at::text;
                    """,
                    incident_id,
                    f"Root cause: {root_cause}. {summary}",
                )
                if not row:
                    raise ValueError(f"Incident '{incident_id}' does not exist")
                return IncidentDetail(**dict(row))

    # 7. Tool Execution History
    async def record_tool_call(
        self,
        incident_id: str,
        tool_name: str,
        duration_ms: float,
        parameters: Optional[Dict[str, Any]] = None,
        caller: str = "agent",
        status: str = "success",
        result_summary: Optional[str] = None,
    ) -> ToolHistoryItem:
        """Records an MCP tool execution record."""
        now_iso = datetime.now(timezone.utc).isoformat()
        item = ToolHistoryItem(
            id=str(uuid4()),
            incident_id=incident_id,
            tool_name=tool_name,
            caller=caller,
            arguments=parameters or {},
            duration_ms=duration_ms,
            status=status,
            result_summary=result_summary,
            created_at=now_iso,
        )
        if not self.pool:
            if incident_id not in self._tool_history:
                self._tool_history[incident_id] = []
            self._tool_history[incident_id].append(item)
            return item

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tool_execution_history (id, incident_id, tool_name, caller, arguments, duration_ms, status, result_summary, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW());
                """,
                item.id,
                item.incident_id,
                item.tool_name,
                item.caller,
                json.dumps(item.arguments),
                item.duration_ms,
                item.status,
                item.result_summary,
            )
            return item

    async def get_tool_history(self, incident_id: str) -> List[ToolHistoryItem]:
        """Returns chronological list of tool executions for an incident."""
        if not self.pool:
            return self._tool_history.get(incident_id, [])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id::text, incident_id, tool_name, caller, arguments, duration_ms, status, result_summary, created_at::text
                FROM tool_execution_history
                WHERE incident_id = $1
                ORDER BY created_at ASC;
                """,
                incident_id,
            )
            items = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("arguments"), str):
                    d["arguments"] = json.loads(d["arguments"])
                items.append(ToolHistoryItem(**d))
            return items
