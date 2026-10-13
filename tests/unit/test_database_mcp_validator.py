"""
Unit tests for SQLMutationValidator in Database MCP.
Verifies strictly read-only SELECT queries and rejection of mutations, DDL, comments, and chaining.
"""

import pytest
from apps.mcp_database.validator import SQLMutationValidator


def test_validator_allows_valid_select_queries():
    valid_queries = [
        "SELECT id, amount, status FROM payments WHERE status = 'failed' LIMIT 10",
        "SELECT p.id, p.amount, c.name FROM payments p JOIN customers c ON p.customer_id = c.id WHERE p.amount > 100",
        "SELECT count(*), status FROM payments GROUP BY status HAVING count(*) > 5",
        "SELECT * FROM pg_stat_activity WHERE state = 'active'",
        "SELECT (SELECT max(amount) FROM payments) AS max_amt",
    ]
    for q in valid_queries:
        result = SQLMutationValidator.validate_sql(q)
        assert result.startswith("SELECT")


def test_validator_strips_single_trailing_semicolon():
    query = "SELECT * FROM payments WHERE id = 'pay_123';"
    result = SQLMutationValidator.validate_sql(query)
    assert not result.endswith(";")
    assert result == "SELECT * FROM payments WHERE id = 'pay_123'"


def test_validator_allows_valid_cte_select():
    cte_query = """
    WITH failed_tx AS (
        SELECT id, amount FROM payments WHERE status = 'failed'
    )
    SELECT id, amount FROM failed_tx ORDER BY amount DESC LIMIT 5
    """
    result = SQLMutationValidator.validate_sql(cte_query)
    assert result.startswith("WITH")
    assert "SELECT" in result


def test_validator_allows_explain_select():
    explain_query = "EXPLAIN SELECT * FROM payments WHERE status = 'failed'"
    result = SQLMutationValidator.validate_sql(explain_query)
    assert result.startswith("EXPLAIN")


def test_validator_rejects_empty_or_whitespace():
    with pytest.raises(ValueError, match="cannot be empty"):
        SQLMutationValidator.validate_sql("")
    with pytest.raises(ValueError, match="cannot be empty"):
        SQLMutationValidator.validate_sql("   \n\t  ")


def test_validator_rejects_comments():
    comment_queries = [
        "SELECT * FROM payments -- where status = 'ok'",
        "SELECT * /* bypass scanner */ FROM payments",
        "/* comment */ SELECT 1",
    ]
    for q in comment_queries:
        with pytest.raises(ValueError, match="SQL comments"):
            SQLMutationValidator.validate_sql(q)


def test_validator_rejects_semicolon_chaining():
    chained = [
        "SELECT 1; DROP TABLE payments;",
        "SELECT * FROM payments; SELECT * FROM accounts",
        "SELECT 1; DELETE FROM payments WHERE id = 1;",
    ]
    for q in chained:
        with pytest.raises(ValueError, match="Multi-statement queries"):
            SQLMutationValidator.validate_sql(q)


@pytest.mark.parametrize(
    "mutating_query, forbidden_token",
    [
        ("INSERT INTO payments (id, amount) VALUES ('p1', 10)", "INSERT"),
        ("UPDATE payments SET status = 'refunded' WHERE id = 'p1'", "UPDATE"),
        ("DELETE FROM payments WHERE status = 'failed'", "DELETE"),
        ("DROP TABLE payments", "DROP"),
        ("ALTER TABLE payments ADD COLUMN test_col int", "ALTER"),
        ("TRUNCATE TABLE payments", "TRUNCATE"),
        ("CREATE TABLE test_table (id int)", "CREATE"),
        ("GRANT SELECT ON payments TO public", "GRANT"),
        ("REVOKE SELECT ON payments FROM public", "REVOKE"),
        ("COPY payments TO '/tmp/dump.csv'", "COPY"),
        ("CALL execute_refund('p1')", "CALL"),
        ("EXECUTE run_something", "EXECUTE"),
        ("SELECT * INTO backup_payments FROM payments", "INTO"),
        ("LOCK TABLE payments IN ACCESS EXCLUSIVE MODE", "LOCK"),
        ("VACUUM FULL payments", "VACUUM"),
        ("SET statement_timeout = 0", "SET"),
        ("RESET statement_timeout", "RESET"),
        ("BEGIN TRANSACTION", "BEGIN"),
    ],
)
def test_validator_rejects_mutation_keywords(mutating_query, forbidden_token):
    with pytest.raises(ValueError, match=forbidden_token):
        SQLMutationValidator.validate_sql(mutating_query)


def test_validator_rejects_cte_with_mutation():
    bad_cte = """
    WITH deleted_rows AS (
        DELETE FROM payments WHERE status = 'failed' RETURNING *
    )
    SELECT * FROM deleted_rows
    """
    with pytest.raises(ValueError, match="DELETE"):
        SQLMutationValidator.validate_sql(bad_cte)


def test_validator_rejects_explain_analyze():
    bad_explain = "EXPLAIN ANALYZE SELECT * FROM payments"
    with pytest.raises(ValueError, match="EXPLAIN ANALYZE is prohibited"):
        SQLMutationValidator.validate_sql(bad_explain)
