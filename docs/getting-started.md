# Getting Started

This guide assumes you have never used this project before. The short version:
open a binary in Ghidra, export it to JSON, then use local tools to search and
review that evidence without keeping Ghidra open.

## What This Project Is

Ghidra AI Exporter is a bridge between Ghidra and external analysis tools.
Ghidra is excellent for detailed reverse engineering, but it is not always the
most convenient place to do broad searches, build reports, or feed small
evidence bundles to AI.

The exporter creates a folder containing structured JSON:

- one file per function;
- imports, strings, globals, types, memory blocks, and call graph data;
- decompiler output and assembly;
- a search index;
- optional derived files for faster or richer lookup.

After that, host-side Python tools can query the folder directly.

## Why You Would Use It

Use this project when you want to:

- search a large Ghidra program quickly by name, string, import, or decompiler
  text;
- give an AI assistant precise evidence without pasting giant files;
- inspect callers, callees, strings, imports, and decompiler output from one
  local API call;
- record reviewed function names in a reversible overlay;
- build repeatable reports and derived indexes from a saved export;
- work without keeping Ghidra open once the export is created.

Do not use it as an automatic truth machine. It preserves and retrieves
evidence; you still decide what the evidence proves.

## Prerequisites

- Ghidra with the target program loaded and analysed.
- Python 3 for host-side tools.
- Host dependencies when using the HTTP API, CLI, MCP adapter, or derived-index
  builders. The supported baseline is small:

```powershell
python -m pip install -r requirements-core.txt
```

  For an exact, reproducible install (pinned transitive dependencies), use the
  lock file instead:

```powershell
python -m pip install -r requirements.lock
```

  The optional semantic/vector search path (Chroma + embeddings) is experimental
  and pulls in PyTorch. Install it only if you need those routes:

```powershell
python -m pip install -r requirements-optional.txt
```

Core export runs inside Ghidra's own scripting environment. Host tools run in
normal Python. Keep those worlds separate. A virtual environment is recommended
for the host tools:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
```

## Step 1: Export From Ghidra

1. Open the target program in Ghidra.
2. Let Ghidra analyse it.
3. Open Script Manager.
4. Run `run_exporter.py` from this project.

By default, the export goes to:

```text
%USERPROFILE%\ghidra_ai_exports\<program-name>
```

Example export path:

```text
%USERPROFILE%\ghidra_ai_exports\sample_program.exe
```

The export report is written to:

```text
<export>\export_report.json
```

Open that if a stage failed.

### Alternative: export without opening Ghidra (headless)

If you would rather not open the Ghidra GUI, run the same pipeline headless with
`tools/headless_export.py`. It imports the binary, runs auto-analysis, and runs
the exporter through PyGhidra.

Prerequisites:

- A local Ghidra install (>= 12.0). Point to it with `--ghidra` or the
  `GHIDRA_INSTALL_DIR` environment variable.
- A JDK 21 (Ghidra's requirement), on `PATH`, in `JAVA_HOME`, or passed with
  `--java-home`.
- PyGhidra in your host Python:

```powershell
python -m pip install -r requirements-headless.txt
# offline, matching your Ghidra build exactly:
# python -m pip install --no-index -f <GHIDRA>\Ghidra\Features\PyGhidra\pypkg\dist pyghidra
```

Run it:

```powershell
$env:GHIDRA_INSTALL_DIR = "C:\path\to\ghidra_12.1.2_PUBLIC"
python .\tools\headless_export.py --binary "C:\samples\sample_program.exe"
```

The export lands in the same place as the GUI exporter
(`%USERPROFILE%\ghidra_ai_exports\<ProgramName>`). Continue with Step 2.

Ghidra 11.3+ removed Jython, so a plain
`analyzeHeadless ... -postScript run_exporter.py` cannot run the Python
exporter ("Ghidra was not started with PyGhidra"). `headless_export.py` uses
PyGhidra specifically to avoid that.

## Step 2: Validate the Export

Before using the export for analysis, validate the basic structure:

```powershell
python .\tools\validate_export.py %USERPROFILE%\ghidra_ai_exports\sample_program.exe --full
```

This checks required files, `index.json`, the function count, and every
function record. If validation fails, fix or recreate the export before
building derived indexes.

## Step 3: Start the Local Evidence API

Start the HTTP API when you want PowerShell, browser, or external AI clients
to query the export:

```powershell
python .\binary_agent_server.py --export %USERPROFILE%\ghidra_ai_exports\sample_program.exe --port 5006
```

Check it:

```powershell
Invoke-RestMethod http://127.0.0.1:5006/health
Invoke-RestMethod http://127.0.0.1:5006/status
```

`/health` is a small liveness check. `/status` tells you which export is being
served, how many functions it has, how many accepted annotations exist, and
which derived indexes are available.

## Step 4: Search and Inspect Evidence

Search for candidates:

```powershell
Invoke-RestMethod http://127.0.0.1:5006/search `
  -Method Post `
  -ContentType application/json `
  -Body '{"query":"sendto","limit":10}'
