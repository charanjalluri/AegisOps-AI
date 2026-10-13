"""
AegisOps AI - Environment Configuration Loader
Safely loads environment variables from .env if present without overwriting existing variables.
Never prints or logs secret values.
"""

import os
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[Path] = None) -> bool:
    """
    Loads key-value pairs from .env into os.environ.
    Preserves existing environment variables. Never logs or prints values.
    """
    path = env_path or (Path(__file__).resolve().parent.parent.parent / ".env")
    if not path.exists():
        return False

    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            key = k.strip()
            val = v.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val
        return True
    except Exception:
        return False
