"""
AegisOps AI - Logs MCP Tool Query Implementations
Read-only queries against raw_logs in aegisops_db with token budgeting and parameterized filtering.
"""

from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict, List, Optional
import asyncpg

from apps.common.mcp.budget import TokenBudgetGuard
from apps.mcp_logs.models import (
    CorrelatedErrorsResult,
    ErrorRateBucket,
    ErrorRateResult,
    GetCorrelatedErrorsInput,
    GetErrorRateInput,
    GetLogsAroundEventInput,
    GetServiceLogsInput,
    LogRecord,
    LogsAroundEventResult,
    LogsQueryResult,
    SearchLogsInput,
)

LEVEL_ORDER = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}


def row_to_log_record(row: Any) -> LogRecord:
    if isinstance(row, dict):
        d = row
    elif hasattr(row, "items"):
        d = dict(row)
    else:
        # Tuple or record from asyncpg
        meta = row[7] if len(row) > 7 else {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        return LogRecord(
            id=str(row[0]),
            timestamp=row[1],
            service=row[2],
            level=row[3],
            message=row[4],
            environment=row[5] if len(row) > 5 else "development",
            trace_id=row[6] if len(row) > 6 else None,
            metadata=meta,
        )

    meta = d.get("metadata", {})
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}

    return LogRecord(
        id=str(d.get("id", "")),
        timestamp=d.get("timestamp"),
        service=d.get("service", ""),
        level=d.get("level", "INFO"),
        message=d.get("message", ""),
        environment=d.get("environment", "development"),
        trace_id=d.get("trace_id"),
        metadata=meta,
    )