```

Inspect one candidate:

```powershell
Invoke-RestMethod http://127.0.0.1:5006/lookup `
  -Method Post `
  -ContentType application/json `
  -Body '{"address":"00401000","include_decompiler":true,"include_assembly":false}'
```

`/lookup` is usually the most important route. It returns:

- raw function identity;
- accepted annotation, if one exists;
- strings and imports linked to the function;
- callers and callees;
- comments and xrefs;
- optional decompiler and assembly output.

## Step 5: Build Useful Derived Indexes

The core API works from the raw export immediately. Derived indexes make
specific workflows better.

Fast decompiler-body search:

```powershell
python .\tools\build_local_index.py %USERPROFILE%\ghidra_ai_exports\sample_program.exe
```


Class/vtable review registry:

```powershell
python .\tools\build_class_registry.py %USERPROFILE%\ghidra_ai_exports\sample_program.exe
```

Low-confidence name review queue:

```powershell
python .\tools\build_name_review_queue.py %USERPROFILE%\ghidra_ai_exports\sample_program.exe --limit 250
```

Restart the HTTP/MCP service after rebuilding derived files. For annotation
changes only, `/reload` is enough.

## Step 6: Record Reviewed Function Names

Do not rename functions just because a search result or model suggested a
name. When you have concrete evidence, record it in the reversible annotation
overlay:

```powershell
python .\tools\function_annotations.py init %USERPROFILE%\ghidra_ai_exports\sample_program.exe

python .\tools\function_annotations.py set `
  %USERPROFILE%\ghidra_ai_exports\sample_program.exe `
  00401000 `
  Net_SendAck `
  --confidence high `
  --evidence "Calls sendto after building ACK payload"
```

Refresh a running HTTP service:

```powershell
Invoke-RestMethod http://127.0.0.1:5006/reload -Method Post
```

Accepted names appear as `active_name`; Ghidra's exported name remains
available as `raw_name`.

## Direct CLI Without a Server

When you just want one query from PowerShell, use the direct evidence CLI
instead of starting the HTTP server:

```powershell
python .\tools\evidence_tools.py --export %USERPROFILE%\ghidra_ai_exports\sample_program.exe status
python .\tools\evidence_tools.py --export %USERPROFILE%\ghidra_ai_exports\sample_program.exe search sendto --limit 5
python .\tools\evidence_tools.py --export %USERPROFILE%\ghidra_ai_exports\sample_program.exe lookup 0047c870 --no-decompiler --assembly
```

This prints JSON and uses the same evidence core as the HTTP and MCP adapters.
It does not start a background process.

## AI Workflows

There are three ways AI can use the export:

| Situation | Use |
| --- | --- |
| AI can run Python in this repo | `tools/evidence_tools.py` |
| AI or another process can call HTTP | `binary_agent_server.py` or `tools/evidence_client.py` |
| AI client supports MCP | `binary_agent_mcp_server.py` |

For an interactive local model:

```powershell
python .\tools\tool_agent.py %USERPROFILE%\ghidra_ai_exports\sample_program.exe http://localhost:11434/api/chat llama3
```

The model is expected to request tools, receive evidence, and then answer with
addresses, evidence, and confidence. Semantic/vector routes are optional leads,
not proof.

## Common Questions

**Do I need Ghidra open while using the API?**

No. Ghidra is needed to create or refresh the export. The API reads the saved
export folder.

**Does this change my Ghidra database?**

No. Host tools read raw export files and write derived files beside them. The
function-name overlay is local and reversible.

**Why not have every script call the HTTP server?**

Local Python scripts can import `LocalEvidenceStore` or `EvidenceTools`
directly. That avoids port and process management. HTTP is for humans,
external processes, and AI clients that need a stable local API.

**What should I trust?**

Trust raw evidence and accepted annotations. Treat autogenerated names,
review-queue suggestions, semantic search, and model output as leads.

**When do I rebuild things?**

- Raw export changed: validate, rebuild derived indexes, restart services.
- Annotation changed: call `/reload` or restart.

## Troubleshooting

`/status` shows the wrong export:

Stop the old server and restart with `--export <correct-folder>`.

Port conflict:

Use another port:

```powershell
python .\binary_agent_server.py --port 5010
```

Search misses decompiler-body text:

Build `local_evidence.sqlite3` with `tools/build_local_index.py`. Body search is
substring-based, so `recv` also finds `WSARecv`. If an index built by an older
version misses substrings, rebuild it: the index now uses a trigram tokenizer
(one-time cost — the index is larger and slower to build than the old
whole-token one, but this is optional derived data you can rebuild any time).

Class or review routes say unavailable:

Build `class_registry.json` or `name_review_queue.json` and restart the
service.

Semantic routes fail:

That is allowed. Core evidence routes do not depend on semantic/vector
dependencies.
