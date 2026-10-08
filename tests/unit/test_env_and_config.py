import os
import tomllib
import pytest

def test_env_example_keys():
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env.example")
    assert os.path.exists(env_path), ".env.example must exist"
    
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    required_keys = [
        "AEGISOPS_ENV",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "AEGISOPS_DB_NAME",
        "DEMO_PAYMENT_DB_NAME",
        "KAFKA_BOOTSTRAP_SERVERS",
        "KAFKA_BOOTSTRAP_SERVERS_INTERNAL",
        "QDRANT_PORT",
        "PROMETHEUS_PORT",
        "GRAFANA_PORT",
        "N8N_PORT",
    ]
    for key in required_keys:
        assert f"{key}=" in content, f"Key {key} missing from .env.example"

def test_pyproject_toml():
    pyproject_path = os.path.join(os.path.dirname(__file__), "..", "..", "pyproject.toml")
    assert os.path.exists(pyproject_path), "pyproject.toml must exist"
    
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    
    assert data["project"]["name"] == "aegisops-ai"
    deps = data["project"]["dependencies"]
    assert any("fastapi" in d for d in deps)
    assert any("pydantic" in d for d in deps)
    assert any("aiokafka" in d for d in deps)
    assert any("asyncpg" in d for d in deps)

def test_gitattributes_enforces_lf():
    gitattr_path = os.path.join(os.path.dirname(__file__), "..", "..", ".gitattributes")
    assert os.path.exists(gitattr_path), ".gitattributes must exist"
    
    with open(gitattr_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "*.sh text eol=lf" in content, ".gitattributes must enforce LF on shell scripts"