class LogsTools:
    """
    Executes strictly read-only diagnostics on raw_logs with TokenBudgetGuard pagination.
    """

    def __init__(self, pool: Optional[asyncpg.Pool] = None, in_memory_logs: Optional[List[Dict[str, Any]]] = None):
        self.pool = pool
        self._in_memory_logs: List[Dict[str, Any]] = in_memory_logs or []

    async def search_logs(self, input_data: SearchLogsInput) -> LogsQueryResult:
        records: List[LogRecord] = []

        if self.pool:
            query = "SELECT id, timestamp, service, level, message, environment, trace_id, metadata FROM raw_logs WHERE 1=1"
            params: List[Any] = []
            idx = 1

            if input_data.service:
                query += f" AND service = ${idx}"
                params.append(input_data.service)
                idx += 1

            if input_data.level:
                query += f" AND level = ${idx}"
                params.append(input_data.level)
                idx += 1

            if input_data.pattern:
                query += f" AND message ILIKE ${idx}"
                params.append(f"%{input_data.pattern}%")
                idx += 1

            if input_data.start_time:
                query += f" AND timestamp >= ${idx}"
                params.append(input_data.start_time)
                idx += 1

            if input_data.end_time:
                query += f" AND timestamp <= ${idx}"
                params.append(input_data.end_time)
                idx += 1

            query += f" ORDER BY timestamp DESC LIMIT ${idx}"
            params.append(input_data.limit * 2)  # Over-fetch slightly for budget pagination

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                records = [row_to_log_record(r) for r in rows]
        else:
            # In-memory filter for offline testing
            filtered = self._in_memory_logs[:]
            if input_data.service:
                filtered = [l for l in filtered if l.get("service") == input_data.service]
            if input_data.level:
                filtered = [l for l in filtered if l.get("level") == input_data.level]
            if input_data.pattern:
                filtered = [l for l in filtered if input_data.pattern.lower() in l.get("message", "").lower()]
            if input_data.start_time:
                filtered = [l for l in filtered if l.get("timestamp") >= input_data.start_time]
            if input_data.end_time:
                filtered = [l for l in filtered if l.get("timestamp") <= input_data.end_time]

            filtered.sort(key=lambda x: x.get("timestamp"), reverse=True)
            records = [row_to_log_record(r) for r in filtered]

        # Apply TokenBudgetGuard pagination
        page = TokenBudgetGuard.paginate_records(
            items=records,
            cursor=input_data.cursor,
            limit=input_data.limit,
            max_tokens=TokenBudgetGuard.DEFAULT_MAX_TOKENS,
        )

        return LogsQueryResult(
            logs=page["items"],
            count=page["count"],
            next_cursor=page["next_cursor"],
            truncated_by_budget=page["truncated_by_budget"],
            estimated_tokens=page["estimated_tokens"],
        )

    async def get_service_logs(self, input_data: GetServiceLogsInput) -> LogsQueryResult:
        search_input = SearchLogsInput(
            service=input_data.service,
            limit=input_data.limit,
        )
        result = await self.search_logs(search_input)

        # Filter by min_level
        min_order = LEVEL_ORDER.get(input_data.min_level.upper(), 0)
        filtered_logs = [
            log for log in result.logs
            if LEVEL_ORDER.get(log.level.upper(), 0) >= min_order
        ]
        result.logs = filtered_logs
        result.count = len(filtered_logs)
        return result

    async def get_error_rate(self, input_data: GetErrorRateInput) -> ErrorRateResult:
        now = input_data.end_time or datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=input_data.window_minutes)

        search_input = SearchLogsInput(
            service=input_data.service,
            start_time=window_start,
            end_time=now,
            limit=200,
        )
        logs_res = await self.search_logs(search_input)
        logs = logs_res.logs

        # Divide lookback into time interval buckets
        interval = timedelta(seconds=input_data.interval_seconds)
        buckets: List[ErrorRateBucket] = []

        total_logs = len(logs)
        total_errors = 0

        curr_start = window_start
        while curr_start < now:
            curr_end = min(curr_start + interval, now)
            bucket_logs = [l for l in logs if curr_start <= l.timestamp < curr_end]
            err_logs = [l for l in bucket_logs if l.level in ("ERROR", "CRITICAL")]
            err_pct = (len(err_logs) / len(bucket_logs) * 100.0) if bucket_logs else 0.0

            total_errors += len(err_logs)
            buckets.append(
                ErrorRateBucket(
                    start_time=curr_start,
                    end_time=curr_end,
                    total_logs=len(bucket_logs),
                    error_logs=len(err_logs),
                    error_percentage=round(err_pct, 2),
                )
            )
            curr_start += interval

        overall_pct = (total_errors / total_logs * 100.0) if total_logs > 0 else 0.0

        return ErrorRateResult(
            service=input_data.service,
            buckets=buckets,
            overall_error_rate_pct=round(overall_pct, 2),
            total_logs=total_logs,
            total_errors=total_errors,
        )

    async def get_correlated_errors(self, input_data: GetCorrelatedErrorsInput) -> CorrelatedErrorsResult:
        # Search for error logs matching error_pattern
        matching_res = await self.search_logs(
            SearchLogsInput(
                service=input_data.service,
                level="ERROR",
                pattern=input_data.error_pattern,
                limit=50,
            )
        )

        correlated_events = []
        for error_log in matching_res.logs:
            # Query window around this error
            window_start = error_log.timestamp - timedelta(seconds=input_data.window_seconds)
            window_end = error_log.timestamp + timedelta(seconds=input_data.window_seconds)

            surrounding = await self.search_logs(
                SearchLogsInput(
                    start_time=window_start,
                    end_time=window_end,
                    limit=20,
                )
            )
            correlated_events.append({
                "anchor_error_id": error_log.id,
                "anchor_timestamp": error_log.timestamp.isoformat(),
                "anchor_message": error_log.message,
                "surrounding_logs_count": surrounding.count,
                "surrounding_sample": [
                    {"service": l.service, "level": l.level, "message": l.message}
                    for l in surrounding.logs[:5]
                ],
            })

        return CorrelatedErrorsResult(
            service=input_data.service,
            error_pattern=input_data.error_pattern,
            matching_errors_count=len(matching_res.logs),
            correlated_events=correlated_events,
        )

    async def get_logs_around_event(self, input_data: GetLogsAroundEventInput) -> LogsAroundEventResult:
        window_delta = timedelta(seconds=input_data.window_seconds)
        start_time = input_data.timestamp - window_delta
        end_time = input_data.timestamp + window_delta

        res = await self.search_logs(
            SearchLogsInput(
                service=input_data.service,
                start_time=start_time,
                end_time=end_time,
                limit=input_data.limit,
            )
        )

        logs_before = [l for l in res.logs if l.timestamp <= input_data.timestamp]
        logs_after = [l for l in res.logs if l.timestamp > input_data.timestamp]

        return LogsAroundEventResult(
            target_timestamp=input_data.timestamp,
            window_seconds=input_data.window_seconds,
            service=input_data.service,
            logs_before=logs_before,
            logs_after=logs_after,
            total_logs=res.count,
        )
