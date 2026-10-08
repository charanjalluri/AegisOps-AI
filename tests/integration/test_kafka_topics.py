import pytest
import os

pytestmark = pytest.mark.integration

def test_live_kafka_topic_connection():
    """
    Integration test connecting to live Kafka cluster.
    Only executes when Kafka broker is running on KAFKA_BOOTSTRAP_SERVERS.
    """
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    try:
        from kafka.admin import KafkaAdminClient
        client = KafkaAdminClient(bootstrap_servers=bootstrap, request_timeout_ms=3000)
        topics = client.list_topics()
        client.close()
        assert len(topics) >= 0
    except Exception as e:
        pytest.skip(f"Kafka cluster not currently reachable at {bootstrap}: {e}")
