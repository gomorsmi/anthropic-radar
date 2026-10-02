# anthropic-radar

**Anthropic infrastructure FinOps SDK** — part of the Hyperscaler Radar suite.

Scan your Anthropic organization for users, invites, workspaces, API keys, Messages API
usage, Claude Code usage, and cost. Detect external service relationships from workspace
and API-key naming conventions, flag cost/hygiene anomalies via a findings engine, and
export inventory to CSV or a draw.io architecture diagram — all through a Python SDK that
mirrors the rest of the Radar suite (`openai-radar`, `aws-radar`, `gcp-radar`, ...).

---

## Install

```
pip install anthropic-radar
```

Requires Python 3.10+. CSV and draw.io export ship in the base install.

---

## Auth: two tiers, on purpose

Unlike OpenAI's project-scoped keys, **every org-visibility endpoint in the Anthropic API
lives behind the Admin API**, which requires an Admin key (`sk-ant-admin01-...`) that only
an org admin can provision, via Console → Settings → Admin Keys. A standard key
(`sk-ant-api03-...`) cannot list users, workspaces, keys, usage, or cost.

* `api_key` only → `anthropic-radar` runs, but every org-level table comes back empty.
  This is a supported "no access" state, not an error, so the CLI stays usable for
  quick checks in restricted environments.
* `admin_key` set (env `ANTHROPIC_ADMIN_KEY` or `--admin-key`) → full org-wide scan.

```python
from anthropic_radar import RadarClient, Runner

# Reads ANTHROPIC_API_KEY / ANTHROPIC_ADMIN_KEY from environment
client = RadarClient()
result = Runner.run_sync(client)

print(result.summary())
result.export_csv("./out/")          # convenience wrapper, see below
```

### Scoped to one workspace

```python
from anthropic_radar import RadarClient, Runner, RunConfig

client = RadarClient(admin_key="sk-ant-admin01-...")
config = RunConfig(workspace_id="wrkspc_xxx", usage_lookback_days=14)
result = Runner.run_sync(client, config)
```

---

## CLI

```
# Full scan — findings table to stdout
anthropic-radar run

# CSVs + draw.io diagram
anthropic-radar run --csv-dir ./out --drawio-file arch.drawio

# JSON instead of a table
anthropic-radar run --output json --out-file scan.json

# Admin key for org-wide data (or set $ANTHROPIC_ADMIN_KEY)
anthropic-radar run --admin-key sk-ant-admin01-... --csv-dir ./out

# Findings only
anthropic-radar findings

# Scope to a workspace, 14-day lookback
anthropic-radar run --workspace wrkspc_xxx --lookback 14

# Print the version
anthropic-radar version
```

Flags follow the Radar suite convention: `--output/-o` selects `table` or `json`,
`--out-file` writes the JSON payload, `--csv-dir` writes per-resource CSVs.

---

## Findings engine

| Rule ID   | Severity | Condition                                             |
| --------- | -------- | ------------------------------------------------------ |
| KEY_001   | MEDIUM   | Active API key had zero usage in the lookback window   |
| KEY_002   | INFO     | API key not scoped to any workspace (org default)      |
| WS_001    | LOW      | Workspace has zero active API keys                      |
| INV_001   | LOW      | Invite still pending after 30+ days                     |
| USAGE_001 | MEDIUM   | Model consumes > 10M tokens in the lookback window      |
| COST_001  | INFO     | Priority service-tier usage present (premium, uncosted) |
| CC_001    | INFO     | Claude Code usage present with no matching workspace    |

---

## Service relationship detection

Claude has no server-side "assistant instructions" field to mine the way OpenAI assistants
do. Instead, `detect_relationships()` scans workspace names and API-key names/hints for
the same external-service signal set as `openai-radar`, and emits `ServiceRelationship`
edges (visualized as dashed lines in the draw.io diagram):

| Kind     | Signals                                          |
| -------- | ------------------------------------------------- |
| AWS      | `aws`, `s3`, `ec2`, `lambda`, `dynamodb`, `sqs`, `bedrock` |
| GCP      | `gcp`, `bigquery`, `gcs`, `google-cloud`, `vertex` |
| AZURE    | `azure`, `blob-storage`, `cosmosdb`                |
| DATABASE | `postgres`, `mysql`, `mongo`, `redis`, `neon`, `supabase` |
| SLACK    | `slack`                                            |
| EMAIL    | `sendgrid`, `mailgun`, `smtp`                      |
| WEBHOOK  | `webhook`, `http-`                                 |

---

## SDK structure

```
src/anthropic_radar/
├── client.py               # RadarClient (api_key vs admin_key auth)
├── runner.py                # Runner, RunConfig, RunResult
├── findings.py               # FindingEngine, Finding, Severity
├── relationships.py          # naming-convention service relationship detection
├── models/base.py            # Pydantic v2 models for all resource types
├── scanners/                 # org.py, api_keys.py, usage.py (usage+cost+Claude Code)
├── exporters/                # csv_exporter.py, drawio_exporter.py
└── cli.py                    # anthropic-radar CLI
```

---

## Part of the Hyperscaler Radar suite

`aws-radar` · `gcp-radar` · `azure-radar` · `oci-radar` · `openai-radar` · `gemini-radar` · `datadog-radar` · `coreweave-radar` · `anthropic-radar`

## License

MIT
