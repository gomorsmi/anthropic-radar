"""Runner: orchestrates scanners, findings, and relationship detection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .client import RadarClient
from .findings import FindingEngine
from .models.base import RunResult
from .relationships import detect_relationships
from .scanners.api_keys import scan_api_keys
from .scanners.org import scan_invites, scan_organization, scan_users, scan_workspaces
from .scanners.usage import scan_claude_code_usage, scan_cost, scan_usage


@dataclass
class RunConfig:
    workspace_id: Optional[str] = None
    usage_lookback_days: int = 7
    cost_lookback_days: int = 30
    include_claude_code: bool = True


class Runner:
    @staticmethod
    def run_sync(client: RadarClient, config: Optional[RunConfig] = None) -> RunResult:
        config = config or RunConfig()
        result = RunResult(admin_scan=client.has_admin_access)

        result.organization = scan_organization(client)
        result.users = scan_users(client)
        result.invites = scan_invites(client)
        result.workspaces = scan_workspaces(client)
        result.api_keys = scan_api_keys(client, workspace_id=config.workspace_id)
        result.usage = scan_usage(client, lookback_days=config.usage_lookback_days)
        result.cost = scan_cost(client, lookback_days=config.cost_lookback_days)
        if config.include_claude_code:
            result.claude_code_usage = scan_claude_code_usage(client, lookback_days=config.usage_lookback_days)

        result.relationships = detect_relationships(result.workspaces, result.api_keys)
        result.findings = FindingEngine().run(result)
        return result
