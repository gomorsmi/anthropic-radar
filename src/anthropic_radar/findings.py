"""Findings engine — flags cost and hygiene anomalies across a scan."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .models.base import Finding, RunResult, Severity

TOKEN_ALERT_THRESHOLD = 10_000_000
INVITE_STALE_DAYS = 30


class FindingEngine:
    """
    | Rule ID   | Severity | Condition                                          |
    |-----------|----------|-----------------------------------------------------|
    | KEY_001   | MEDIUM   | Active API key with zero usage in lookback window    |
    | KEY_002   | INFO     | API key not assigned to any workspace (org default)  |
    | WS_001    | LOW      | Workspace has zero active API keys                    |
    | INV_001   | LOW      | Invite still pending after 30+ days                   |
    | USAGE_001 | MEDIUM   | Model consumes > 10M tokens in the lookback window    |
    | COST_001  | INFO     | Priority service-tier usage present (premium pricing) |
    | CC_001    | INFO     | Claude Code usage present with no matching workspace  |
    """

    def run(self, result: RunResult) -> list[Finding]:
        findings: list[Finding] = []
        findings += self._api_key_findings(result)
        findings += self._workspace_findings(result)
        findings += self._invite_findings(result)
        findings += self._usage_findings(result)
        findings += self._cost_findings(result)
        return findings

    def _api_key_findings(self, result: RunResult) -> list[Finding]:
        out = []
        used_key_ids = {u.api_key_id for u in result.usage if u.api_key_id}
        for key in result.api_keys:
            if (key.status or "").lower() == "active" and key.id not in used_key_ids and result.usage:
                out.append(
                    Finding(
                        rule_id="KEY_001",
                        severity=Severity.MEDIUM,
                        resource_kind="api_key",
                        resource_id=key.id,
                        message=f"Active API key '{key.name or key.id}' had no usage in the lookback window.",
                    )
                )
            if not key.workspace_id:
                out.append(
                    Finding(
                        rule_id="KEY_002",
                        severity=Severity.INFO,
                        resource_kind="api_key",
                        resource_id=key.id,
                        message=f"API key '{key.name or key.id}' is not scoped to a workspace (org default).",
                    )
                )
        return out

    def _workspace_findings(self, result: RunResult) -> list[Finding]:
        out = []
        keys_per_ws = defaultdict(int)
        for key in result.api_keys:
            if key.workspace_id and (key.status or "").lower() == "active":
                keys_per_ws[key.workspace_id] += 1
        for ws in result.workspaces:
            if ws.archived_at:
                continue
            if keys_per_ws.get(ws.id, 0) == 0:
                out.append(
                    Finding(
                        rule_id="WS_001",
                        severity=Severity.LOW,
                        resource_kind="workspace",
                        resource_id=ws.id,
                        message=f"Workspace '{ws.name or ws.id}' has zero active API keys.",
                    )
                )
        return out

    def _invite_findings(self, result: RunResult) -> list[Finding]:
        out = []
        now = datetime.now(timezone.utc)
        for invite in result.invites:
            if (invite.status or "").lower() != "pending" or not invite.invited_at:
                continue
            invited_at = invite.invited_at
            if invited_at.tzinfo is None:
                invited_at = invited_at.replace(tzinfo=timezone.utc)
            if now - invited_at > timedelta(days=INVITE_STALE_DAYS):
                out.append(
                    Finding(
                        rule_id="INV_001",
                        severity=Severity.LOW,
                        resource_kind="invite",
                        resource_id=invite.id,
                        message=f"Invite for '{invite.email or invite.id}' has been pending for over {INVITE_STALE_DAYS} days.",
                    )
                )
        return out

    def _usage_findings(self, result: RunResult) -> list[Finding]:
        out = []
        totals = defaultdict(int)
        for bucket in result.usage:
            if bucket.model:
                totals[bucket.model] += bucket.total_tokens
        for model, total in totals.items():
            if total > TOKEN_ALERT_THRESHOLD:
                out.append(
                    Finding(
                        rule_id="USAGE_001",
                        severity=Severity.MEDIUM,
                        resource_kind="model",
                        resource_id=model,
                        message=f"Model '{model}' consumed {total:,} tokens in the lookback window (> 10M).",
                    )
                )
        priority_tiers = {b.service_tier for b in result.usage if (b.service_tier or "").lower() == "priority"}
        if priority_tiers:
            out.append(
                Finding(
                    rule_id="COST_001",
                    severity=Severity.INFO,
                    resource_kind="organization",
                    resource_id=result.organization.id if result.organization else "org",
                    message="Priority service-tier usage detected; priced above standard tier and excluded from the cost report.",
                )
            )
        return out

    def _cost_findings(self, result: RunResult) -> list[Finding]:
        out = []
        if result.claude_code_usage:
            ws_ids = {b.workspace_id for b in result.usage if b.workspace_id}
            cc_users = {b.user_id for b in result.claude_code_usage if b.user_id}
            if cc_users and not ws_ids:
                out.append(
                    Finding(
                        rule_id="CC_001",
                        severity=Severity.INFO,
                        resource_kind="claude_code",
                        resource_id="claude_code_usage",
                        message="Claude Code usage detected with no corresponding Messages API workspace usage in the same window.",
                    )
                )
        return out
