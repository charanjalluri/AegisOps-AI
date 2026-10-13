"""
AegisOps AI - SQL Mutation Validator
Enforces strictly read-only single-statement SELECT queries for Database MCP tools.
Rejects mutations, DDL, comment tricks, semicolon chaining, and administrative statements.
"""

import re
from typing import Set

# Keywords that are strictly prohibited anywhere in an ad-hoc query
PROHIBITED_KEYWORDS: Set[str] = {
    # DML mutations
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "UPSERT",
    "REPLACE",
    # DDL
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "RENAME",
    # Permissions and roles
    "GRANT",
    "REVOKE",
    # Procedural and execution
    "CALL",
    "EXECUTE",
    "DO",
    "FUNCTION",
    "PROCEDURE",
    # Data export / creation
    "COPY",
    "INTO",  # Prevents SELECT ... INTO new_table
    "OUTFILE",
    "DUMP",
    # Administrative & maintenance
    "LOCK",
    "DISCARD",
    "VACUUM",
    "REINDEX",
    "CLUSTER",
    # Session state modification
    "SET",
    "RESET",
    # Transaction control (managed by application layer)
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "START",
    "SAVEPOINT",
}


class SQLMutationValidator:
    """
    Validates SQL query strings to ensure they are strictly read-only, single-statement,
    and safe from query injection / mutation attempts.
    """

    @classmethod
    def validate_sql(cls, query: str) -> str:
        """
        Validates and sanitizes a query.

        Args:
            query: Raw SQL query string.

        Returns:
            Cleaned SQL query without trailing semicolon.

        Raises:
            ValueError: If query violates read-only or single-statement constraints.
        """
        if not query or not query.strip():
            raise ValueError("SQL query cannot be empty")

        trimmed = query.strip()

        # 1. Prohibit SQL comments (-- or /* */) to prevent token masking/obfuscation
        if "--" in trimmed or "/*" in trimmed or "*/" in trimmed:
            raise ValueError(
                "SQL comments ('--', '/*') are prohibited to prevent query obfuscation"
            )

        # 2. Check for semicolon chaining (multiple statements)
        # Allow an optional single trailing semicolon
        normalized = trimmed
        if normalized.endswith(";"):
            normalized = normalized[:-1].rstrip()

        if ";" in normalized:
            raise ValueError(
                "Multi-statement queries (semicolon chaining) are prohibited"
            )

        # 3. Check statement starter (must start with SELECT, WITH, or EXPLAIN)
        starter_match = re.match(r"^\s*([a-zA-Z]+)", normalized)
        if not starter_match:
            raise ValueError("Invalid SQL syntax: missing command starter")

        starter = starter_match.group(1).upper()
        if starter not in {"SELECT", "WITH", "EXPLAIN"}:
            raise ValueError(
                f"Prohibited SQL command '{starter}'. Only SELECT, WITH (CTE), or EXPLAIN queries are permitted"
            )

        # If starts with WITH, must contain SELECT
        if starter == "WITH":
            if not re.search(r"\bSELECT\b", normalized, re.IGNORECASE):
                raise ValueError("WITH CTE statements must culminate in a SELECT query")

        # If starts with EXPLAIN, ensure it targets a SELECT query and does not contain ANALYZE
        if starter == "EXPLAIN":
            if re.search(r"\bANALYZE\b", normalized, re.IGNORECASE):
                raise ValueError(
                    "EXPLAIN ANALYZE is prohibited because it executes statements that may have side effects"
                )
            if not re.search(r"\bSELECT\b", normalized, re.IGNORECASE):
                raise ValueError("EXPLAIN statements must target a SELECT query")

        # 4. Prohibit mutation/DDL/administrative keywords anywhere in statement
        for keyword in sorted(PROHIBITED_KEYWORDS):
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, normalized, re.IGNORECASE):
                raise ValueError(
                    f"Prohibited SQL keyword '{keyword}' detected. Mutation and administrative statements are strictly forbidden"
                )

        return normalized
