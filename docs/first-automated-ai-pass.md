# Your first automated AI pass

Use this guide when you want a local model to inspect an exported program while
you are away, without letting it change your original evidence or Ghidra
project.

## The simple idea

Think of the export as the original case file. The automated model is allowed
to leave sticky notes in its own folder. It is **not** allowed to rewrite the
case file or rename functions in Ghidra.

```text
raw Ghidra export (never changed)
    -> automated model proposes names in one run folder
    -> you or a stronger model checks each proposal
    -> verified names become reversible annotations
```

This means it is safe to try a small pass. A bad model can create poor
proposals, but it cannot silently turn them into accepted facts.

## Before you start

You need:

- A completed Ghidra export. Follow [Getting started](getting-started.md) if
  you do not have one yet.
- The host tools installed with `python -m pip install -e .`.
- Ollama or another local OpenAI-compatible model server running.

Choose the export and make sure it is healthy:

```powershell
revhub projects
revhub use TargetClient.exe
revhub doctor
revhub validate --full
revhub query status
```

Replace `TargetClient.exe` with the project name shown by `revhub projects`.
Stop and fix any validation error before involving a model. The output of
`revhub query status` should identify the binary you intended to study.

## Choose a model and run identifier

Ask Ollama which models are actually installed. Use the name exactly as shown:

```powershell
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Give this pass a short, unique name. It keeps the model's work separate from
every other pass:

```powershell
$runId = 'first-pass-20260722'
```

Use a new run id when you want an independent experiment. Reuse the same run
id only to continue an interrupted run with the same settings.

## First: make a no-write test

Run one dry test before leaving a model unattended. Replace
`<exact-model-name>` with a name from `ollama list`:

```powershell
revhub overnight `
  --provider ollama `
  --endpoint http://127.0.0.1:11434/api/chat `
  --model '<exact-model-name>' `
  --run-id $runId `
  --max-targets 1 `
  --max-minutes 10 `
  --context-window 8192 `
  --context-chars 6000 `
  --timeout 300 `
  --retries 1 `
  --temperature 0 `
  --max-tokens 400 `
  --dry-run
```

Success means the final JSON says `"dry_run": true` and `"writes": 0`.
This checks the connection, model name, and response format. It does not create
proposals or annotations.

If it fails, check that Ollama is running, copy the model name exactly, and try
again. For memory errors, lower `--context-window` to `4096` and
`--context-chars` to `3000`.

## Then: run a small real test

Do a small pass before an overnight run. It writes only disposable proposals:

```powershell
revhub overnight `
  --provider ollama `
  --endpoint http://127.0.0.1:11434/api/chat `
  --model '<exact-model-name>' `
  --run-id $runId `
  --max-targets 25 `
  --max-minutes 90 `
  --context-window 8192 `
  --context-chars 6000 `
  --timeout 300 `
  --retries 2 `
  --temperature 0 `
  --max-tokens 400
```

The model works one function at a time. For each function it may propose a
name, skip it, or defer it. A proposal is a question for review, not a rename.

If this finishes without provider errors and the output looks sensible, you can
run a larger pass. Reuse `$runId` to continue from where the small pass stopped:

```powershell
revhub overnight `
  --provider ollama `
  --endpoint http://127.0.0.1:11434/api/chat `
  --model '<exact-model-name>' `
  --run-id $runId `
  --max-targets 500 `
  --max-minutes 480 `
  --context-window 8192 `
  --context-chars 6000 `
  --timeout 300 `
  --retries 2 `
  --temperature 0 `
  --max-tokens 400
```

Keep the computer awake, on power, and leave the runner terminal and model
server open. It is fine for the display to turn off; system sleep pauses the
run.

## Check on a running pass

The run folder is inside your selected export:

```text
<export>\agent_runs\<run-id>\
```

Open a second PowerShell terminal and follow its log. Replace `<export-path>`
with the export path printed by `revhub use` or `revhub query status`:

```powershell
$runDirectory = '<export-path>\agent_runs\first-pass-20260722'
Get-Content -LiteralPath "$runDirectory\runner.jsonl" -Wait
```

The important files are:

