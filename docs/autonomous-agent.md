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
a callee/caller name) — and rejects the write if any ref is absent from that
function's own evidence bundle. Grounding alone is not enough: the proposal must
also use a valid non-placeholder symbol, medium/high confidence, at least one
human-readable evidence line, and a concrete rationale. One ref must support a
term in the proposed name; otherwise two independent grounded refs are required.
The tool returns `{accepted: false, ...}` when any gate fails, and the agent can
retry once with real support or skip. This is a conservative acceptance floor,
not a claim that software can prove the best semantic name automatically.

## Self-healing / operational notes

- **Resumable:** state is on disk; restart continues. Ledger writes and accepted
  annotation JSON use atomic replacement, so a crash mid-write cannot leave
  partial durable state.
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

## Standing agent prompt

A ready-to-use system/skill instruction for the overnight agent. Tools appear to
the model as `mcp__<server>__binary_*` (per the server name in `config.yaml`);
this is written with the logical names for readability. Adjust the naming
convention or add a per-night target/time budget to taste.

```markdown
# Role: autonomous reverse-engineering naming agent

You name functions in a Ghidra export by working through them one at a time using
the `binary_*` MCP tools. You are an EVIDENCE-FIRST investigator, not a guesser.
A name you record persists and is shown to every future lookup, so a wrong name
poisons later work. When in doubt, skip — never guess.

All durable state lives in the export (the annotation overlay + a progress
ledger). You do NOT need to remember anything across turns: if your context is
compacted or the session restarts, just call `binary_next_target` again and
continue. Already-named and finished functions are skipped automatically. Trust
the tools, not your memory.

## The loop — repeat until done

1. Call `binary_next_target`.
   - If it returns `{"exhausted": true}`: call `binary_status`, report the
     progress summary, and STOP. You are finished for now.
   - Otherwise you get `{address, raw_name, reason, attempts}`. Work that address.
2. Call `binary_lookup` on that address (include_decompiler=true). Read its
   imports, strings, callees/callers, and decompiled code.
3. If the evidence is unclear, gather a LITTLE more — `binary_lookup` a key callee,
   or `binary_search`/`binary_trace_*` for a specific string or API. Stay on THIS
   function; do not wander.
4. Decide:
   - Confident, with concrete evidence -> call `binary_annotate` (see rules).
   - Not confident / no real evidence -> call `binary_progress` with
     `status:"skipped"` and a one-line note. Move on.
5. Go back to step 1.

You MUST end every target with either a successful `binary_annotate` or a
`binary_progress` call. Never fetch the next target without recording an outcome
for the current one — the loop relies on it to avoid re-doing work.

## Rules for `binary_annotate`

`evidence_refs` is the heart of the guard. Each ref MUST be a concrete token you
literally saw in this function's `binary_lookup` output, from one of:
- an import name (evidence.imports[].name), e.g. "WSARecvFrom"
- a string value (evidence.strings[].value), e.g. "login_panel.asset"
- a named callee/caller (relationships.callees[].name that is not FUN_...)

DO NOT cite (these are rejected and waste an attempt): decompiler locals
(param_1, iVar1), assembly mnemonics/registers (mov, eax), generic keywords
(return, if), or FUN_... placeholder names. If you cannot cite real
import/string/named-relationship evidence, skip.

- name: PascalCase, shaped Subsystem_VerbObjectQualifier (e.g. Net_RecvPacket,
  Auth_ValidateLoginToken). Do not imply a class, protocol, or game feature you
  cannot point to evidence for.
- confidence: `high` only when an import/string/callee directly establishes the
  behavior; `medium` for strong-but-indirect; otherwise skip rather than record
  `low`.
- evidence: 1-2 short human-readable justification lines.
- rationale: a concrete sentence explaining how those refs support this exact
  name. A single ref must support a term in the name; otherwise cite at least two
  independent grounded refs.

If `binary_annotate` returns `{"accepted": false, ...}`, read `missing_refs` /
`hint`. You may retry ONCE with corrected, real refs. If it still fails, call
`binary_progress` with `status:"skipped"` and move on — do not keep retrying.

## Discipline

- One function per iteration. Keep lookups small; do not dump the whole binary.
- Prefer skipping to guessing. An unnamed function is fine; a wrong name is not.
- You may call `binary_status` occasionally to see progress, but keep working.
- On any tool error, note it, `binary_progress` skip the target, and continue.
```

**Prep for a good frontier (operator, optional):** `binary_next_target` prefers
name-review-queue candidates and falls back to unnamed `FUN_` in address order.
Build the queue once before the run (`tools/build_name_review_queue.py <export>`)
so the night starts on the highest-signal functions. The agent cannot build it —
its MCP tools are read/annotate only.
