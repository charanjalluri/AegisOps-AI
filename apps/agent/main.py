"""
AegisOps AI - Autonomous Investigation Agent Service (REASON-02, REASON-04, REASON-05)
Consumes incidents.created events from Kafka, orchestrates LangGraph investigations,
and publishes synthesized Root Cause Analysis reports to ai.analysis.
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Optional

# Ensure project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.agent.orchestration.graph import InvestigationGraph
from apps.common.schemas.events import IncidentEvent, IncidentSeverity, IncidentStatus


async def run_agent_service(kafka_bootstrap: Optional[str] = None):
    """Kafka event loop consumer."""
    print(f"[Agent] Starting AegisOps Investigation Agent...")
    bootstrap = kafka_bootstrap or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")

    try:
        from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

        consumer = AIOKafkaConsumer(
            "incidents.created",
            bootstrap_servers=bootstrap,
            group_id="aegisops-investigation-agent",
            auto_offset_reset="latest",
        )
        producer = AIOKafkaProducer(bootstrap_servers=bootstrap)

        await consumer.start()
        await producer.start()
        print(f"[Agent] Connected to Kafka at {bootstrap}. Listening on 'incidents.created'...")

        async def emit_event(topic: str, payload: dict):
            await producer.send_and_wait(topic, json.dumps(payload, default=str).encode("utf-8"))

        graph = InvestigationGraph(event_emitter=emit_event)

        try:
            async for msg in consumer:
                data = json.loads(msg.value.decode("utf-8"))
                incident = IncidentEvent(**data)
                print(f"[Agent] Received incident: {incident.incident_id} ({incident.title})")

                final_state = await graph.run(incident)
                print(f"[Agent] Investigation complete for {incident.incident_id}. Status: {final_state.status}")
                if final_state.rca_report:
                    rca = final_state.rca_report
                    print(f"        Primary Root Cause: {rca.get('primary_root_cause')}")
                    print(f"        Calibrated Confidence: {rca.get('confidence_score'):.1%}")

        finally:
            await consumer.stop()
            await producer.stop()

    except Exception as e:
        print(f"[Agent] Kafka connection failed ({e}). Fallback to offline mode.")


def main():
    parser = argparse.ArgumentParser(description="AegisOps Investigation Agent")
    parser.add_argument("--test-run", action="store_true", help="Execute single mock incident investigation")
    parser.add_argument("--kafka", default=None, help="Kafka bootstrap server")
    args = parser.parse_args()

    if args.test_run:
        sample_incident = IncidentEvent(
            incident_id="INC-DEMO-001",
            title="Database Connection Pool Saturation on Payment Service",
            service="payment-service",
            severity=IncidentSeverity.SEV1,
            status=IncidentStatus.INVESTIGATING,
            summary="Payment service error rate spiked to 28.4% with PostgreSQL connection timeouts.",
        )
        graph = InvestigationGraph()
        state = asyncio.run(graph.run(sample_incident))
        print(f"Investigation Status: {state.status}")
        if state.rca_report:
            print(f"Primary Root Cause: {state.rca_report['primary_root_cause']}")
            print(f"Confidence: {state.rca_report['confidence_score']:.1%}")
    else:
        asyncio.run(run_agent_service(args.kafka))


if __name__ == "__main__":
    main()
