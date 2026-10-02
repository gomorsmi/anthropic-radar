"""
Service relationship detection.

Claude has no server-side "assistant instructions" the way OpenAI does, so
instead of scanning a stored prompt, we scan the free-text fields an org
actually controls and that tend to leak integration intent: workspace
names and API key names/hints (e.g. "prod-lambda-ingest", "bigquery-etl-key",
"slack-bot-key"). Each hit becomes a ServiceRelationship edge in the
draw.io diagram, same shape/kinds as openai-radar.
"""
from __future__ import annotations

from .models.base import ApiKey, RelationshipKind, ServiceRelationship, Workspace

_SIGNALS: dict[RelationshipKind, list[str]] = {
    RelationshipKind.AWS: ["aws", "s3", "ec2", "lambda", "dynamodb", "sqs", "bedrock"],
    RelationshipKind.GCP: ["gcp", "bigquery", "gcs", "google-cloud", "vertex"],
    RelationshipKind.AZURE: ["azure", "blob-storage", "cosmosdb"],
    RelationshipKind.DATABASE: ["postgres", "mysql", "mongo", "redis", "neon", "supabase"],
    RelationshipKind.SLACK: ["slack"],
    RelationshipKind.EMAIL: ["sendgrid", "mailgun", "smtp"],
    RelationshipKind.WEBHOOK: ["webhook", "http-"],
}


def _match(text: str) -> list[tuple[RelationshipKind, str]]:
    lowered = text.lower()
    hits = []
    for kind, signals in _SIGNALS.items():
        for signal in signals:
            if signal in lowered:
                hits.append((kind, signal))
    return hits


def detect_relationships(workspaces: list[Workspace], api_keys: list[ApiKey]) -> list[ServiceRelationship]:
    out: list[ServiceRelationship] = []
    for ws in workspaces:
        for kind, signal in _match(ws.name or ""):
            out.append(
                ServiceRelationship(
                    source_kind="workspace", source_id=ws.id, source_label=ws.name, kind=kind, signal=signal
                )
            )
    for key in api_keys:
        haystack = " ".join(filter(None, [key.name, key.partial_key_hint]))
        for kind, signal in _match(haystack):
            out.append(
                ServiceRelationship(
                    source_kind="api_key", source_id=key.id, source_label=key.name, kind=kind, signal=signal
                )
            )
    return out
