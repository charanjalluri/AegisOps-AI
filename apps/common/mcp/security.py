"""
AegisOps AI - Shared MCP Security & Sanitization
Redacts credentials, tokens, secrets, and connection strings from tool inputs, outputs, and audit logs.
"""

import re
from typing import Any, Dict, List, Set, Union


class Sanitizer:
    SENSITIVE_KEYS: Set[str] = {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "authorization",
        "auth_header",
        "private_key",
        "db_password",
        "client_secret",
        "connection_string",
    }

    # Regex patterns for sensitive values embedded in strings
    BEARER_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE)
    BASIC_AUTH_PATTERN = re.compile(r"(Basic\s+)[A-Za-z0-9+/=]{8,}", re.IGNORECASE)
    URI_CREDENTIAL_PATTERN = re.compile(r"(://[^:]+:)([^@]+)(@)", re.IGNORECASE)
    API_KEY_PATTERN = re.compile(r"((?:key|token|secret|password)\s*[:=]\s*['\"]?)[A-Za-z0-9_\-]{16,}['\"]?", re.IGNORECASE)

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """Recursively redact sensitive fields and substrings."""
        if isinstance(data, dict):
            sanitized_dict: Dict[str, Any] = {}
            for k, v in data.items():
                lower_k = str(k).lower()
                if any(sensitive in lower_k for sensitive in cls.SENSITIVE_KEYS):
                    sanitized_dict[k] = "[REDACTED]"
                else:
                    sanitized_dict[k] = cls.sanitize(v)
            return sanitized_dict

        elif isinstance(data, list):
            return [cls.sanitize(item) for item in data]

        elif isinstance(data, str):
            sanitized_str = cls.URI_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]\3", data)
            sanitized_str = cls.BEARER_PATTERN.sub(r"\1[REDACTED]", sanitized_str)
            sanitized_str = cls.BASIC_AUTH_PATTERN.sub(r"\1[REDACTED]", sanitized_str)
            sanitized_str = cls.API_KEY_PATTERN.sub(r"\1[REDACTED]", sanitized_str)
            return sanitized_str

        return data

    mask_secrets = sanitize