| File | Plain-English meaning |
| --- | --- |
| `runner.jsonl` | What happened, in order, including errors. |
| `name_candidates.json` | The model's suggested names and cited evidence. |
| `investigation_progress.json` | What was processed, skipped, or deferred. |

Press `Ctrl+C` to stop safely. Run the same command with the same run id to
resume later; already finished functions are not repeated.

## What to do when the pass finishes

The final summary tells you how much work was attempted. It does **not** tell
you whether the names are correct. Do these things in order:

1. Check `runner.jsonl` for `provider-error` or repeated JSON/timeout errors.
   Fix the model problem before continuing.
2. Leave `name_candidates.json` where it is. Do not copy it into annotations
   and do not rename functions in Ghidra from it.
3. Use a stronger model or a careful human reviewer to check candidates one at
   a time through the local MCP server.

Start the review server for the same export and run id:

```powershell
revhub mcp --run-id $runId
```

Connect your MCP-capable review client to that stdio command. Give the reviewer
the command and then connect the client; a quiet terminal is normal while it
waits. Give the reviewer this instruction:

```text
Call binary_candidate_preflight once. Review candidates one at a time from
binary_candidate_page using bucket review and limit 10. For each candidate,
call binary_review_brief first. Request full binary_lookup or assembly only if
needed. Accept a name only when its concrete strings, imports, relationships,
and control flow support it. Reject unsupported names and defer uncertain ones.
Never bulk accept. Include a reviewer identity and a short review note.
```

Accepted names are saved only in
`<export>\annotations\function_names.json`. They are reversible, keep their
evidence and reviewer identity, and do not alter the raw export or Ghidra.
Use the annotation history command to inspect later corrections:

```powershell
python .\tools\function_annotations.py history <export-path> 00401000
```

## Continuous Codex or Claude campaigns

Use one task for discovery and a fresh task for review. This preserves an
independent reviewer while avoiding a new chat for every candidate page.

At any point, ask the MCP server for the exact durable state:

```powershell
revhub campaign-status --run-id <run-id>
```

The JSON field `next_action` is one of `run_preflight`, `review_pending`,
`inspect_preflight_exceptions`, or `discover`. `review.completion_percent`
counts only candidates eligible for review, not every function in the binary.
The same summary is available to MCP clients through `binary_campaign_status`.

For a reviewer, give one instruction that pages internally until the queue is
empty instead of ending after the first page:

```text
Call binary_campaign_status. If it says run_preflight, call
binary_candidate_preflight with refresh false. Then continue serially until
binary_campaign_status reports no pending reviewable candidates: request a
candidate page with bucket review and limit 25, review each candidate through
binary_review_brief first, and accept, reject, or defer it. Use full lookup
only when the brief is insufficient. Report progress after each 25 decisions,
but do not stop at a page boundary. Never bulk accept or modify raw exports.
```

For a discovery task, keep the work focused but let it process several bounded
checkpoints before it stops. For example, inspect up to 100 selected network or
login functions in groups of 25, report each checkpoint, and write proposals
only with `binary_propose_name`. A separate reviewer task should clear the
resulting proposal queue before the next discovery campaign.

## Simple choices after review

| Situation | What to do |
| --- | --- |
| The reviewer accepts a name | Keep it. It is a reversible annotation with evidence. |
| The reviewer rejects a name | Keep the rejection history; it prevents the same weak proposal being trusted. |
| The reviewer needs more proof | Defer it and move to the next candidate. |
| The model stopped or the computer slept | Fix the problem and rerun with the same run id. |
| You used the wrong export | Stop, run `revhub use <correct-project>`, validate it, then use a new run id. |
| You do not want the pass | Remove only that run's `agent_runs\<run-id>` folder. Never remove `annotations` just to discard model proposals. |

## When to use a bigger model

Use a smaller, inexpensive local model for the first pass. Its job is to sort
the large pile into possible leads. Use a stronger model for review, where it
sees a small bounded batch and must verify each concrete piece of evidence.

This two-step approach is usually faster, cheaper, and more accurate than
asking one large model to read the whole export. The detailed controls,
provider troubleshooting, and advanced MCP workflow are in
[Overnight naming](autonomous-agent.md).
