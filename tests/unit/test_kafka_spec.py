import os
import pytest
import sys

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.init_kafka import TOPIC_CONFIGS, get_topic_names

def test_eight_operational_topics_defined():
    topic_names = get_topic_names()
    assert len(topic_names) == 8, f"Expected 8 operational topics, got {len(topic_names)}"

def test_exact_topic_names():
    expected_topics = {
        "logs.raw",
        "metrics.raw",
        "alerts.raw",
        "deployments.events",
        "incidents.created",
        "incidents.updated",
        "ai.analysis",
        "ai.actions",
    }
    actual_topics = set(get_topic_names())
    assert actual_topics == expected_topics, f"Mismatch in topic names: {actual_topics.symmetric_difference(expected_topics)}"

def test_topic_partitions_and_retention():
    for topic in TOPIC_CONFIGS:
        assert topic["partitions"] >= 1, f"Topic {topic['name']} must have at least 1 partition"
        assert topic["replication_factor"] == 1, f"Local dev cluster must use replication factor 1"
        assert "retention.ms" in topic["config"], f"Topic {topic['name']} must define retention.ms"
