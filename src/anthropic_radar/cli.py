"""anthropic-radar CLI."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .client import AnthropicRadarError, RadarClient
from .exporters.csv_exporter import export_csv
from .exporters.drawio_exporter import export_drawio
from .runner import RunConfig, Runner


def _print_table(title: str, rows, columns):
    print(f"\n{title} ({len(rows)})")
    if not rows:
        return
    widths = [max(len(c), max((len(str(getattr(r, c, ''))) for r in rows), default=0)) for c in columns]
    print("  " + "  ".join(c.ljust(w) for c, w in zip(columns, widths)))
    for r in rows:
        print("  " + "  ".join(str(getattr(r, c, "")).ljust(w) for c, w in zip(columns, widths)))


def _cmd_run(args: argparse.Namespace) -> int:
    client = RadarClient(api_key=args.api_key, admin_key=args.admin_key)
    config = RunConfig(
        workspace_id=args.workspace,
        usage_lookback_days=args.lookback,
        cost_lookback_days=max(args.lookback, 30),
    )
    try:
        result = Runner.run_sync(client, config)
    except AnthropicRadarError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.output == "json":
        payload = result.model_dump(mode="json")
        text = json.dumps(payload, indent=2, default=str)
        if args.out_file:
            with open(args.out_file, "w", encoding="utf-8") as fh:
                fh.write(text)
        else:
            print(text)
    else:
        print(result.summary())
        _print_table("Workspaces", result.workspaces, ["id", "name", "member_count"])
        _print_table("API keys", result.api_keys, ["id", "name", "workspace_id", "status"])
        _print_table("Findings", result.findings, ["rule_id", "severity", "resource_kind", "message"])

    if args.csv_dir:
        written = export_csv(result, args.csv_dir)
        print(f"\nWrote {len(written)} CSV file(s) to {args.csv_dir}")
    if args.drawio_file:
        path = export_drawio(result, args.drawio_file)
        print(f"Wrote draw.io diagram to {path}")
    return 0


def _cmd_findings(args: argparse.Namespace) -> int:
    client = RadarClient(api_key=args.api_key, admin_key=args.admin_key)
    try:
        result = Runner.run_sync(client, RunConfig(usage_lookback_days=args.lookback))
    except AnthropicRadarError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _print_table("Findings", result.findings, ["rule_id", "severity", "resource_kind", "resource_id", "message"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="anthropic-radar")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--api-key", default=None, help="Standard key (sk-ant-api03-...). Defaults to $ANTHROPIC_API_KEY.")
    common.add_argument("--admin-key", default=None, help="Admin key (sk-ant-admin01-...), for org-wide visibility. Defaults to $ANTHROPIC_ADMIN_KEY.")

    run_p = sub.add_parser("run", parents=[common], help="Full scan")
    run_p.add_argument("--workspace", default=None, help="Scope API-key scan to one workspace ID")
    run_p.add_argument("--lookback", type=int, default=7, help="Usage lookback window, in days")
    run_p.add_argument("--output", "-o", choices=["table", "json"], default="table")
    run_p.add_argument("--out-file", default=None, help="Write JSON payload here instead of stdout")
    run_p.add_argument("--csv-dir", default=None, help="Write per-resource CSVs here")
    run_p.add_argument("--drawio-file", default=None, help="Write a draw.io architecture diagram here")
    run_p.set_defaults(func=_cmd_run)

    findings_p = sub.add_parser("findings", parents=[common], help="Findings only")
    findings_p.add_argument("--lookback", type=int, default=7)
    findings_p.set_defaults(func=_cmd_findings)

    version_p = sub.add_parser("version", help="Print the version")
    version_p.set_defaults(func=lambda args: print(__version__) or 0)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
