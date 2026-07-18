# Getting started

This guide takes a new user from a Ghidra program to validated, queryable evidence. The core workflow is local and does not require an LLM, Chroma, or a background service.

## 1. Install the host tools

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e .
revhub doctor
```

`requirements-core.txt` is the small unpinned baseline. The lock file is reproducible. `requirements-optional.txt` provides the supported optional semantic index and is unnecessary for export, validation, HTTP, MCP, or direct queries.

Try the checked-in fixture without Ghidra:

```powershell
revhub use .\samples\tiny_export
revhub validate --full
revhub query status
revhub query lookup 00401000 --no-decompiler
```

## 2. Export a program

### Ghidra user interface

1. Open the target in Ghidra and let analysis finish.
2. Add this repository as a Script Manager directory.
3. Run `run_exporter.py`.
4. Read `<export>/export_report.json`; do not continue past a failed stage.

The default destination is `<repository>/project_exports/<program-name>/`. Each program is self-contained. To use another drive, set this before starting Ghidra or host tools:

```powershell
$env:RE_EVIDENCE_PROJECTS_ROOT = 'X:\RE-Projects'
```

### Headless export

Headless export needs Ghidra 12.x, JDK 21, and PyGhidra:

```powershell
python -m pip install -r requirements-headless.txt
$env:GHIDRA_INSTALL_DIR = 'C:\Tools\ghidra_12.1.2_PUBLIC'
python .\tools\headless_export.py --binary 'C:\samples\TargetClient.exe'
```

Ghidra 11.3+ does not run these scripts through plain `analyzeHeadless -postScript`; the supplied driver launches through PyGhidra.

## 3. Select and validate the project

```powershell
revhub projects
revhub use TargetClient.exe
revhub validate --full
```

`revhub use` accepts a project name or path. Resolution order is explicit argument, `GHIDRA_AI_EXPORT_PATH`, saved pointer, then repo-local default. Validation checks the manifest, index, function count, and every function record.

## 4. Query evidence

One-off queries need no server:

```powershell
revhub query status
revhub query search sendto --limit 10
revhub query lookup 0047c870 --no-decompiler --assembly
```

For HTTP clients, start the foreground service:

```powershell
revhub serve --port 5006
Invoke-RestMethod http://127.0.0.1:5006/health
Invoke-RestMethod http://127.0.0.1:5006/routes
```

`/lookup` returns raw identity, accepted annotation, linked strings/imports, callers/callees, comments, xrefs, and optional decompiler/assembly.

## 5. Build derived artifacts

```powershell
revhub index
revhub classes
revhub review-queue --limit 250
revhub network
revhub benchmark --query send --query packet
```

To rebuild the export's AI context, Markdown, summaries, and search index later
without reopening Ghidra:

```powershell
revhub post-process
```

- `local_evidence.sqlite3`: substring decompiler-body search.
- `class_registry.json`: conservative class/vtable context.
- `name_review_queue.json`: non-promoting heuristic leads.
- `derived/network/`: networking lifecycle, leads, and unknowns.

For authorised runtime traffic and recreation contracts:

```powershell
revhub network-capture .\capture.jsonl --source 'authorised test session'
revhub protocol-contract
revhub protocol-contract --validate
```

Restart HTTP/MCP after rebuilding derived artifacts. For annotation changes, HTTP `/reload` is enough.

## 6. Record reviewed conclusions

After checking concrete evidence, record a reversible name:

```powershell
python .\tools\function_annotations.py init .\project_exports\TargetClient.exe
python .\tools\function_annotations.py set `
  .\project_exports\TargetClient.exe 00401000 Net_SendAck `
  --confidence high `
  --evidence 'Calls send after constructing the acknowledged frame'
```

Accepted names live in `annotations/function_names.json`; raw exports remain unchanged. See [Function annotations](function-annotations.md).

## 7. Connect an AI agent

```powershell
revhub mcp --run-id investigation-01
```

Interactive reviewers may use `binary_annotate`. Unattended models use `binary_propose_name`, writing only to `agent_runs/<run-id>/`. Review later with `binary_candidate_queue` and `binary_review_candidate`. See [AI agent guide](ai-agent-guide.md) and [Overnight naming](autonomous-agent.md).

Or test one decision through Ollama's native local endpoint:

```powershell
revhub overnight --provider ollama `
    --endpoint http://127.0.0.1:11434/api/chat `
    --model qwen3-coder:30b `
    --run-id investigation-01 `
    --context-window 8192 `
    --dry-run
```

Before leaving it unattended, follow the complete [overnight local-model
quick start](autonomous-agent.md) for provider setup, bounded run settings,
monitoring, Windows sleep, resume behaviour, morning review, and disposal.

Optional semantic search now uses one portable per-export backend:

```powershell
python -m pip install -e '.[semantic]'
revhub semantic-index
revhub query semantic 'packet dispatch' --limit 10
```

## Troubleshooting

- Run `revhub doctor` and confirm the active export.
- Run `revhub validate --full` before debugging query failures.
- Use `GET /health` for liveness and `GET /routes` for the HTTP catalog.
- Run direct scripts from the repo root or install editable.
- Missing optional vector packages must not affect core tools.
