import os
import pytest

def test_postgres_init_script_lf_line_endings():
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "infrastructure", "postgres", "init-databases.sh"
    )
    assert os.path.exists(script_path), "init-databases.sh must exist"
    
    with open(script_path, "rb") as f:
        content = f.read()
    
    assert b"\r" not in content, "init-databases.sh must have LF line endings only (no CRLF/\\r)"
    assert content.startswith(b"#!/bin/sh"), "init-databases.sh must have a valid #!/bin/sh shebang"

def test_postgres_init_script_creates_both_databases():
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "infrastructure", "postgres", "init-databases.sh"
    )
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    assert "aegisops_db" in text, "Script must create aegisops_db"
    assert "demo_payment_db" in text, "Script must create demo_payment_db"
    assert "uuid-ossp" in text, "Script must enable uuid-ossp extension"
