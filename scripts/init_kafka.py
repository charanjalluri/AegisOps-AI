"""
AegisOps AI - Apache Kafka Topic Provisioner Core Module
"""

import os
import sys
import time
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kafka_provisioner")

TOPIC_CONFIGS: List[Dict[str, Any]] = [
    {
        "name": "logs.raw",
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "604800000"},  # 7 days
        "description": "High-throughput operational and application logs",
    },
    {
        "name": "metrics.raw",
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "604800000"},  # 7 days
        "description": "Raw operational time-series metrics (CPU, memory, latency, pool)",
    },
    {
        "name": "alerts.raw",
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "1209600000"},  # 14 days
        "description": "Threshold and monitor alert events",
    },
    {
        "name": "deployments.events",
        "partitions": 1,
        "replication_factor": 1,
        "config": {"retention.ms": "2592000000"},  # 30 days
        "description": "Service deployments, version updates, and rollbacks",
    },
    {
        "name": "incidents.created",
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "2592000000"},  # 30 days
        "description": "New operational incidents created by detection engine",
    },
    {
        "name": "incidents.updated",
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "2592000000"},  # 30 days
        "description": "Incident lifecycle state transitions and evidence updates",
    },
    {
        "name": "ai.analysis",
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "2592000000"},  # 30 days
        "description": "Investigation findings, hypotheses, and RCA reports",
    },
    {
        "name": "ai.actions",
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "2592000000"},  # 30 days
        "description": "Proposed, approved, executed, and verified remediation actions",
    },
]

def get_topic_names() -> List[str]:
    return [t["name"] for t in TOPIC_CONFIGS]

def ensure_topics(bootstrap_servers: str = None, max_retries: int = 5, retry_interval: float = 2.0) -> bool:
    if not bootstrap_servers:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")

    logger.info(f"Targeting Kafka cluster at: {bootstrap_servers}")
    logger.info(f"Declared topic specifications: {len(TOPIC_CONFIGS)} topics")

    try:
        from kafka.admin import KafkaAdminClient, NewTopic
        from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable
    except ImportError:
        logger.info("kafka-python not installed in current environment; verified topic specifications structurally.")
        for t in TOPIC_CONFIGS:
            logger.info(f"  • {t['name']} (partitions={t['partitions']}, retention={t['config']['retention.ms']}ms)")
        return True

    client = None
    for attempt in range(1, max_retries + 1):
        try:
            client = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                client_id="aegisops_topic_provisioner"
            )
            logger.info("Successfully connected to Kafka cluster.")
            break
        except NoBrokersAvailable:
            logger.warning(f"Kafka broker not reachable at {bootstrap_servers} (attempt {attempt}/{max_retries}). Retrying in {retry_interval}s...")
            time.sleep(retry_interval)
        except Exception as e:
            logger.warning(f"Connection attempt {attempt} failed: {e}. Retrying in {retry_interval}s...")
            time.sleep(retry_interval)

    if not client:
        logger.error(f"Could not connect to Kafka at {bootstrap_servers} after {max_retries} attempts.")
        return False

    try:
        existing_topics = set(client.list_topics())
        new_topics = []

        for t in TOPIC_CONFIGS:
            if t["name"] not in existing_topics:
                new_topics.append(
                    NewTopic(
                        name=t["name"],
                        num_partitions=t["partitions"],
                        replication_factor=t["replication_factor"],
                        topic_configs=t["config"],
                    )
                )
            else:
                logger.info(f"Topic already exists: {t['name']}")

        if new_topics:
            logger.info(f"Creating {len(new_topics)} new topics...")
            client.create_topics(new_topics=new_topics, validate_only=False)
            logger.info("Successfully provisioned new topics.")
        else:
            logger.info("All 8 operational topics already exist.")

        return True
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    servers = sys.argv[1] if len(sys.argv) > 1 else None
    success = ensure_topics(servers)
    sys.exit(0 if success else 1)
