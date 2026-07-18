# Overnight local-model naming

Unattended output is staged as disposable candidates. It is never accepted merely because a model passed a citation guard.

```text
raw export (immutable)
  -> agent_runs/<run-id>/name_candidates.json (disposable)
  -> explicit stronger-model/human review
  -> annotations/function_names.json (accepted reversible overlay)
```

Progress is stored beside candidates in `agent_runs/<run-id>/investigation_progress.json`. Deleting the run directory scraps the pass without touching raw evidence or accepted names. `binary_annotate` remains for deliberate reviewers; do not put it in an unattended prompt.

## Start or resume

```powershell
python X:\Sources\RE-Evidence-Hub\binary_agent_mcp_server.py `
  --export X:\Sources\RE-Evidence-Hub\project_exports\TargetClient.exe `
  --run-id local-night-01
```

Use the same id to resume, or a new id for an independent model/pass. Absolute paths are recommended because MCP clients may use an unspecified working directory and reduced environment.

## Unattended loop

1. `binary_next_target`.
2. `binary_lookup` with decompiler evidence.
3. At most one or two relevant follow-up lookups.
4. If grounded, `binary_propose_name`; otherwise `binary_progress` as skipped/deferred.
5. Repeat until exhausted.

Every target ends with a proposal or progress record. Proposals require a valid non-placeholder symbol, medium/high confidence, rationale, evidence lines, and concrete refs found in that function's imports, strings, or named relationships. One ref must support a name term, or two independent refs are required. This catches fabrication; it does not prove the best name.

## Review later

1. List pending entries with `binary_candidate_queue`.
2. Re-run `binary_lookup` and verify code/control flow.
3. Use `binary_review_candidate` with `accept` or `reject` and a note.
4. Acceptance is blocked if the exported function hash changed.

Accepted candidates enter the annotation overlay with source `candidate-review:<run-id>`. Rejected entries remain audit history and never affect active names.

## Standing prompt

```markdown
Work one function at a time. Call binary_next_target, then binary_lookup.
Only cite imports, strings, or named relationships returned for that function.
If evidence supports a conservative name, call binary_propose_name. Otherwise
record skipped/deferred with binary_progress. Never call binary_annotate or
binary_review_candidate: you propose, you do not review. Stop when exhausted.
```

Run `revhub review-queue` first to prioritise high-signal functions.

## Built-in local-model runner

An MCP orchestrator is optional. The supported runner calls an OpenAI-compatible
local endpoint directly while retaining the same guard and candidate store:

```powershell
revhub overnight `
  --model qwen3-coder:30b `
  --run-id local-night-01 `
  --max-targets 500 `
  --max-minutes 480 `
  --max-tokens 1200
```

Ollama's native endpoint is also supported:

```powershell
revhub overnight --provider ollama `
  --endpoint http://127.0.0.1:11434/api/chat `
  --model qwen3-coder:30b --run-id local-night-01
```

Use `--dry-run` to request one decision without writing anything. The runner
limits decompiler context, retries transient HTTP failures, stops on its target
or time budget, and appends `runner.jsonl` inside the run directory. Reusing the
run id resumes its ledger; proposals still require separate review.
