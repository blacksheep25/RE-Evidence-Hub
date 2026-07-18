# Overnight local-model naming

This guide takes a Windows user from a validated export to a bounded overnight
local-model pass and a separate morning review. The built-in runner stays in
the foreground and writes only disposable candidates. It never changes raw
evidence, accepted annotations, or the Ghidra project.

```text
raw export (immutable)
  -> agent_runs/<run-id>/name_candidates.json (disposable proposals)
  -> explicit stronger-model or human review
  -> annotations/function_names.json (accepted reversible overlay)
```

## Before the first run

Install the repository host tools and select a complete export:

```powershell
cd X:\Sources\RE-Evidence-Hub
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e .

revhub projects
revhub use TargetClient.exe
revhub doctor
revhub validate --full
revhub query status
```

Replace `TargetClient.exe` with a project shown by `revhub projects`. The saved
project pointer lets later `revhub overnight` commands omit the export path.
Run `revhub review-queue --limit 250` if you want direct import/resource leads
to be attempted before the remaining unnamed `FUN_...` functions.

## Prepare Ollama on Windows

The simplest local provider is Ollama. Install it using the
[official Windows guide](https://docs.ollama.com/windows), then open a new
PowerShell terminal:

```powershell
ollama --version
ollama pull qwen3-coder:30b
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

`qwen3-coder:30b` is an example, not a requirement. Choose an instruction or
coding model that fits the machine's available RAM/VRAM and reliably returns
JSON. Use the exact name shown by `ollama list` in the runner command.

The normal Windows Ollama application exposes its local API at
`http://127.0.0.1:11434/api`. If the API check fails and the Ollama application
is not running, launch it. Standalone CLI users can instead run `ollama serve`
in a separate visible terminal and leave that terminal open. See Ollama's
[API introduction](https://docs.ollama.com/api/introduction) for the upstream
endpoint contract.

## Test one decision without writing

Always begin with a dry run. It asks the model about one function, prints the
decision, and writes no ledger, candidate, or runner log:

```powershell
revhub overnight `
  --provider ollama `
  --endpoint http://127.0.0.1:11434/api/chat `
  --model qwen3-coder:30b `
  --run-id local-night-01 `
  --dry-run
```

Check that the command exits successfully and returns one JSON object with
`"dry_run": true`, a target, a decision, and `"writes": 0`. Fix endpoint,
model-name, memory, or JSON-response problems before starting a long pass.
The dry run verifies connectivity and response parsing; because it deliberately
does not write a candidate, it does not exercise the final proposal guard.
Confirm that the returned decision uses `propose`, `skip`, or `defer` and has
the documented evidence fields before continuing.

## Start the bounded overnight run

Run the real pass in a visible foreground terminal:

```powershell
revhub overnight `
  --provider ollama `
  --endpoint http://127.0.0.1:11434/api/chat `
  --model qwen3-coder:30b `
  --run-id local-night-01 `
  --max-targets 500 `
  --max-minutes 480 `
  --context-chars 12000 `
  --timeout 300 `
  --retries 2 `
  --temperature 0 `
  --max-tokens 1200
```

The example stops after 500 targets or eight hours, whichever comes first.
Start with 10-25 targets on an unfamiliar model before committing to a large
pass. Keep the runner terminal and Ollama open. On a laptop, connect AC power
and temporarily configure Windows not to put the computer to sleep; the display
may turn off, but system sleep pauses the run. Restore the preferred sleep
setting afterwards.

The runner processes one function at a time, bounds decompiler context, and
retries transient HTTP failures. A malformed per-function decision is logged
and deferred; the existing attempt limit retires that target after three bad
decisions so the pass can continue. A genuine provider/API outage still stops
the run safely instead of mass-deferring functions while the model is offline.
A model proposal must pass the same evidence guard as an MCP proposal. Passing
that guard makes it reviewable, not correct.

## Monitor a running pass

Each completed decision or error is appended to:

```text
project_exports/TargetClient.exe/agent_runs/local-night-01/runner.jsonl
```

In a second PowerShell terminal, follow it with:

```powershell
$runDirectory = '.\project_exports\TargetClient.exe\agent_runs\local-night-01'
Get-Content -LiteralPath "$runDirectory\runner.jsonl" -Wait
```

The file appears after the first completed decision. The same directory holds:

- `investigation_progress.json`: processed/skipped/deferred addresses and
  attempt counts.
- `name_candidates.json`: pending model proposals and their cited evidence.
- `runner.jsonl`: chronological decisions and errors.

The runner prints a final JSON summary containing processed, proposed, skipped,
deferred, error, elapsed-time, and remaining estimates. If it exits with an
error, inspect the final `runner.jsonl` record, fix the provider problem, and
resume the same run.

## Stop and resume safely

Press `Ctrl+C` in the runner terminal to stop it. Mutable JSON artifacts are
locked and atomically replaced, so already completed work remains usable. Run
the same command with the same `--run-id` to resume; completed targets are not
repeated. A new run id creates an independent pass that can use a different
model or settings.

Run IDs must be filesystem-safe. Useful examples are `local-night-01`,
`qwen-pass-2026-07-18`, or `verification-pass-02`.

## Morning review

Do not copy candidates directly into accepted annotations. First inspect
`name_candidates.json`, then connect a stronger-model or human-controlled MCP
reviewer to the same export and run id:

```powershell
python X:\Sources\RE-Evidence-Hub\binary_agent_mcp_server.py `
  --export X:\Sources\RE-Evidence-Hub\project_exports\TargetClient.exe `
  --run-id local-night-01
```

Use that command as the stdio MCP server command in the review client. The
reviewer should:

1. Call `binary_candidate_queue` to list pending entries.
2. Call `binary_lookup` for one address and verify code/control flow.
3. Call `binary_review_candidate` with `accept` or `reject` and a review note.
4. Repeat only while it can genuinely verify the evidence.

Acceptance is blocked if the exported function hash changed or the cited
evidence is no longer grounded. Accepted candidates enter the annotation
overlay with source `candidate-review:<run-id>`. Rejected entries remain audit
history and never affect active names. There is intentionally no bulk
auto-accept command.

A suitable reviewer prompt is:

```markdown
Review one pending naming candidate at a time. Call binary_candidate_queue,
then binary_lookup for the candidate address. Verify the proposed name against
the function's concrete imports, strings, relationships, control flow, and
assembly when needed. Accept only conservative names directly supported by the
evidence; otherwise reject with a concise reason. Do not bulk accept.
```

## Discard an unwanted pass

Stop the runner and verify the exact directory under
`<export>/agent_runs/<run-id>/`. Moving that one run directory elsewhere or
deleting it scraps its ledger, proposals, and logs without changing raw exports
or `annotations/function_names.json`. Never delete the export's `annotations/`
directory when discarding an agent pass.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Connection refused | Start the local provider and retry `Invoke-RestMethod http://127.0.0.1:11434/api/tags`. |
| HTTP 404 | Pair `--provider ollama` with `/api/chat`, or `--provider openai` with the server's `/v1/chat/completions` endpoint. |
| Model not found | Use the exact name from `ollama list`; run `ollama pull <name>` if it is absent. |
| Model response did not contain JSON | Use an instruction-following model, keep temperature at zero, and test again with `--dry-run`. |
| Requests time out or exhaust memory | Use a smaller model or lower `--context-chars`; increase `--timeout` only when the model is healthy but slow. |
| Runner exits after partial progress | A `provider-error` means the endpoint remained unavailable after retries. Fix it and reuse the same run id; isolated malformed decisions no longer stop the pass. |
| Few or no pending candidates | Inspect skip/defer decisions and rejected proposal results; the guard intentionally refuses weakly grounded names. |
| Wrong binary appears in the output | Stop, run `revhub use <correct-project>`, then confirm with `revhub query status` before choosing a new run id. |

## Other OpenAI-compatible local servers

The default provider expects an OpenAI-compatible chat-completions response at
`choices[0].message.content`:

```powershell
revhub overnight `
  --provider openai `
  --endpoint http://127.0.0.1:1234/v1/chat/completions `
  --model local-model-name `
  --run-id local-night-01 `
  --max-targets 100 `
  --max-minutes 480
```

Change the endpoint and model name to those exposed by the local server. If it
requires a bearer token, pass `--api-key` or set `OPENAI_API_KEY` in the runner
terminal. Keep local APIs bound to loopback unless remote access is deliberately
configured and secured.

## Advanced: orchestrate the loop over MCP

The built-in runner above is the easiest unattended route. `revhub mcp` starts
only a stdio tool server; it does not launch a model or autonomously perform a
pass. Use it when an MCP-capable agent will orchestrate the loop itself:

```powershell
python X:\Sources\RE-Evidence-Hub\binary_agent_mcp_server.py `
  --export X:\Sources\RE-Evidence-Hub\project_exports\TargetClient.exe `
  --run-id local-night-01
```

The unattended orchestrator should repeat:

1. `binary_next_target`.
2. `binary_lookup` with decompiler evidence.
3. At most one or two relevant follow-up lookups.
4. `binary_propose_name` when grounded; otherwise `binary_progress` as skipped
   or deferred.
5. Stop when the target queue is exhausted.

Every target ends with a proposal or progress record. Never give an unattended
prompt access to `binary_annotate` or `binary_review_candidate`.

```markdown
Work one function at a time. Call binary_next_target, then binary_lookup.
Only cite imports, strings, or named relationships returned for that function.
If evidence supports a conservative name, call binary_propose_name. Otherwise
record skipped/deferred with binary_progress. Never call binary_annotate or
binary_review_candidate: you propose, you do not review. Stop when exhausted.
```
