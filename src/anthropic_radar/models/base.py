"""Pydantic v2 models for all Anthropic org resource types."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RelationshipKind(str, Enum):
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "AZURE"
    DATABASE = "DATABASE"
    SLACK = "SLACK"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"


class Organization(BaseModel):
    id: str
    name: Optional[str] = None


class User(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    added_at: Optional[datetime] = None


class Invite(BaseModel):
    id: str
    email: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    invited_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class Workspace(BaseModel):
    id: str
    name: Optional[str] = None
    archived_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    member_count: int = 0
    active_key_count: int = 0


class ApiKey(BaseModel):
    id: str
    name: Optional[str] = None
    workspace_id: Optional[str] = None
    status: Optional[str] = None  # active | inactive | archived
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    partial_key_hint: Optional[str] = None
    tokens_in_lookback: int = 0
    last_used_at: Optional[datetime] = None


class UsageBucket(BaseModel):
    starting_at: Optional[datetime] = None
    model: Optional[str] = None
    workspace_id: Optional[str] = None
    api_key_id: Optional[str] = None
    service_tier: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )


class ClaudeCodeUsageBucket(BaseModel):
    starting_at: Optional[datetime] = None
    user_id: Optional[str] = None
    model: Optional[str] = None
    sessions: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    lines_added: int = 0
    lines_removed: int = 0


class CostBucket(BaseModel):
    starting_at: Optional[datetime] = None
    workspace_id: Optional[str] = None
    model: Optional[str] = None
    description: Optional[str] = None
    amount_usd: float = 0.0


class ServiceRelationship(BaseModel):
    source_kind: str  # "workspace" | "api_key"
    source_id: str
    source_label: Optional[str] = None
    kind: RelationshipKind
    signal: str


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    resource_kind: str
    resource_id: str
    message: str


class RunResult(BaseModel):
    organization: Optional[Organization] = None
    users: list[User] = Field(default_factory=list)
    invites: list[Invite] = Field(default_factory=list)
    workspaces: list[Workspace] = Field(default_factory=list)
    api_keys: list[ApiKey] = Field(default_factory=list)
    usage: list[UsageBucket] = Field(default_factory=list)
    claude_code_usage: list[ClaudeCodeUsageBucket] = Field(default_factory=list)
    cost: list[CostBucket] = Field(default_factory=list)
    relationships: list[ServiceRelationship] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    admin_scan: bool = False

    def summary(self) -> str:
        lines = [
            "Anthropic Radar scan summary",
            f"  organization:        {self.organization.name if self.organization else 'n/a (no admin key)'}",
            f"  users:               {len(self.users)}",
            f"  pending invites:     {len([i for i in self.invites if (i.status or '').lower() == 'pending'])}",
            f"  workspaces:          {len(self.workspaces)}",
            f"  api keys:            {len(self.api_keys)}",
            f"  usage buckets:       {len(self.usage)}",
            f"  claude code buckets: {len(self.claude_code_usage)}",
            f"  cost buckets:        {len(self.cost)}",
            f"  relationships:       {len(self.relationships)}",
            f"  findings:            {len(self.findings)}",
        ]
        by_sev: dict[str, int] = {}
        for f in self.findings:
            by_sev[f.severity.value] = by_sev.get(f.severity.value, 0) + 1
        if by_sev:
            lines.append("  findings by severity: " + ", ".join(f"{k}={v}" for k, v in sorted(by_sev.items())))
        return "\n".join(lines)

    def export_csv(self, out_dir):
        from ..exporters.csv_exporter import export_csv

        return export_csv(self, out_dir)

    def export_drawio(self, out_path):
        from ..exporters.drawio_exporter import export_drawio

        return export_drawio(self, out_path)
