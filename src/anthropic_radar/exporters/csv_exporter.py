"""Per-resource CSV export."""
from __future__ import annotations

import csv
from pathlib import Path

from ..models.base import RunResult

_TABLES = ["users", "invites", "workspaces", "api_keys", "usage", "claude_code_usage", "cost", "relationships", "findings"]


def export_csv(result: RunResult, out_dir: str | Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for table in _TABLES:
        rows = getattr(result, table)
        path = out_dir / f"{table}.csv"
        if not rows:
            continue
        fieldnames = list(rows[0].model_dump().keys())
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: ("" if v is None else v) for k, v in row.model_dump().items()})
        written.append(path)
    return written
