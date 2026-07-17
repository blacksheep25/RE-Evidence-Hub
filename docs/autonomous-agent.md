# Autonomous investigation over MCP

This guide describes running an MCP-capable agent against an export **unattended
and resumably** — e.g. overnight — so it keeps naming functions on a large
binary without stopping, and picks up cleanly after a restart.

It is model- and client-agnostic. A worked example for the [Hermes](#example-hermes-client)
client is at the end.

## Mental model: the export is the memory

The agent is a *retriever and judge*, not an oracle. Two files beside the export
hold all durable state, so nothing important lives only in the model's context:

- **`annotations/function_names.json`** — the reversible overlay of accepted,
  evidence-backed names. This is the agent's *notebook*. A confirmed name comes
  back on the next `binary_lookup` as `active_name`, so a name concluded at 1am
  is still known at 4am even after the context window is compacted.
- **`investigation_progress.json`** — the work ledger: which functions are
  `done` / `skipped`, with attempt counts. This is the *task queue*.

Because both are on disk, **context compaction and process restarts are
non-events**: the agent re-reads them and continues. That is what makes an
overnight run resumable and its progress trackable.

## The loop

The MCP server exposes read tools (`binary_status`, `binary_search`,
`binary_lookup`, `binary_trace_*`, `binary_class`, `binary_review_queue`) plus
three tools that close the autonomous loop:

| Tool | Role |
| --- | --- |
| `binary_next_target` | Pick the next function to work on (skips anything named or recorded done/skipped). Returns `{exhausted: true}` when the frontier is empty. |
| `binary_annotate` | **The only write tool.** Record a confirmed name + evidence. Guarded (see below); on success the name becomes `active_name` and the target is marked done. |
| `binary_progress` | Mark a target `done`/`skipped`/`deferred`, and/or read the progress summary. |

A single overnight iteration:

1. `binary_next_target` → an address (or `exhausted`, then stop).
2. `binary_lookup` that address (decompiler + strings + imports + callers/callees).
3. Decide a name from that evidence, **or** give up.
4. If naming: `binary_annotate` with `evidence_refs` you actually saw in step 2.
   If giving up: `binary_progress` with `status: "skipped"` so the loop advances.
5. Repeat.

Resuming is just restarting the loop: already-named and skipped targets are not
re-served.

## The write guard (why the durable output stays trustworthy)

Nobody is watching at 3am, and a wrong accepted name is self-reinforcing (it
feeds back as `active_name` on every future lookup). So `binary_annotate`
requires **`evidence_refs`** — concrete tokens (an import name, a string value,
a callee name) — and **rejects the write if any ref is not present in that
function's own evidence bundle**. A hallucinated justification never becomes an
accepted name; the tool returns `{accepted: false, missing_refs: [...]}` and the
agent can retry with real refs or skip. This enforces the project's
evidence-first rule mechanically.

## Self-healing / operational notes

- **Resumable:** state is on disk; restart continues. Ledger writes are atomic
  (write-temp-then-rename), so a crash mid-write cannot corrupt progress.
- **No dead loops:** the ledger counts attempts; mark a target `skipped` when it
  can't be named and the frontier moves on.
- **Bounded work per step:** query one function at a time via `binary_lookup`;
  never dump the whole export. This keeps each iteration small regardless of
  binary size (the docs' reference target has ~74k functions — you will not
  "finish" it; you make *prioritized, compounding* progress).
- **Read-only-ish + reversible:** the only writes are overlay annotations and
  the progress ledger; raw export files are never touched. Delete the overlay to
  undo everything.

## Example: Hermes client

Hermes has a built-in MCP client: it spawns configured stdio servers at startup,
discovers their tools, and exposes them to the model as native tools named
`mcp__<server>__<tool>`. Add the server to Hermes' `config.yaml` (native Windows:
`%LOCALAPPDATA%\hermes\config.yaml`):

```yaml
mcp_servers:
  re_evidence_hub:                 # keep the name [A-Za-z0-9_] (it is sanitized into the tool name)
    command: C:\path\to\RE-Evidence-Hub\.venv\Scripts\python.exe   # a NON-shell command; do NOT wrap in cmd /c or powershell -Command
    args:
      - C:\path\to\RE-Evidence-Hub\binary_agent_mcp_server.py
      - --export
      - C:\Users\you\ghidra_ai_exports\TargetProgram.exe           # ABSOLUTE: the subprocess cannot rely on ~ expansion
    env:
      # Hermes gives stdio servers a STRIPPED environment. On Windows, Python
      # often needs these because they are not inherited:
      SystemRoot: C:\Windows
      APPDATA: C:\Users\you\AppData\Roaming
      PYTHONUNBUFFERED: "1"
    connect_timeout: 60            # initial connect + discovery (seconds)
    timeout: 300                   # per tool-call (seconds)
    sampling:
      enabled: false               # this server issues no sampling requests
```

Then **restart Hermes** (MCP servers are discovered at startup; there is no hot
reload). Verify with `hermes mcp list` / `hermes mcp test re_evidence_hub`.

Why these specifics (from Hermes' MCP client behavior):

- **Non-shell `command`.** A shell interpreter (`cmd /c`, `powershell -Command`,
  `bash -c`) triggers Hermes' MCP security scanning; a plain `python.exe` path is
  never flagged.
- **Absolute `--export` + `env`.** Hermes strips the environment and does not set
  the subprocess cwd, so relative paths and `~` expansion are unreliable; pass
  absolute paths and add any needed Windows vars under `env`.
- **Unattended writes need no special approval.** Hermes does not gate individual
  MCP tool calls, so `binary_annotate` runs without prompts. (The `approvals.*`
  settings only affect the agent's *own* shell/exec tool.) Ensure
  `HERMES_SAFE_MODE` is unset, or MCP servers do not load at all.
- **Tools-only, protocol-compatible.** The server advertises only a `tools`
  capability (required, or Hermes registers zero tools) and answers `initialize`
  with a protocol version Hermes' SDK accepts; it never asks the client for
  resources, prompts, or elicitation, so nothing can block an unattended run.

Give the model a short standing instruction to run the loop above (call
`binary_next_target`, `binary_lookup`, then `binary_annotate` or
`binary_progress`), and it will make durable, resumable progress across sessions.
