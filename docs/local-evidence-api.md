# Local Evidence API

`binary_agent_server.py` and `binary_agent_mcp_server.py` are the normal,
local-first interfaces for an exported binary. They read raw export JSON and
the reversible annotation overlay only. They do not require Ghidra to be open
and never write to the Ghidra database or raw function files.

Use the HTTP API when a human, shell script, browser, or external AI client
needs to query an export through a stable local URL. In-process Python code
should usually use `tools/evidence_tools.py` directly so it does not depend on
a background server or port.

## Start the HTTP API

```powershell
python .\binary_agent_server.py --export .\project_exports\sample_program.exe --port 5006
```

The service binds to `127.0.0.1:5006` by default. You can use command-line
flags or environment variables:

```powershell
$env:GHIDRA_AI_EXPORT_PATH = '.\project_exports\sample_program.exe'
$env:GHIDRA_AI_API_PORT = '5006'
python .\binary_agent_server.py
```

Command-line flags take the same role:

```powershell
python .\binary_agent_server.py --export .\project_exports\sample_program.exe --host 127.0.0.1 --port 5006
```

Core routes are dependency-free apart from Flask:

| Route | Purpose |
| --- | --- |
| `GET /health` | Small liveness probe for monitors and scripts. |
| `GET /status` | Target identity, annotation count, and index capabilities. |
| `GET /routes` | Machine-readable route catalog. |
| `POST /search` | Searches raw names, accepted annotations, and optional FTS body search. |
| `POST /lookup` | One evidence bundle: annotation, strings, imports, callers/callees, and decompiler output. |
| `POST /asset`, `/control`, `/packet` | Static evidence traces for a named term. Packet results are candidates, not protocol claims. |
| `POST /class` | Queries the derived class/vtable registry. A class-to-vtable association exists only where an accepted annotation explicitly cites that vtable address; RTTI and class strings remain discovery evidence. |
| `POST /review` | Queries the derived function-name review queue. Its `proposed_name` values are low-confidence review prompts, never active annotations. |
| `POST /reload` | Reloads accepted annotations only; it never reloads or mutates raw function data. |
| `POST /function`, `/callers`, `/callees`, `/strings`, `/imports` | Focused compatibility routes. |

Example:

```powershell
Invoke-RestMethod http://127.0.0.1:5006/health
Invoke-RestMethod http://127.0.0.1:5006/routes
Invoke-RestMethod http://127.0.0.1:5006/asset -Method Post -ContentType 'application/json' `
  -Body '{"term":"login_panel.asset"}'
```

`/semantic`, `/hybrid`, and `/ask` remain optional experimental routes. They
load their model/vector dependencies only when called and return HTTP 503 when
those dependencies are unavailable; they cannot prevent core static search
from starting.

## Build the optional fast local index

The core service works immediately from `index.json`. Build this derived FTS5
index when searching decompiler bodies frequently:

```powershell
revhub index
```

It creates `<export>\local_evidence.sqlite3`. Delete and rebuild it whenever
the export changes. Raw JSON and annotations remain untouched.


## Build the class/vtable registry and name review queue

These two derived artifacts make repeated work faster without smuggling an
inference into the active symbol set:

```powershell
revhub classes
revhub review-queue --limit 250
```

`class_registry.json` groups accepted `C..._Method` annotations with exported
RTTI/class-string evidence. It records a vtable association only if accepted
annotation evidence contains the concrete vtable address. A generic exported
`vftable` global is not assigned to a class automatically.

`name_review_queue.json` has only direct-import and direct-resource-string
candidates for still-raw `FUN_...` functions. It does not edit
`annotations/function_names.json`; inspect the function and use
`tools/function_annotations.py set` with concrete evidence before accepting a
name. Rebuild either artifact after annotations or the raw export change, then
restart the HTTP/MCP service.

Examples:

```powershell
Invoke-RestMethod http://127.0.0.1:5006/class -Method Post -ContentType 'application/json' -Body '{"query":"CIFSkillBoard"}'
Invoke-RestMethod http://127.0.0.1:5006/review -Method Post -ContentType 'application/json' -Body '{"query":"sendto"}'
```

## Generate a reviewable evidence pack

Evidence packs are derived JSON snapshots for one bounded recreation task. They
keep binary evidence, resource/control traces, and accepted annotations in
one reviewable file without changing raw exports:

```powershell
python .\tools\generate_evidence_pack.py 'Title Login and Server Select' `
  --export .\project_exports\sample_program.exe `
  --control LOGIN_BUTTON --control SERVER_LIST `
  --asset login_panel.asset --asset server_panel.asset `
  --function UI_ApplyLoginAndServerLayout
```

The default output is `<export>\evidence_packs\<title>.json`. Treat it as a
review artifact: if the binary export or accepted annotations change, rebuild
the pack rather than editing it manually.

## MCP adapter

The dependency-free stdio adapter exposes read-only tools to an MCP client:

```powershell
python .\binary_agent_mcp_server.py --export .\project_exports\sample_program.exe --run-id interactive-review
```

Tools are `binary_status`, `binary_search`, `binary_lookup`,
`binary_trace_asset`, `binary_trace_control`, `binary_trace_packet`,
`binary_class`, and `binary_review_queue`.
Accepted annotation names and their evidence are included in results; an LLM
or heuristic suggestion is never presented as an accepted name.

## In-process Python tools

For Python scripts running in this repository, prefer the in-process adapter:

```python
from tools.evidence_tools import EvidenceTools

tools = EvidenceTools(r".\project_exports\sample_program.exe")
result = tools.execute_tool("lookup", {"address": "00401000", "include_decompiler": False})
```

This uses the same `LocalEvidenceStore` core as the HTTP and MCP adapters.
Use `tools/evidence_client.py` only when the script intentionally needs to
call an already-running HTTP server.

The same module also has a direct CLI for one-off shell queries:

```powershell
revhub query status
revhub query search sendto --limit 5
revhub query lookup 0047c870 --no-decompiler --assembly
```

## Annotation refresh and export refresh

After recording an accepted name with `tools/function_annotations.py`, refresh
the running HTTP service without restarting it:

```powershell
Invoke-RestMethod http://127.0.0.1:5006/reload -Method Post
```

When the raw binary export changes instead, first run full export validation,
rebuild `local_evidence.sqlite3`, and restart the HTTP/MCP process. The reload
route intentionally cannot hide an unvalidated raw-export change.
