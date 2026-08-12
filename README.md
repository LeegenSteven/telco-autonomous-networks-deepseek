# Local Telco Anomaly Detection and Root Cause Analysis

This project demonstrates an agentic LTE operations workflow using DeepSeek and
a completely local data layer. It detects KPI anomalies, creates incidents,
performs root cause analysis (RCA), classifies severity, searches local RCA
rules and documentation, and produces a report.

DigitalRoute provided the synthesized, realistic eNodeB performance and cell
trace samples in `data/`. The project does not connect to a live telecom
network.

## Architecture

```text
Google ADK (local orchestration only)
        |
        +--> DeepSeek API: reasoning and tool calling
        +--> DuckDB: performance, KPI, traces, incidents
        +--> Local JSON: RCA rules
        +--> Local Markdown: internal documentation
        +--> Local JSONL: application logs
```

Google Cloud, BigQuery, Vertex AI Search, ADC, and Terraform are not required.

## Prerequisites

- Python 3.12 or newer
- A DeepSeek API key

## Setup on Windows

From the repository root:

```powershell
cd agents
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edit `agents/.env` and set:

```dotenv
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODEL=deepseek-v4-flash
```

Do not commit `agents/.env`.

## Initialize local data

Run from `agents/`:

```powershell
python -m telco_local.init_db
```

This creates `.local/telco_demo.duckdb`, imports `data/performance.csv` and
`data/cell-traces.csv`, creates the KPI view, and creates the local incident
tables. The command is idempotent. To discard local incidents and recreate all
tables:

```powershell
python -m telco_local.init_db --reset
```

## Run the Chinese operations UI

From `agents/` with the virtual environment active:

```powershell
.\start_web.ps1
```

Open `http://127.0.0.1:8000`. The project-local UI uses Simplified Chinese for
navigation, status messages, confirmations, errors, and RCA reports, while
retaining telecom terms such as KPI, eNodeB, Cell ID, Incident, and RCA.

The page streams an auditable execution summary while an Agent is working. It
shows Agent stages, tool calls, completion states, and the answer as it is
generated, but deliberately does not expose private model chain-of-thought.
Use **停止生成** to cancel the active stream and stop the current Agent run.
A tool action that finished before cancellation cannot be rolled back
automatically.

Conversation history is persisted by ADK in each Agent's local
`.adk/session.db` SQLite database. The sidebar can reopen, rename, refresh, and
delete saved conversations. A new conversation is saved after its first
message and receives an automatic title based on that message. Deleting chat
history does not delete incidents or RCA reports stored in DuckDB.

The generic ADK developer UI is still available for debugging with
`adk web --logo-text "电信智能运维平台"`; its framework-level developer labels
remain controlled by the installed ADK package.

Before the first interactive run, you can verify live DeepSeek Tool Calling:

```powershell
python -m telco_local.smoke_test
```

This command makes a small real API request and therefore requires a valid
`DEEPSEEK_API_KEY`. The offline test suite never calls the API.

To run the live Incident Detector -> RCA acceptance test:

```powershell
python -m telco_local.e2e_test
```

This test makes multiple real API requests and creates one local demo incident.
It runs every read-only RCA stage and generates a report, but deliberately
declines simulated actions and report persistence.

### 1. Detect and create an incident

Select `incident_detector` and enter:

```text
Check if there are any new incidents.
```

Review the candidates and confirm one incident. Copy its ID.

### 2. Perform RCA

Select `root_cause_analysis` and enter:

```text
Analyse incident <incident-id>
```

The workflow retrieves local rules, queries local trace statistics, determines
severity, searches local documentation and similar incidents, reviews any
simulated actions, and generates an RCA report. The report is written to DuckDB
only after user confirmation.

## Configuration

The main settings in `agents/.env` are:

| Variable | Default | Purpose |
|---|---|---|
| `DEEPSEEK_API_KEY` | empty | DeepSeek authentication |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API endpoint |
| `DEEPSEEK_DEFAULT_MODEL` | `deepseek-v4-flash` | Default model for all agents |
| `LOCAL_DB_PATH` | `../.local/telco_demo.duckdb` | DuckDB file |
| `LOCAL_LOG_PATH` | `../.local/logs/agent_events.jsonl` | Structured local log |
| `EXTERNAL_DOCS_ENABLED` | `false` | Allow-list external HTTP retrieval |

Per-agent model overrides are documented in `agents/.env.example`.

## Data handling and safety

- The bundled records are synthetic.
- Raw cell trace rows stay in local DuckDB.
- Agent prompts use incident summaries and aggregate statistics rather than
  complete IMSI, MSISDN, or IMEISV values.
- Configuration adjustment tools are simulations and do not modify network
  equipment.
- Enabling external documentation retrieval sends requests to the allow-listed
  public URLs; it is disabled by default.

## Tests

Run from `agents/`:

```powershell
python -m pytest -q
```

The offline suite validates KPI calculations, incident and approved-report
persistence, RCA rule selection, tool-call serialization, similarity ranking,
and DeepSeek provider configuration without calling the DeepSeek API.

## Migration plan

The maintained implementation plan and acceptance criteria are in
`docs/local-deepseek-migration-plan.md`.

## License

Apache 2.0. See `LICENSE`.
