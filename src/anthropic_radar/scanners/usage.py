"""Scanners for the Usage & Cost Admin API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterator

from ..client import RadarClient
from ..models.base import UsageBucket, ClaudeCodeUsageBucket, CostBucket


def _window(lookback_days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=lookback_days)
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")


def _pages(client: RadarClient, path: str, params: dict) -> Iterator[dict]:
    params = dict(params)
    while True:
        page = client.get(path, params=params)
        yield from page.get("data", [])
        if not page.get("has_more"):
            break
        params["page"] = page.get("next_page")
        if not params["page"]:
            break


def scan_usage(client: RadarClient, lookback_days: int = 7, bucket_width: str = "1d") -> list[UsageBucket]:
    if not client.has_admin_access:
        return []
    starting_at, ending_at = _window(lookback_days)
    out: list[UsageBucket] = []
    for bucket in _pages(
        client,
        "/v1/organizations/usage_report/messages",
        {
            "starting_at": starting_at,
            "ending_at": ending_at,
            "bucket_width": bucket_width,
            "group_by[]": ["model", "workspace_id", "api_key_id", "service_tier"],
        },
    ):
        for result in bucket.get("results", [bucket]):
            out.append(
                UsageBucket(
                    starting_at=bucket.get("starting_at"),
                    model=result.get("model"),
                    workspace_id=result.get("workspace_id"),
                    api_key_id=result.get("api_key_id"),
                    service_tier=result.get("service_tier"),
                    input_tokens=result.get("uncached_input_tokens", 0) or result.get("input_tokens", 0),
                    output_tokens=result.get("output_tokens", 0),
                    cache_read_tokens=result.get("cache_read_input_tokens", 0),
                    cache_creation_tokens=result.get("cache_creation_input_tokens", 0),
                )
            )
    return out


def scan_claude_code_usage(client: RadarClient, lookback_days: int = 7) -> list[ClaudeCodeUsageBucket]:
    if not client.has_admin_access:
        return []
    starting_at, ending_at = _window(lookback_days)
    out: list[ClaudeCodeUsageBucket] = []
    try:
        for bucket in _pages(
            client,
            "/v1/organizations/usage_report/claude_code",
            {"starting_at": starting_at, "ending_at": ending_at, "bucket_width": "1d"},
        ):
            for result in bucket.get("results", [bucket]):
                out.append(
                    ClaudeCodeUsageBucket(
                        starting_at=bucket.get("starting_at"),
                        user_id=result.get("actor", {}).get("user_id") if isinstance(result.get("actor"), dict) else result.get("user_id"),
                        model=result.get("model"),
                        sessions=result.get("num_sessions", 0),
                        input_tokens=result.get("input_tokens", 0),
                        output_tokens=result.get("output_tokens", 0),
                        lines_added=result.get("lines_of_code_added", result.get("code_edit_tool_lines_added", 0)) or 0,
                        lines_removed=result.get("lines_of_code_removed", result.get("code_edit_tool_lines_removed", 0)) or 0,
                    )
                )
    except Exception:
        # Claude Code usage report may be unavailable to orgs without seats provisioned
        return out
    return out


def scan_cost(client: RadarClient, lookback_days: int = 30) -> list[CostBucket]:
    if not client.has_admin_access:
        return []
    starting_at, ending_at = _window(lookback_days)
    out: list[CostBucket] = []
    for bucket in _pages(
        client,
        "/v1/organizations/cost_report",
        {"starting_at": starting_at, "ending_at": ending_at, "bucket_width": "1d", "group_by[]": ["workspace_id", "description"]},
    ):
        for result in bucket.get("results", [bucket]):
            amount = result.get("amount") or {}
            value = float(amount.get("value", 0)) if isinstance(amount, dict) else float(result.get("amount_usd", 0) or 0)
            out.append(
                CostBucket(
                    starting_at=bucket.get("starting_at"),
                    workspace_id=result.get("workspace_id"),
                    model=result.get("model"),
                    description=result.get("description"),
                    amount_usd=value,
                )
            )
    return out
