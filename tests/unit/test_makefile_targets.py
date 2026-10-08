import os
import pytest

def test_makefile_exists_and_contains_targets():
    makefile_path = os.path.join(os.path.dirname(__file__), "..", "..", "Makefile")
    assert os.path.exists(makefile_path), "Makefile must exist"

    with open(makefile_path, "r", encoding="utf-8") as f:
        content = f.read()

    expected_targets = [
        "setup:",
        "up:",
        "down:",
        "clean:",
        "logs:",
        "test-unit:",
        "test-integration:",
        "reset-demo:",
    ]
    for target in expected_targets:
        assert target in content, f"Target {target} missing from Makefile"

def test_makefile_clean_removes_volumes():
    makefile_path = os.path.join(os.path.dirname(__file__), "..", "..", "Makefile")
    with open(makefile_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify clean target has -v flag to remove volumes
    clean_section = [line for line in content.split("\n") if "down -v" in line]
    assert len(clean_section) > 0, "Makefile clean target must use 'docker compose down -v' to clean volumes"
