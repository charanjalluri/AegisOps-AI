import os
import yaml
import pytest

@pytest.fixture
def compose_config():
    compose_path = os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose.yml")
    assert os.path.exists(compose_path), "docker-compose.yml must exist"
    with open(compose_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_compose_structure(compose_config):
    assert "services" in compose_config
    assert "volumes" in compose_config
    assert "networks" in compose_config

def test_pinned_image_versions(compose_config):
    services = compose_config["services"]
    required_services = [
        ("postgres", "postgres:16.4-alpine"),
        ("kafka", "apache/kafka:3.7.0"),
        ("kafka-ui", "provectuslabs/kafka-ui:v0.7.2"),
        ("qdrant", "qdrant/qdrant:v1.9.0"),
        ("prometheus", "prom/prometheus:v2.51.0"),
        ("grafana", "grafana/grafana:10.4.0"),
        ("n8n", "n8nio/n8n:1.36.0"),
    ]

    for service_name, expected_image in required_services:
        assert service_name in services, f"Service {service_name} missing from docker-compose.yml"
        actual_image = services[service_name]["image"]
        assert actual_image == expected_image, f"Service {service_name} image mismatch: expected {expected_image}, got {actual_image}"
        assert ":latest" not in actual_image, f"Service {service_name} must NOT use ':latest' tag"

def test_kafka_dual_listeners(compose_config):
    kafka_env = compose_config["services"]["kafka"]["environment"]
    advertised_listeners = kafka_env.get("KAFKA_ADVERTISED_LISTENERS", "")
    assert "PLAINTEXT://kafka:9092" in advertised_listeners, "Kafka must advertise PLAINTEXT://kafka:9092 for internal Docker networking"
    assert "EXTERNAL://localhost:29092" in advertised_listeners, "Kafka must advertise EXTERNAL://localhost:29092 for host machine access"

def test_postgres_init_mount(compose_config):
    volumes = compose_config["services"]["postgres"]["volumes"]
    mount_exists = any("init-databases.sh:/docker-entrypoint-initdb.d/init-databases.sh" in v for v in volumes)
    assert mount_exists, "postgres service must mount init-databases.sh into /docker-entrypoint-initdb.d/"
